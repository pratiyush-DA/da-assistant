"""Structural boosts for retrieved chunks based on parsed query signals."""

from services.graphrag.retriever import RetrievedChunk
from services.graphrag.workbook_rag import intent_chunk_types


def boost_chunks_for_signals(
    chunks: list[RetrievedChunk],
    signals: dict,
) -> list[RetrievedChunk]:
    """Re-order chunks using metadata alignment (before cross-encoder rerank)."""
    if not chunks:
        return chunks

    intent = signals.get("workbook_intent") or "general"
    allowed_types = set(intent_chunk_types(intent))
    entity_table = signals.get("entity_table")
    sheet_hint = signals.get("sheet_hint")
    column_name = signals.get("column_name")

    def sort_key(c: RetrievedChunk) -> tuple:
        boost = 0
        ctype = c.chunk_type or ""
        if ctype in allowed_types:
            boost += 50
        if entity_table and (c.table_name or "").lower() == entity_table.lower():
            boost += 80
        if sheet_hint:
            sn = (c.sheet_name or "").lower()
            sh = sheet_hint.lower()
            if sn == sh:
                boost += 60
            elif sh in sn:
                boost += 30
        if column_name and intent == "column":
            col_norm = (c.column_name or "").lower().replace(" ", "")
            target = column_name.lower().replace(" ", "")
            if col_norm == target:
                boost += 40
        return (-boost, -c.score)

    return sorted(chunks, key=sort_key)
