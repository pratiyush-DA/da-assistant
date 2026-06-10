"""Per-request retrieval and citation profile (file-agnostic)."""

from dataclasses import dataclass, field
from uuid import UUID

from services.graphrag.client_corpus import (
    document_for_id,
    get_client_corpus_profile,
    top_affinity_document_id,
    document_is_narrative_only,
    document_is_workbook_only,
)
from services.graphrag.domain_scoring import score_query_domain
from services.graphrag.query_signals import parse_query_signals
from services.graphrag.workbook_rag import (
    _query_spans_both_domains,
    client_has_workbook_chunks,
    intent_chunk_types,
    query_has_workbook_signals,
)

WORKBOOK_INTENTS = frozenset({
    "catalog",
    "table",
    "table_by_definition",
    "database",
    "column",
    "code",
})


@dataclass(frozen=True)
class RetrievalProfile:
    domain: str  # narrative | workbook | mixed | general
    workbook_intent: str
    is_mixed_client: bool
    has_workbook: bool
    allowed_retrieval_types: frozenset[str] = field(default_factory=frozenset)
    allowed_citation_types: frozenset[str] = field(default_factory=frozenset)
    inject_catalog: bool = False
    citation_budget: int = 8
    narrative_limit_ratio: float = 1.0
    workbook_limit_ratio: float = 0.0
    narrative_score: float = 0.0
    workbook_score: float = 0.0
    workbook_confidence: float = 0.0
    document_affinity: dict[str, float] = field(default_factory=dict)
    entity_in_workbook: bool | None = None
    focus_document_ids: tuple[str, ...] = ()


def _citation_types_for_intent(workbook_intent: str) -> frozenset[str]:
    types = set(intent_chunk_types(workbook_intent))
    if workbook_intent != "catalog":
        types.discard("table_catalog")
    return frozenset(types)


def _retrieval_types_for_domain(domain: str, workbook_intent: str) -> frozenset[str]:
    if domain == "narrative":
        return frozenset({"row"})
    if domain == "workbook":
        return frozenset(intent_chunk_types(workbook_intent))
    return frozenset({"row"}) | frozenset(intent_chunk_types(workbook_intent))


def _ratios_from_affinity(
    domain: str,
    wb_intent: str,
    message: str,
    affinity: dict[str, float],
    corpus_profile,
) -> tuple[float, float]:
    if domain == "narrative":
        return 1.0, 0.0
    if domain == "workbook":
        return 0.0, 1.0

    top_id = top_affinity_document_id(affinity, corpus_profile)
    if top_id:
        top_doc = document_for_id(corpus_profile, top_id)
        if top_doc and document_is_narrative_only(top_doc):
            return 0.85, 0.15
        if top_doc and document_is_workbook_only(top_doc):
            return 0.15, 0.85

    if query_has_workbook_signals(message, wb_intent):
        return 0.55, 0.45
    return 0.75, 0.25


def resolve_retrieval_profile(
    client_id: UUID | str,
    message: str,
    document_ids: list[str] | None = None,
) -> RetrievalProfile:
    signals = parse_query_signals(message, client_id)
    scored = score_query_domain(client_id, message, signals)
    corpus = get_client_corpus_profile(client_id)
    mixed = corpus.is_mixed
    has_wb = client_has_workbook_chunks(client_id)

    domain = scored.domain
    wb_intent = scored.workbook_intent

    if _query_spans_both_domains(message):
        domain = "mixed" if mixed else domain

    focus_ids: tuple[str, ...] = ()
    if document_ids:
        focus_ids = tuple(str(d) for d in document_ids)

    inject_catalog = wb_intent == "catalog"

    narr_ratio, wb_ratio = _ratios_from_affinity(
        domain, wb_intent, message, scored.document_affinity, corpus
    )

    if domain == "narrative":
        citation_types = frozenset({"row"})
    elif domain == "workbook":
        citation_types = _citation_types_for_intent(wb_intent)
    else:
        citation_types = frozenset({"row"}) | _citation_types_for_intent(wb_intent)
        if wb_intent != "catalog":
            citation_types = frozenset(
                t for t in citation_types if t != "table_catalog"
            )

    retrieval_types = _retrieval_types_for_domain(domain, wb_intent)

    return RetrievalProfile(
        domain=domain,
        workbook_intent=wb_intent,
        is_mixed_client=mixed,
        has_workbook=has_wb,
        allowed_retrieval_types=retrieval_types,
        allowed_citation_types=citation_types,
        inject_catalog=inject_catalog,
        citation_budget=8,
        narrative_limit_ratio=narr_ratio,
        workbook_limit_ratio=wb_ratio,
        narrative_score=scored.narrative_score,
        workbook_score=scored.workbook_score,
        workbook_confidence=scored.workbook_confidence,
        document_affinity=scored.document_affinity,
        entity_in_workbook=scored.entity_in_workbook,
        focus_document_ids=focus_ids,
    )
