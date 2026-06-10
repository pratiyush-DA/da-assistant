from unittest.mock import patch
from uuid import uuid4

from services.graphrag.client_corpus import ClientCorpusProfile, ClientDocument
from services.graphrag.domain_scoring import score_query_domain


def _mixed_corpus():
    return ClientCorpusProfile(
        client_id="c1",
        documents=(
            ClientDocument("d1", "upgrade_plan.pdf", "pdf", frozenset({"row"})),
            ClientDocument("d2", "dict.xlsx", "xlsx", frozenset({"column"})),
        ),
        has_narrative=True,
        has_workbook=True,
        is_mixed=True,
    )


def test_narrative_list_boosts_pdf_domain():
    client_id = str(uuid4())
    signals = {
        "workbook_intent": "general",
        "entity_table": None,
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
            return_value={"d1": 0.8, "d2": 0.1},
        ),
    ):
        result = score_query_domain(
            client_id,
            "List the five key client requirements defined in the change request",
            signals,
        )
    assert result.workbook_intent == "general"
    assert result.narrative_score > result.workbook_score
    assert result.domain in ("narrative", "mixed", "general")
