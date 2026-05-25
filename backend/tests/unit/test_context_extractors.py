from services.graphrag.context_extractors import (
    catalog_names_from_chunks,
    parse_table_names_from_catalog,
)
from services.graphrag.retriever import RetrievedChunk


def _catalog_chunk(text: str) -> RetrievedChunk:
    return RetrievedChunk(
        id="1",
        chunk_text=text,
        child_text=text,
        section_header="",
        page_number=None,
        document_id="d1",
        source="dict.xlsx",
        score=1.0,
        chunk_type="table_catalog",
    )


def test_parse_tables_from_ingest_format():
    text = "Table catalog | Sheet: Tables | Tables (3): Agency, Request, SectionI-1"
    assert parse_table_names_from_catalog(text) == ["Agency", "Request", "SectionI-1"]


def test_parse_derived_catalog():
    text = "Table catalog (derived): Customer, Order"
    assert parse_table_names_from_catalog(text) == ["Customer", "Order"]


def test_catalog_names_from_chunks():
    chunks = [_catalog_chunk("Tables (2): Alpha, Beta")]
    assert catalog_names_from_chunks(chunks) == ["Alpha", "Beta"]
