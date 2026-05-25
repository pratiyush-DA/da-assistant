import pytest
from django.test import override_settings

from services.embedding import embed_query, embed_texts


@pytest.mark.slow
@override_settings(EMBEDDING_MODEL="BAAI/bge-large-en-v1.5")
def test_embed_documents_dimensions():
    vectors = embed_texts(["hello world", "second doc"])
    assert len(vectors) == 2
    assert len(vectors[0]) == 1024
    assert len(vectors[1]) == 1024


@pytest.mark.slow
@override_settings(EMBEDDING_MODEL="BAAI/bge-large-en-v1.5")
def test_embed_query_dimensions():
    vector = embed_query("what are payment terms?")
    assert len(vector) == 1024
