from collections.abc import Iterator

from django.conf import settings
from langchain_core.exceptions import LangChainException

from services.graphrag.context_extractors import (
    catalog_names_from_chunks,
    extract_definition_from_table_chunk,
    format_table_list_for_context,
)
from services.graphrag.hybrid_retriever import hybrid_search
from services.graphrag.metadata_lookup import fetch_catalog_chunk
from services.graphrag.multi_hop import (
    mixed_document_search,
    multi_hop_search,
    workbook_multi_hop_search,
)
from services.graphrag.retriever import RetrievedChunk
from services.graphrag.workbook_rag import (
    classify_query_domain,
    classify_workbook_query,
    client_has_workbook_chunks,
    client_is_mixed,
    resolve_budget_mode,
    resolve_use_dictionary_prompt,
)
from services.langchain.prompts import (
    DATA_DICTIONARY_SYSTEM_PROMPT,
    MIXED_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
)
from services.langchain.rag_chain import format_context_from_chunks, stream_rag_tokens
from services.llm.token_budget import fit_chunks_to_token_budget

CATALOG_ABSTAIN_MESSAGE = (
    "I cannot list tables: no table catalog was found in the retrieved context. "
    "Please re-ingest the spreadsheet workbook for this client."
)


def _retrieve_chunks(client_id: str, message: str) -> list[RetrievedChunk]:
    wb_intent = classify_workbook_query(message)

    if wb_intent == "catalog" and client_has_workbook_chunks(client_id):
        return workbook_multi_hop_search(client_id, message)

    if client_is_mixed(client_id):
        domain = classify_query_domain(message)
        if domain == "narrative":
            return hybrid_search(client_id, message, chunk_types=["row"])
        if domain == "workbook" or wb_intent in (
            "table",
            "database",
            "column",
            "code",
        ):
            return workbook_multi_hop_search(client_id, message)
        return mixed_document_search(client_id, message)

    if settings.MULTI_HOP_ENABLED and client_has_workbook_chunks(client_id):
        return multi_hop_search(client_id, message)
    return hybrid_search(client_id, message)


def _inject_catalog_chunk(
    client_id: str, fitted: list[RetrievedChunk]
) -> list[RetrievedChunk]:
    if catalog_names_from_chunks(fitted):
        return fitted
    catalog = fetch_catalog_chunk(client_id)
    if not catalog:
        return fitted
    seen = {c.id for c in fitted}
    if catalog.id in seen:
        return fitted
    return [catalog] + fitted


def _catalog_abstain_message(
    client_id: str, message: str, fitted: list[RetrievedChunk]
) -> str | None:
    if classify_workbook_query(message) != "catalog":
        return None
    fitted_with_catalog = _inject_catalog_chunk(client_id, fitted)
    if catalog_names_from_chunks(fitted_with_catalog):
        return None
    return CATALOG_ABSTAIN_MESSAGE


def _format_context_with_catalog_facts(
    message: str, fitted: list[RetrievedChunk]
) -> str:
    if classify_workbook_query(message) != "catalog":
        return format_context_from_chunks(fitted)

    names = catalog_names_from_chunks(fitted)
    prefix = format_table_list_for_context(names, limit=5) if names else ""
    base = format_context_from_chunks(fitted)
    if prefix:
        return prefix + "\n\n---\n\n" + base
    return base


def _format_context_with_table_definition(
    message: str, fitted: list[RetrievedChunk]
) -> str:
    if classify_workbook_query(message) != "table":
        return format_context_from_chunks(fitted)
    for chunk in fitted:
        if (chunk.chunk_type or "") == "table_definition":
            definition = extract_definition_from_table_chunk(chunk)
            if definition:
                table = chunk.table_name or "unknown"
                prefix = (
                    f"Table definition (quote verbatim in Details): "
                    f"Table: {table} | Definition: {definition}"
                )
                return prefix + "\n\n---\n\n" + format_context_from_chunks(fitted)
    return format_context_from_chunks(fitted)


def _system_prompt_for_client(client_id: str, message: str) -> tuple[str, bool, bool, str]:
    """Returns (system_prompt, use_dictionary_prompt, use_mixed_prompt, budget_mode)."""
    use_dictionary = resolve_use_dictionary_prompt(client_id, message)
    budget_mode = resolve_budget_mode(client_id, message)

    if client_is_mixed(client_id):
        domain = classify_query_domain(message)
        wb_intent = classify_workbook_query(message)
        if domain == "workbook" or wb_intent in (
            "catalog",
            "table",
            "database",
            "column",
            "code",
        ):
            return DATA_DICTIONARY_SYSTEM_PROMPT, True, False, budget_mode
        if domain == "general":
            return MIXED_SYSTEM_PROMPT, False, True, budget_mode
        return SYSTEM_PROMPT, False, False, budget_mode

    if use_dictionary:
        return DATA_DICTIONARY_SYSTEM_PROMPT, True, False, budget_mode
    return SYSTEM_PROMPT, False, False, budget_mode


def _fit_context(
    client_id: str, message: str, chunks: list[RetrievedChunk]
) -> tuple[str, list[RetrievedChunk], bool, bool]:
    system_prompt, use_dictionary, use_mixed, budget_mode = _system_prompt_for_client(
        client_id, message
    )
    chunks = _inject_catalog_chunk(client_id, chunks)
    fitted = fit_chunks_to_token_budget(
        chunks, message, system_prompt, budget_mode=budget_mode
    )
    fitted = _inject_catalog_chunk(client_id, fitted)

    abstain = _catalog_abstain_message(client_id, message, fitted)
    if abstain:
        return abstain, fitted, use_dictionary, use_mixed

    wb_intent = classify_workbook_query(message)
    if wb_intent == "catalog":
        context = _format_context_with_catalog_facts(message, fitted)
    elif wb_intent == "table":
        context = _format_context_with_table_definition(message, fitted)
    else:
        context = format_context_from_chunks(fitted)

    return context, fitted, use_dictionary, use_mixed


def retrieve_and_fit_context(
    client_id: str, message: str
) -> tuple[str, list[RetrievedChunk], bool, bool]:
    chunks = _retrieve_chunks(client_id, message)
    return _fit_context(client_id, message, chunks)


def stream_rag_answer(client_id: str, message: str) -> Iterator[str]:
    if not settings.GROQ_API_KEY:
        yield "Error: GROQ_API_KEY is not configured."
        return

    chunks = _retrieve_chunks(client_id, message)
    context, fitted, use_dictionary, use_mixed = _fit_context(
        client_id, message, chunks
    )

    if context.startswith("I cannot list tables"):
        yield context
        return

    try:
        yield from stream_rag_tokens(
            message,
            context,
            use_dictionary_prompt=use_dictionary,
            use_mixed_prompt=use_mixed,
        )
    except LangChainException as exc:
        err = str(exc).lower()
        if "413" in err or "429" in err or "rate_limit" in err or "too large" in err:
            yield (
                "The retrieved document context exceeds your Groq plan's per-request "
                "token limit (6,000 TPM for llama-3.1-8b-instant on the free tier). "
                "Context was trimmed automatically; try a shorter question, fewer "
                "documents, or set GROQ_MODEL to a model with a higher TPM limit "
                "(e.g. llama-3.3-70b-versatile at 12K), or upgrade at console.groq.com."
            )
        else:
            yield f"Groq API error: {exc}"
    except Exception as exc:
        err = str(exc).lower()
        if "413" in err or "429" in err or "rate_limit" in err:
            yield (
                "The retrieved document context exceeds your Groq plan's per-request "
                "token limit. Try a shorter question or a model with higher TPM."
            )
        else:
            yield f"Error: {exc}"
