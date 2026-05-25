"""Structured extraction from workbook chunk text (file-agnostic)."""

import re

from services.graphrag.retriever import RetrievedChunk

CATALOG_TABLES_PATTERN = re.compile(
    r"Tables\s*\(\s*\d+\s*\)\s*:\s*(.+)",
    re.I | re.DOTALL,
)
DERIVED_CATALOG_PATTERN = re.compile(
    r"Table catalog \(derived\)\s*:\s*(.+)",
    re.I,
)


def parse_table_names_from_catalog(text: str) -> list[str]:
    """Parse table names from ingest catalog or derived fallback text."""
    if not text:
        return []
    m = CATALOG_TABLES_PATTERN.search(text)
    if not m:
        m = DERIVED_CATALOG_PATTERN.search(text)
    if not m:
        return []
    listing = m.group(1).strip()
    if not listing:
        return []
    names: list[str] = []
    for part in re.split(r",\s*", listing):
        name = part.strip().strip(".")
        if name:
            names.append(name)
    return names


def catalog_names_from_chunks(chunks: list[RetrievedChunk]) -> list[str]:
    """Union of table names parsed from any table_catalog chunk in context."""
    seen: set[str] = set()
    out: list[str] = []
    for c in chunks:
        if (c.chunk_type or "") != "table_catalog":
            continue
        for name in parse_table_names_from_catalog(c.child_text or c.chunk_text or ""):
            if name not in seen:
                seen.add(name)
                out.append(name)
    return out


def catalog_chunk_has_parseable_names(chunk: RetrievedChunk) -> bool:
    text = chunk.child_text or chunk.chunk_text or ""
    return bool(parse_table_names_from_catalog(text))


def format_table_list_for_context(names: list[str], limit: int = 5) -> str:
    """Build a facts line for catalog questions (names from parse only)."""
    if not names:
        return ""
    picked = names[:limit]
    suffix = f" (showing {len(picked)} of {len(names)} tables)" if len(names) > limit else ""
    return f"Allowed table names (from catalog only){suffix}: " + ", ".join(picked)


def extract_definition_from_table_chunk(chunk: RetrievedChunk) -> str | None:
    text = chunk.child_text or chunk.chunk_text or ""
    m = re.search(r"Definition:\s*(.+?)(?:\s*\||\s*$)", text, re.I | re.DOTALL)
    if m:
        return m.group(1).strip()
    return None
