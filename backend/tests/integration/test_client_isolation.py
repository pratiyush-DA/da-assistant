import uuid

import pytest

from services.embedding import embed_texts
from services.graphrag import search_similar_chunks
from services.neo4j.repositories import ClientRepository, DocumentRepository, IngestionRepository
from services.neo4j.schema import init_schema
from tests.conftest import requires_neo4j


@requires_neo4j
@pytest.mark.django_db
def test_client_isolation_in_vector_search():
    init_schema()
    client_repo = ClientRepository()
    doc_repo = DocumentRepository()
    ingest_repo = IngestionRepository()

    client_a = client_repo.create(name=f"Client A {uuid.uuid4().hex[:6]}")
    client_b = client_repo.create(name=f"Client B {uuid.uuid4().hex[:6]}")

    doc_a = doc_repo.create(
        client_id=client_a["id"],
        filename="a.txt",
        file_type="txt",
        file_path="",
    )
    doc_b = doc_repo.create(
        client_id=client_b["id"],
        filename="b.txt",
        file_type="txt",
        file_path="",
    )

    parents_a = [
        {
            "id": str(uuid.uuid4()),
            "text": "Client A secret keyword: ALPHA_UNIQUE_12345",
            "chunk_index": 0,
            "page_number": 1,
            "section_header": "A Section",
            "token_count": 10,
        }
    ]
    children_a = [
        {
            "id": str(uuid.uuid4()),
            "parent_id": parents_a[0]["id"],
            "text": parents_a[0]["text"],
            "child_index": 0,
            "embedding": embed_texts([parents_a[0]["text"]])[0],
        }
    ]
    parents_b = [
        {
            "id": str(uuid.uuid4()),
            "text": "Client B secret keyword: BETA_UNIQUE_67890",
            "chunk_index": 0,
            "page_number": 1,
            "section_header": "B Section",
            "token_count": 10,
        }
    ]
    children_b = [
        {
            "id": str(uuid.uuid4()),
            "parent_id": parents_b[0]["id"],
            "text": parents_b[0]["text"],
            "child_index": 0,
            "embedding": embed_texts([parents_b[0]["text"]])[0],
        }
    ]

    ingest_repo.write_chunks(doc_a["id"], client_a["id"], parents_a, children_a)
    ingest_repo.write_chunks(doc_b["id"], client_b["id"], parents_b, children_b)
    doc_repo.set_status(doc_a["id"], "ready")
    doc_repo.set_status(doc_b["id"], "ready")

    results = search_similar_chunks(client_a["id"], "ALPHA_UNIQUE_12345")
    assert len(results) >= 1
    for chunk in results:
        assert "BETA_UNIQUE" not in chunk.chunk_text
        assert chunk.source != "b.txt"

    doc_repo.delete_cascade(doc_a["id"])
    doc_repo.delete_cascade(doc_b["id"])
