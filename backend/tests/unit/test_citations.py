from services.graphrag.citations import chunk_display_label, select_citation_chunks
from services.graphrag.retrieval_profile import RetrievalProfile
from services.graphrag.retriever import RetrievedChunk


def _row(filename: str) -> RetrievedChunk:
    return RetrievedChunk(
        id="r1",
        chunk_text="Pratiyush works at Data Axle",
        section_header="",
        page_number=None,
        document_id="d1",
        source=filename,
        score=1.0,
        chunk_type="row",
        child_text="Pratiyush works at Data Axle",
    )


def _catalog() -> RetrievedChunk:
    return RetrievedChunk(
        id="c1",
        chunk_text="catalog",
        section_header="Catalog (FOIA Tables)",
        page_number=None,
        document_id="d2",
        source="dict.xlsx",
        score=0.9,
        chunk_type="table_catalog",
        child_text="catalog",
    )


def test_select_citation_narrative_excludes_catalog():
    profile = RetrievalProfile(
        domain="narrative",
        workbook_intent="general",
        is_mixed_client=True,
        has_workbook=True,
        allowed_citation_types=frozenset({"row"}),
    )
    fitted = [_row("test_text1.txt"), _row("test_text2.txt"), _catalog()]
    cites = select_citation_chunks(fitted, profile)
    assert len(cites) == 2
    assert all(c.chunk_type == "row" for c in cites)
    assert {c.source for c in cites} == {"test_text1.txt", "test_text2.txt"}


def test_display_label_uses_filename_for_row():
    label = chunk_display_label(_row("test_text1.txt"))
    assert label == "test_text1.txt"


def test_display_label_workbook_includes_filename():
    chunk = RetrievedChunk(
        id="x",
        chunk_text="body",
        section_header="SectionI-1 (FOIA Fields)",
        page_number=None,
        document_id="d",
        source="data_dictionary.xlsx",
        score=1.0,
        chunk_type="column",
        table_name="SectionI-1",
        column_name="OrderId",
        child_text="body",
    )
    label = chunk_display_label(chunk)
    assert "data_dictionary.xlsx" in label
    assert "SectionI-1" in label
