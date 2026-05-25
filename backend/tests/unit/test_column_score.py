from services.graphrag.metadata_lookup import score_column_chunk
from services.graphrag.retriever import RetrievedChunk


def _col(text: str, table: str = "T1") -> RetrievedChunk:
    return RetrievedChunk(
        id="1",
        chunk_text=text,
        child_text=text,
        section_header="",
        page_number=None,
        document_id="d1",
        source="x.xlsx",
        score=1.0,
        chunk_type="column",
        table_name=table,
        column_name="ReportTitle",
    )


def test_prefers_row_with_datatype():
    weak = _col(
        "Table: OtherDetails | Column: ReportTitle | Datatype: | Definition: weak",
        "OtherDetails",
    )
    strong = _col(
        "Table: SectionI-1 | Column: ReportTitle | Datatype: VARCHAR(100) | "
        "Definition: The heading",
        "SectionI-1",
    )
    assert score_column_chunk("ReportTitle", strong) > score_column_chunk(
        "ReportTitle", weak
    )
