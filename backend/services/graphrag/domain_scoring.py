"""Scored domain classification and guarded workbook intent (client-scoped)."""

import re
from dataclasses import dataclass

from django.conf import settings

from services.graphrag.client_catalog import get_sheet_index, resolve_sheet_hint
from services.graphrag.client_corpus import (
    document_for_id,
    entity_resolves_to_workbook,
    get_client_corpus_profile,
    score_document_affinity,
    top_affinity_document_id,
    document_is_narrative_only,
    document_is_workbook_only,
)
from services.graphrag.workbook_rag import (
    NARRATIVE_PERSONNEL_PATTERN,
    NARRATIVE_QUERY_PATTERN,
    WORKBOOK_QUERY_PATTERN,
    _narrative_query_strength,
    _workbook_query_strength,
    _query_spans_both_domains,
    classify_workbook_query,
    query_has_narrative_personnel_signals,
    query_is_strict_catalog,
)

GUARDED_WORKBOOK_INTENTS = frozenset({
    "catalog",
    "table",
    "table_by_definition",
    "database",
    "column",
    "code",
})

STRUCTURAL_WORKBOOK_PATTERN = re.compile(
    r"\b(datatype|data\s*type|column\s+definition|columndefinition|code\s*set|permissible)\b",
    re.I,
)

NARRATIVE_LIST_PATTERN = re.compile(
    r"(?:"
    r"\blist\s+the\s+\d+\b|"
    r"\blist\s+\d+\b|"
    r"\bhow\s+many\s+.{0,60}\bfields?\b|"
    r"\brequirements?\s+defined\s+in\b|"
    r"\bexplicitly\s+named\s+.{0,80}\bfields?\b"
    r")",
    re.I,
)


@dataclass(frozen=True)
class DomainScoreResult:
    domain: str
    narrative_score: float
    workbook_score: float
    workbook_intent: str
    workbook_confidence: float
    document_affinity: dict[str, float]
    entity_in_workbook: bool | None


def _has_structural_workbook_signals(query: str) -> bool:
    return bool(STRUCTURAL_WORKBOOK_PATTERN.search(query))


def _sheet_matches_client(client_id, query: str) -> bool:
    sheet_index = get_sheet_index(client_id)
    return resolve_sheet_hint(query, sheet_index) is not None


def resolve_workbook_intent_guarded(
    client_id,
    query: str,
    signals: dict,
) -> str:
    raw = classify_workbook_query(
        query,
        quoted_definition=signals.get("quoted_definition"),
        entity_table=signals.get("entity_table"),
        column_name=signals.get("column_name"),
        sheet_hint=signals.get("sheet_hint"),
    )
    if raw not in GUARDED_WORKBOOK_INTENTS:
        return raw
    if raw == "catalog":
        if _sheet_matches_client(client_id, query):
            return raw
        if query_is_strict_catalog(query):
            return raw
        return "general"

    entity_table = signals.get("entity_table")
    column_name = signals.get("column_name")
    entity_ok = False
    if entity_table and entity_resolves_to_workbook(client_id, entity_table):
        entity_ok = True
    if column_name and entity_resolves_to_workbook(client_id, column_name):
        entity_ok = True
    if _sheet_matches_client(client_id, query):
        return raw
    if _has_structural_workbook_signals(query):
        return raw
    if entity_ok:
        return raw
    if raw == "table_by_definition" and signals.get("quoted_definition"):
        return raw
    return "general"


def score_query_domain(client_id, query: str, signals: dict) -> DomainScoreResult:
    profile = get_client_corpus_profile(client_id)
    affinity = score_document_affinity(client_id, query)
    wb_intent = resolve_workbook_intent_guarded(client_id, query, signals)

    narrative_score = float(_narrative_query_strength(query))
    workbook_score = float(_workbook_query_strength(query))

    if NARRATIVE_QUERY_PATTERN.search(query):
        narrative_score += 2.0
    if WORKBOOK_QUERY_PATTERN.search(query):
        workbook_score += 2.0
    if query_has_narrative_personnel_signals(query):
        narrative_score += settings.RAG_SCORE_PERSONNEL
    if _has_structural_workbook_signals(query):
        workbook_score += settings.RAG_SCORE_STRUCT_WB
    if _sheet_matches_client(client_id, query):
        workbook_score += settings.RAG_SCORE_SHEET_MATCH

    entity_table = signals.get("entity_table")
    column_name = signals.get("column_name")
    entity_in_workbook: bool | None = None
    entity_token = entity_table or column_name
    if entity_token:
        entity_in_workbook = entity_resolves_to_workbook(client_id, entity_token)
        if entity_in_workbook:
            workbook_score += settings.RAG_SCORE_ENTITY_MATCH
        else:
            narrative_score += settings.RAG_SCORE_ENTITY_MISS
            workbook_score = max(0.0, workbook_score - 2.0)

    top_doc_id = top_affinity_document_id(affinity, profile)
    if top_doc_id:
        top_doc = document_for_id(profile, top_doc_id)
        if top_doc and document_is_narrative_only(top_doc):
            narrative_score += 2.0
        elif top_doc and document_is_workbook_only(top_doc):
            workbook_score += 2.0

    if NARRATIVE_LIST_PATTERN.search(query):
        narrative_score += settings.RAG_SCORE_ENTITY_MISS
        if top_doc_id:
            top_doc = document_for_id(profile, top_doc_id)
            if top_doc and document_is_narrative_only(top_doc):
                narrative_score += 2.0
                workbook_score = max(0.0, workbook_score - 2.0)

    if query_has_narrative_personnel_signals(query):
        domain = "narrative"
    elif _query_spans_both_domains(query):
        domain = "mixed" if profile.is_mixed else "general"
    elif abs(narrative_score - workbook_score) < settings.RAG_DOMAIN_CONFIDENCE_MARGIN:
        domain = "mixed" if profile.is_mixed else "general"
    elif narrative_score >= workbook_score and narrative_score >= settings.RAG_MIN_DOMAIN_SCORE:
        domain = "narrative"
    elif workbook_score > narrative_score and workbook_score >= settings.RAG_MIN_DOMAIN_SCORE:
        domain = "workbook"
    elif narrative_score >= settings.RAG_MIN_DOMAIN_SCORE:
        domain = "narrative"
    elif workbook_score >= settings.RAG_MIN_DOMAIN_SCORE:
        domain = "workbook"
    else:
        domain = "general"

    if profile.is_mixed and domain == "general" and wb_intent == "general":
        if narrative_score > workbook_score:
            domain = "narrative"
        elif workbook_score > narrative_score:
            domain = "mixed"

    workbook_confidence = workbook_score
    return DomainScoreResult(
        domain=domain,
        narrative_score=narrative_score,
        workbook_score=workbook_score,
        workbook_intent=wb_intent,
        workbook_confidence=workbook_confidence,
        document_affinity=affinity,
        entity_in_workbook=entity_in_workbook,
    )
