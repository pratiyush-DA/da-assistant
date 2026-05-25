from collections.abc import Iterator

from django.conf import settings
from langchain_core.exceptions import LangChainException

from services.graphrag.citations import select_citation_chunks
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
from services.graphrag.query_signals import parse_query_signals
from services.graphrag.retrieval_profile import RetrievalProfile, resolve_retrieval_profile
from services.graphrag.retriever import RetrievedChunk
from services.graphrag.workbook_rag import (
    classify_workbook_query,
    client_has_workbook_chunks,
    client_is_mixed,
    resolve_budget_mode,
)
from services.langchain.prompts import (
    DATA_DICTIONARY_SYSTEM_PROMPT,
    MIXED_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
)
from services.langchain.rag_chain import format_context_from_chunks, stream_rag_tokens
from services.langchain.rag_context import RAGFitResult
from services.llm.token_budget import fit_chunks_to_token_budget

CATALOG_ABSTAIN_MESSAGE = (
    "I cannot list tables: no table catalog was found in the retrieved context. "
    "Please re-ingest the spreadsheet workbook for this client."
)

WORKBOOK_INTENTS = frozenset({
    "catalog",
    "table",
    "table_by_definition",
    "database",
    "column",
    "code",
})


def _retrieve_chunks(
    client_id: str, message: str, profile: RetrievalProfile
) -> list[RetrievedChunk]:
    wb_intent = profile.workbook_intent

    if wb_intent == "catalog" and profile.has_workbook:
        return workbook_multi_hop_search(client_id, message)

    if profile.domain == "narrative":
        return hybrid_search(client_id, message, chunk_types=["row"])

    if profile.domain == "workbook" or wb_intent in WORKBOOK_INTENTS:
        return workbook_multi_hop_search(client_id, message)

    if profile.is_mixed_client:
        return mixed_document_search(client_id, message, profile=profile)

    if wb_intent == "table_by_definition" and profile.has_workbook:
        return workbook_multi_hop_search(client_id, message)

    if settings.MULTI_HOP_ENABLED and profile.has_workbook:
        return multi_hop_search(client_id, message)
    return hybrid_search(client_id, message, chunk_types=["row"])


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


def _format_context_with_table_by_definition(
    message: str, fitted: list[RetrievedChunk], client_id: str
) -> str:
    signals = parse_query_signals(message, client_id)
    if signals.get("workbook_intent") != "table_by_definition":
        return format_context_from_chunks(fitted)
    for chunk in fitted:
        if (chunk.chunk_type or "") == "table_definition":
            definition = extract_definition_from_table_chunk(chunk)
            if definition:
                table = chunk.table_name or "unknown"
                sheet = chunk.sheet_name or ""
                prefix = (
                    f"Matching table for the quoted definition (answer with this table name): "
                    f"Table: {table} | Definition: {definition}"
                    + (f" | Sheet: {sheet}" if sheet else "")
                )
                return prefix + "\n\n---\n\n" + format_context_from_chunks(fitted)
    return format_context_from_chunks(fitted)


def _budget_mode_for_profile(profile: RetrievalProfile, client_id: str, message: str) -> str:
    intent_modes = {
        "table": "workbook_table",
        "table_by_definition": "workbook_table",
        "database": "workbook_database",
        "catalog": "workbook_catalog",
        "column": "workbook_column",
        "code": "workbook_code",
    }
    if profile.domain == "narrative":
        return "narrative"
    if profile.domain == "workbook":
        return intent_modes.get(profile.workbook_intent, "workbook")
    if profile.is_mixed_client and profile.domain == "mixed":
        return "mixed"
    return resolve_budget_mode(client_id, message)


def _system_prompt_for_profile(
    profile: RetrievalProfile,
) -> tuple[str, bool, bool]:
    """Returns (system_prompt, use_dictionary_prompt, use_mixed_prompt)."""
    wb_intent = profile.workbook_intent

    if profile.is_mixed_client:
        if profile.domain == "workbook" or wb_intent in WORKBOOK_INTENTS:
            return DATA_DICTIONARY_SYSTEM_PROMPT, True, False
        if profile.domain == "mixed":
            return MIXED_SYSTEM_PROMPT, False, True
        return SYSTEM_PROMPT, False, False

    if profile.has_workbook and profile.domain == "workbook":
        return DATA_DICTIONARY_SYSTEM_PROMPT, True, False
    if profile.has_workbook and wb_intent in WORKBOOK_INTENTS:
        return DATA_DICTIONARY_SYSTEM_PROMPT, True, False
    return SYSTEM_PROMPT, False, False


def _fit_context(
    client_id: str, message: str, chunks: list[RetrievedChunk], profile: RetrievalProfile
) -> RAGFitResult:
    system_prompt, use_dictionary, use_mixed = _system_prompt_for_profile(profile)
    budget_mode = _budget_mode_for_profile(profile, client_id, message)

    if profile.inject_catalog:
        chunks = _inject_catalog_chunk(client_id, chunks)

    fitted = fit_chunks_to_token_budget(
        chunks, message, system_prompt, budget_mode=budget_mode
    )

    if profile.inject_catalog:
        fitted = _inject_catalog_chunk(client_id, fitted)

    citation_chunks = select_citation_chunks(fitted, profile)

    abstain = _catalog_abstain_message(client_id, message, fitted)
    if abstain:
        return RAGFitResult(
            context=abstain,
            fitted_chunks=fitted,
            citation_chunks=citation_chunks,
            use_dictionary=use_dictionary,
            use_mixed=use_mixed,
        )

    wb_intent = profile.workbook_intent
    if wb_intent == "catalog":
        context = _format_context_with_catalog_facts(message, fitted)
    elif wb_intent == "table":
        context = _format_context_with_table_definition(message, fitted)
    elif wb_intent == "table_by_definition":
        context = _format_context_with_table_by_definition(message, fitted, client_id)
    else:
        context = format_context_from_chunks(fitted)

    return RAGFitResult(
        context=context,
        fitted_chunks=fitted,
        citation_chunks=citation_chunks,
        use_dictionary=use_dictionary,
        use_mixed=use_mixed,
    )


def retrieve_and_fit_context(client_id: str, message: str) -> RAGFitResult:
    profile = resolve_retrieval_profile(client_id, message)
    chunks = _retrieve_chunks(client_id, message, profile)
    return _fit_context(client_id, message, chunks, profile)


def stream_rag_answer(client_id: str, message: str) -> Iterator[str]:
    if not settings.GROQ_API_KEY:
        yield "Error: GROQ_API_KEY is not configured."
        return

    result = retrieve_and_fit_context(client_id, message)

    if result.context.startswith("I cannot list tables"):
        yield result.context
        return

    try:
        yield from stream_rag_tokens(
            message,
            result.context,
            use_dictionary_prompt=result.use_dictionary,
            use_mixed_prompt=result.use_mixed,
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
