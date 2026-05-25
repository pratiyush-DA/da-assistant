from services.graphrag.metadata_lookup import (
    _definition_similarity,
    score_column_chunk,
)
from services.graphrag.retriever import RetrievedChunk


def _col_chunk(table_name: str, definition: str) -> RetrievedChunk:
    text = (
        f"Table: {table_name} | Column: FullNameofPointofContact | "
        f"Definition: {definition} | Sheet: FOIA Fields"
    )
    return RetrievedChunk(
        id="1",
        chunk_text=text,
        section_header="",
        page_number=None,
        document_id="d1",
        source="f.xlsx",
        score=1.0,
        chunk_type="column",
        sheet_name="FOIA Fields",
        table_name=table_name,
        column_name="FullNameofPointofContact",
        child_text=text,
    )


def test_score_column_prefers_requested_table():
    c3 = _col_chunk(
        "SectionI-3",
        "The complete name of the individual who handles paper report distribution.",
    )
    c1 = _col_chunk(
        "SectionI-1",
        "The complete name of the individual who handles report distribution.",
    )
    s3 = score_column_chunk(
        "FullNameofPointofContact",
        c3,
        required_table_name="SectionI-1",
    )
    s1 = score_column_chunk(
        "FullNameofPointofContact",
        c1,
        required_table_name="SectionI-1",
    )
    assert s1 > s3


def test_definition_similarity_exact():
    assert _definition_similarity(
        "Organization responsible for issuing the FOIA annual report",
        "Organization responsible for issuing the FOIA annual report",
    ) >= 0.95
