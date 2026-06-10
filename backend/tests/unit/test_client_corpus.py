from unittest.mock import MagicMock, patch
from uuid import uuid4

from services.graphrag.client_corpus import (
    ClientCorpusProfile,
    ClientDocument,
    clear_corpus_cache,
    document_is_narrative_only,
    document_is_workbook_only,
    entity_resolves_to_workbook,
    score_document_affinity,
)


def test_document_is_narrative_only():
    doc = ClientDocument("d1", "plan.pdf", "pdf", frozenset({"row"}))
    assert document_is_narrative_only(doc)
    assert not document_is_workbook_only(doc)


def test_document_is_workbook_only():
    doc = ClientDocument("d2", "dict.xlsx", "xlsx", frozenset({"column", "table_definition"}))
    assert document_is_workbook_only(doc)
    assert not document_is_narrative_only(doc)


def test_score_document_affinity_matches_filename_tokens():
    client_id = str(uuid4())
    profile = ClientCorpusProfile(
        client_id=client_id,
        documents=(
            ClientDocument("d1", "upgrade_plan_v3.pdf", "pdf", frozenset({"row"})),
            ClientDocument("d2", "data_dictionary.xlsx", "xlsx", frozenset({"column"})),
        ),
        has_narrative=True,
        has_workbook=True,
        is_mixed=True,
    )
    with patch(
        "services.graphrag.client_corpus.get_client_corpus_profile",
        return_value=profile,
    ):
        scores = score_document_affinity(client_id, "What is in the upgrade plan v3?")
    assert scores["d1"] > scores["d2"]


def test_entity_resolves_to_workbook_exact_table():
    client_id = str(uuid4())
    index = MagicMock()
    index.table_names = frozenset({"TABLE_A"})
    index.column_keys = frozenset()
    with patch(
        "services.graphrag.client_corpus.get_workbook_entity_index",
        return_value=index,
    ):
        assert entity_resolves_to_workbook(client_id, "TABLE_A")
        assert not entity_resolves_to_workbook(client_id, "ZZZ_UNKNOWN")


def test_clear_corpus_cache():
    from services.graphrag import client_corpus

    client_corpus._corpus_cache["x"] = MagicMock()
    client_corpus._entity_index_cache["x"] = MagicMock()
    clear_corpus_cache("x")
    assert "x" not in client_corpus._corpus_cache
    assert "x" not in client_corpus._entity_index_cache
