from apps.chat.views import _chunks_to_sources
from services.graphrag.retriever import RetrievedChunk


def test_chunks_to_sources_includes_display_label():
    chunk = RetrievedChunk(
        id="1",
        chunk_text="text",
        section_header="Catalog (FOIA Tables)",
        page_number=None,
        document_id="d1",
        source="test_text1.txt",
        score=1.0,
        chunk_type="row",
        child_text="text",
    )
    sources = _chunks_to_sources([chunk])
    assert len(sources) == 1
    assert sources[0]["display_label"] == "test_text1.txt"
    assert sources[0]["source"] == "test_text1.txt"
