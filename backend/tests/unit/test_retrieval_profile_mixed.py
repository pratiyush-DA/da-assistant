from unittest.mock import patch
from uuid import uuid4

from services.graphrag.domain_scoring import DomainScoreResult
from services.graphrag.retrieval_profile import resolve_retrieval_profile


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


def test_ambiguous_query_resolves_mixed_domain():
    client_id = str(uuid4())
    scored = DomainScoreResult(
        domain="mixed",
        narrative_score=2.5,
        workbook_score=2.0,
        workbook_intent="general",
        workbook_confidence=2.0,
        document_affinity={"d1": 0.5},
        entity_in_workbook=False,
    )
    with (
        patch(
            "services.graphrag.retrieval_profile.get_client_corpus_profile",
            return_value=_mixed_corpus(),
        ),
        patch(
            "services.graphrag.retrieval_profile.score_query_domain",
            return_value=scored,
        ),
        patch(
            "services.graphrag.retrieval_profile.client_has_workbook_chunks",
            return_value=True,
        ),
    ):
        profile = resolve_retrieval_profile(
            client_id, "What tables are mentioned in the architecture section?"
        )
    assert profile.domain == "mixed"
    assert profile.workbook_intent == "general"
    assert profile.narrative_limit_ratio > profile.workbook_limit_ratio


def test_guarded_intent_not_forced_to_workbook_domain():
    client_id = str(uuid4())
    scored = DomainScoreResult(
        domain="narrative",
        narrative_score=4.0,
        workbook_score=1.0,
        workbook_intent="general",
        workbook_confidence=1.0,
        document_affinity={},
        entity_in_workbook=False,
    )
    with (
        patch(
            "services.graphrag.retrieval_profile.get_client_corpus_profile",
            return_value=_mixed_corpus(),
        ),
        patch(
            "services.graphrag.retrieval_profile.score_query_domain",
            return_value=scored,
        ),
        patch(
            "services.graphrag.retrieval_profile.client_has_workbook_chunks",
            return_value=True,
        ),
    ):
        profile = resolve_retrieval_profile(
            client_id, "Describe the database migration timeline in the project plan"
        )
    assert profile.domain == "narrative"
    assert profile.workbook_intent == "general"
