import uuid

import pytest

from services.embedding import embed_texts
from services.neo4j.repositories import ClientRepository, DocumentRepository, IngestionRepository
from services.neo4j.schema import init_schema
from tests.conftest import requires_neo4j


@requires_neo4j
@pytest.mark.django_db
def test_delete_document_removes_chunks():
    init_schema()
    client = ClientRepository().create(name=f"Delete Test {uuid.uuid4().hex[:6]}")
    doc = DocumentRepository().create(
        client_id=client["id"],
        filename="del.txt",
        file_type="txt",
        file_path="",
    )
    parent_id = str(uuid.uuid4())
    parents = [
        {
            "id": parent_id,
            "text": "delete me content",
            "chunk_index": 0,
            "page_number": None,
            "section_header": "",
            "token_count": 3,
        }
    ]
    children = [
        {
            "id": str(uuid.uuid4()),
            "parent_id": parent_id,
            "text": "delete me content",
            "child_index": 0,
            "embedding": embed_texts(["delete me content"])[0],
        }
    ]
    IngestionRepository().write_chunks(doc["id"], client["id"], parents, children)
    doc_repo = DocumentRepository()
    assert doc_repo.chunk_count(doc["id"]) == 1

    assert doc_repo.delete_cascade(doc["id"]) is True
    assert doc_repo.get(doc["id"]) is None
