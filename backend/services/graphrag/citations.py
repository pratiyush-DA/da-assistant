"""Select and format chunks for API/UI citations."""

from services.graphrag.retrieval_profile import RetrievalProfile
from services.graphrag.retriever import RetrievedChunk

_DOC_EXTENSIONS = (".txt", ".pdf", ".docx", ".doc", ".md", ".csv")


def empty_citations() -> list[RetrievedChunk]:
    return []


def chunk_display_label(chunk: RetrievedChunk) -> str:
    """Human-readable citation label (filename-first)."""
    ctype = chunk.chunk_type or ""
    filename = (chunk.source or "").strip()

    if ctype == "row":
        parts: list[str] = []
        if filename:
            parts.append(filename)
        if chunk.section_header:
            if parts:
                parts[0] = f"{parts[0]} — {chunk.section_header}"
            else:
                parts.append(chunk.section_header)
        if chunk.page_number is not None:
            page = f"page {chunk.page_number}"
            if parts:
                parts[-1] = f"{parts[-1]}, {page}"
            else:
                parts.append(page)
        if parts:
            return parts[0] if len(parts) == 1 else "; ".join(parts)
        return "Document"

    if ctype == "table_catalog":
        if filename:
            return f"{filename} — table catalog"
        return chunk.section_header or "Table catalog"

    detail = chunk.section_header or ""
    if not detail and chunk.table_name:
        detail = f"Table {chunk.table_name}"
        if chunk.column_name:
            detail += f", Column {chunk.column_name}"
    elif chunk.column_name and chunk.column_name not in detail:
        detail = f"{detail}, Column {chunk.column_name}" if detail else f"Column {chunk.column_name}"

    if filename and detail:
        return f"{filename} — {detail}"
    if filename:
        return filename
    return detail or ctype or "Source"


def select_citation_chunks(
    fitted: list[RetrievedChunk],
    profile: RetrievalProfile,
) -> list[RetrievedChunk]:
    """Return deduplicated citation-eligible chunks from fitted context."""
    if not fitted:
        return []

    allowed = profile.allowed_citation_types
    if profile.workbook_intent != "catalog":
        allowed = frozenset(t for t in allowed if t != "table_catalog")

    candidates: list[RetrievedChunk] = []
    for chunk in fitted:
        ctype = chunk.chunk_type or ""
        if ctype not in allowed:
            continue
        if ctype == "table_catalog" and profile.workbook_intent != "catalog":
            continue
        candidates.append(chunk)

    def sort_key(c: RetrievedChunk) -> tuple:
        if profile.domain == "narrative":
            return (c.page_number if c.page_number is not None else 9999, -c.score)
        filename = (c.source or "").lower()
        has_file = bool(filename) and filename.endswith(_DOC_EXTENSIONS)
        return (0 if has_file else 1, -c.score)

    candidates.sort(key=sort_key)

    seen: set[tuple[str, str]] = set()
    out: list[RetrievedChunk] = []
    for chunk in candidates:
        doc_key = chunk.document_id or ""
        src_key = (chunk.source or chunk.section_header or chunk.id or "").strip()
        key = (doc_key, src_key)
        if key in seen:
            continue
        seen.add(key)
        out.append(chunk)
        if len(out) >= profile.citation_budget:
            break

    return out
