from unittest.mock import patch
from uuid import uuid4

from services.graphrag.domain_scoring import (
    resolve_workbook_intent_guarded,
    score_query_domain,
)


def _mixed_corpus():
    from services.graphrag.client_corpus import ClientCorpusProfile, ClientDocument

    return ClientCorpusProfile(
        client_id="c1",
        documents=(
            ClientDocument("d1", "doc1.pdf", "pdf", frozenset({"row"})),
            ClientDocument("d2", "dict.xlsx", "xlsx", frozenset({"column"})),
        ),
        has_narrative=True,
        has_workbook=True,
        is_mixed=True,
    )


def test_entity_in_index_biases_workbook():
    client_id = str(uuid4())
    signals = {
        "workbook_intent": "table",
        "entity_table": "TABLE_A",
        "column_name": None,
        "sheet_hint": None,
        "quoted_definition": None,
    }
    with (
        patch(
            "services.graphrag.domain_scoring.get_client_corpus_profile",
            return_value=_mixed_corpus(),
        ),
        patch(
            "services.graphrag.domain_scoring.score_document_affinity",
            return_value={},
        ),
        patch(
            "services.graphrag.domain_scoring.entity_resolves_to_workbook",
            return_value=True,
        ),
        patch(
            "services.graphrag.domain_scoring.resolve_workbook_intent_guarded",
            return_value="table",
        ),
    ):
        result = score_query_domain(client_id, "What is TABLE_A used for?", signals)
    assert result.workbook_score >= result.narrative_score
    assert result.entity_in_workbook is True


def test_entity_missing_downgrades_workbook_intent():
    client_id = str(uuid4())
    signals = {
        "workbook_intent": "table",
        "entity_table": "UNKNOWN_TABLE",
        "column_name": None,
        "sheet_hint": None,
        "quoted_definition": None,
    }
    with (
        patch(
            "services.graphrag.domain_scoring.entity_resolves_to_workbook",
            return_value=False,
        ),
        patch(
            "services.graphrag.domain_scoring._sheet_matches_client",
            return_value=False,
        ),
        patch(
            "services.graphrag.domain_scoring._has_structural_workbook_signals",
            return_value=False,
        ),
    ):
        intent = resolve_workbook_intent_guarded(
            client_id, "What fields are in UNKNOWN_TABLE?", signals
        )
    assert intent == "general"


def test_sheet_match_allows_workbook_intent():
    client_id = str(uuid4())
    signals = {
        "workbook_intent": "column",
        "entity_table": None,
        "column_name": "OrderId",
        "sheet_hint": "Sheet1",
        "quoted_definition": None,
    }
    with (
        patch(
            "services.graphrag.domain_scoring.entity_resolves_to_workbook",
            return_value=False,
        ),
        patch(
            "services.graphrag.domain_scoring._sheet_matches_client",
            return_value=True,
        ),
    ):
        intent = resolve_workbook_intent_guarded(
            client_id, "What is the datatype for OrderId on Sheet1?", signals
        )
    assert intent == "column"
