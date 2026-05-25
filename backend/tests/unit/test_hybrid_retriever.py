from services.graphrag.hybrid_retriever import _escape_lucene, rrf_merge


def test_escape_lucene_special_chars():
    assert _escape_lucene("foo+bar") == "foo\\+bar"


def test_rrf_merge_combines_rankings():
    list_a = [{"id": "1", "document_id": "d", "chunk_text": "a", "score": 0.9}]
    list_b = [{"id": "2", "document_id": "d", "chunk_text": "b", "score": 0.8}]
    merged = rrf_merge([list_a, list_b], k=60)
    assert len(merged) == 2
    assert merged[0].score >= merged[1].score


def test_rrf_prefers_both_lists():
    list_a = [{"id": "1", "document_id": "d", "chunk_text": "a", "score": 0.5}]
    list_b = [{"id": "1", "document_id": "d", "chunk_text": "a", "score": 0.5}]
    merged = rrf_merge([list_a, list_b], k=60)
    assert len(merged) == 1
    assert merged[0].score > 0.03
