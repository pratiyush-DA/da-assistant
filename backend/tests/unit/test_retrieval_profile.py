from uuid import uuid4

from services.graphrag.retrieval_profile import resolve_retrieval_profile
from services.graphrag.workbook_rag import query_has_narrative_personnel_signals


def test_personnel_query_detected():
    q = "who is data engineer and where does he work?"
    assert query_has_narrative_personnel_signals(q)


def test_personnel_query_profile_domain_narrative():
    profile = resolve_retrieval_profile(uuid4(), "who is data engineer and where does he work?")
    assert profile.domain == "narrative"
    assert profile.inject_catalog is False
    assert profile.workbook_limit_ratio == 0.0
    assert profile.allowed_citation_types == frozenset({"row"})


def test_catalog_query_injects_catalog():
    profile = resolve_retrieval_profile(uuid4(), "List 5 tables in the dataset")
    assert profile.workbook_intent == "catalog"
    assert profile.inject_catalog is True
