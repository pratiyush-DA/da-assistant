import uuid

import pytest

from services.embedding import embed_texts
from services.neo4j.repositories import (
    ChatRepository,
    ClientRepository,
    ConversationRepository,
    DocumentRepository,
    IngestionRepository,
    UserRepository,
)
from services.neo4j.schema import init_schema
from tests.conftest import requires_neo4j


@requires_neo4j
@pytest.mark.django_db
def test_delete_client_cascade_removes_all_client_data():
    init_schema()
    suffix = uuid.uuid4().hex[:6]
    client = ClientRepository().create(name=f"Client Delete {suffix}")
    client_id = client["id"]

    user = UserRepository().create(
        email=f"delete-client-{suffix}@data-axle.com",
        display_name="Delete Test User",
    )
    conv = ConversationRepository().create(
        user_id=user["id"],
        client_id=client_id,
        title="Test conv",
    )
    ConversationRepository().create_message(conv["id"], "user", "hello")

    doc = DocumentRepository().create(
        client_id=client_id,
        filename="del.txt",
        file_type="txt",
        file_path="",
    )
    parent_id = str(uuid.uuid4())
    parents = [
        {
            "id": parent_id,
            "text": "client delete content",
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
            "text": "client delete content",
            "child_index": 0,
            "embedding": embed_texts(["client delete content"])[0],
        }
    ]
    IngestionRepository().write_chunks(doc["id"], client_id, parents, children)
    ChatRepository().create_message(client_id, "user", "legacy chat")

    doc_repo = DocumentRepository()
    assert doc_repo.chunk_count(doc["id"]) == 1
    assert ConversationRepository().get(conv["id"]) is not None
    assert len(ChatRepository().list_by_client(client_id)) == 1

    assert ClientRepository().delete_cascade(client_id) is True
    assert ClientRepository().get(client_id) is None
    assert doc_repo.get(doc["id"]) is None
    assert ConversationRepository().get(conv["id"]) is None
    assert len(ChatRepository().list_by_client(client_id)) == 0
    assert UserRepository().get(user["id"]) is not None
