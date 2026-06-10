"""Fit RAG context into Groq per-request token limits (TPM cap for on_demand tier)."""

import tiktoken
from django.conf import settings

from services.graphrag.retriever import RetrievedChunk
from services.langchain.rag_chain import _chunk_label

_ENCODING = tiktoken.get_encoding("cl100k_base")

WORKBOOK_PRIORITY = {
    "column": 0,
    "code_set": 1,
    "table_definition": 2,
    "database": 3,
    "table_catalog": 4,
    "overview": 5,
    "table": 6,
    "row": 7,
}

INTENT_PRIORITY = {
    "workbook_table": {"table_definition": 0, "table_catalog": 1, "column": 9},
    "workbook_database": {"database": 0, "overview": 1, "column": 9},
    "workbook_catalog": {"table_catalog": 0, "column": 9, "table_definition": 9},
    "workbook_column": {"column": 0, "code_set": 9},
    "workbook_code": {"code_set": 0, "column": 5},
}


def count_tokens(text: str) -> int:
    return len(_ENCODING.encode(text))


def _messages_token_count(system: str, user_content: str) -> int:
    return count_tokens(system) + count_tokens(user_content) + 8


def _format_block(chunk: RetrievedChunk, index: int, sep: str) -> str:
    label = _chunk_label(chunk)
    source = f" ({chunk.source})" if chunk.source else ""
    page = f", page {chunk.page_number}" if chunk.page_number else ""
    body = chunk.child_text or chunk.chunk_text
    return f"{sep}[{index}] {label}{source}{page}\n{body}"


def _sort_chunks_for_budget(
    chunks: list[RetrievedChunk], budget_mode: str
) -> list[RetrievedChunk]:
    if budget_mode in INTENT_PRIORITY:
        prio = INTENT_PRIORITY[budget_mode]

        def key(c: RetrievedChunk) -> tuple:
            return (prio.get(c.chunk_type or "row", 9), -c.score)

        return sorted(chunks, key=key)

    if budget_mode == "workbook":
        return sorted(
            chunks,
            key=lambda c: (WORKBOOK_PRIORITY.get(c.chunk_type or "row", 7), -c.score),
        )

    if budget_mode in ("mixed", "narrative", "default"):
        return sorted(chunks, key=lambda c: -c.score)

    return list(chunks)


def _apply_mixed_token_floor(
    sorted_chunks: list[RetrievedChunk],
    context_budget: int,
    floor_ratio: float,
) -> list[RetrievedChunk]:
    """Reserve narrative row token budget before workbook chunks consume the pool."""
    row_chunks = sorted(
        [c for c in sorted_chunks if (c.chunk_type or "") == "row"],
        key=lambda c: -c.score,
    )
    other_chunks = sorted(
        [c for c in sorted_chunks if (c.chunk_type or "") != "row"],
        key=lambda c: -c.score,
    )
    if not row_chunks or not other_chunks:
        return sorted_chunks

    floor = max(64, int(context_budget * floor_ratio))
    reserved_rows: list[RetrievedChunk] = []
    used = 0
    for chunk in row_chunks:
        block = _format_block(chunk, len(reserved_rows) + 1, "")
        block_tokens = count_tokens(block)
        if used + block_tokens <= floor:
            reserved_rows.append(chunk)
            used += block_tokens

    remaining_rows = [c for c in row_chunks if c not in reserved_rows]
    return reserved_rows + other_chunks + remaining_rows


def _apply_mixed_slot_reservation(
    sorted_chunks: list[RetrievedChunk], limit: int
) -> list[RetrievedChunk]:
    """Reserve slots for narrative row chunks when merging workbook + document context."""
    row_chunks = [c for c in sorted_chunks if (c.chunk_type or "") == "row"]
    other_chunks = [c for c in sorted_chunks if (c.chunk_type or "") != "row"]
    if not row_chunks:
        return sorted_chunks

    max_row = min(4, max(2, limit // 3))
    max_other = limit - max_row
    reserved_rows = row_chunks[:max_row]
    reserved_other = other_chunks[:max_other]
    combined = reserved_rows + reserved_other
    combined.sort(key=lambda c: -c.score)
    return combined


def fit_chunks_to_token_budget(
    chunks: list[RetrievedChunk],
    user_message: str,
    system_prompt: str,
    *,
    budget_mode: str = "default",
    workbook_client: bool | None = None,
) -> list[RetrievedChunk]:
    """
    Return chunks whose combined context fits under LLM_MAX_REQUEST_TOKENS.
    budget_mode: narrative | workbook | workbook_table | workbook_database | mixed | default
    """
    if workbook_client is not None and budget_mode == "default":
        budget_mode = "workbook" if workbook_client else "default"

    max_request = settings.LLM_MAX_REQUEST_TOKENS
    reserved = (
        _messages_token_count(system_prompt, f"Context:\n\nQuestion: {user_message}")
        + settings.LLM_MAX_COMPLETION_TOKENS
    )
    safety_margin = 64
    context_budget = max(256, max_request - reserved - safety_margin)

    sorted_chunks = _sort_chunks_for_budget(chunks, budget_mode)
    if budget_mode == "workbook_column":
        sorted_chunks = sorted_chunks[:3]
    elif budget_mode == "workbook_catalog":
        sorted_chunks = sorted_chunks[:2]
    elif budget_mode in ("workbook_table", "workbook_database"):
        sorted_chunks = sorted_chunks[:2]
    if budget_mode == "mixed":
        sorted_chunks = _apply_mixed_slot_reservation(
            sorted_chunks, settings.VECTOR_SEARCH_LIMIT
        )
        sorted_chunks = _apply_mixed_token_floor(
            sorted_chunks,
            context_budget,
            settings.MIXED_NARRATIVE_TOKEN_FLOOR_RATIO,
        )

    included: list[RetrievedChunk] = []
    used = 0

    for chunk in sorted_chunks:
        sep = "\n\n---\n\n" if included else ""
        block = _format_block(chunk, len(included) + 1, sep)
        block_tokens = count_tokens(block)

        if used + block_tokens <= context_budget:
            included.append(chunk)
            used += block_tokens
            continue

        remaining = context_budget - used - count_tokens(sep + _chunk_label(chunk) + "\n")
        if remaining < 64:
            continue

        body = chunk.child_text or chunk.chunk_text
        truncated_text = _ENCODING.decode(_ENCODING.encode(body)[:remaining])
        included.append(
            RetrievedChunk(
                id=chunk.id,
                chunk_text=truncated_text + "…",
                section_header=chunk.section_header,
                page_number=chunk.page_number,
                document_id=chunk.document_id,
                source=chunk.source,
                score=chunk.score,
                chunk_type=chunk.chunk_type,
                sheet_name=chunk.sheet_name,
                table_name=chunk.table_name,
                column_name=chunk.column_name,
                child_text=truncated_text + "…",
            )
        )
        break

    return included


def build_context_from_chunks(chunks: list[RetrievedChunk]) -> str:
    from services.langchain.rag_chain import format_context_from_chunks

    return format_context_from_chunks(chunks)
