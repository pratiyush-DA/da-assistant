"""Per-request retrieval and citation profile (file-agnostic)."""

from dataclasses import dataclass, field
from uuid import UUID

from services.graphrag.query_signals import parse_query_signals
from services.graphrag.workbook_rag import (
    _query_spans_both_domains,
    classify_query_domain,
    client_has_workbook_chunks,
    client_is_mixed,
    intent_chunk_types,
    query_has_narrative_personnel_signals,
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
    domain: str  # narrative | workbook | mixed
    workbook_intent: str
    is_mixed_client: bool
    has_workbook: bool
    allowed_retrieval_types: frozenset[str] = field(default_factory=frozenset)
    allowed_citation_types: frozenset[str] = field(default_factory=frozenset)
    inject_catalog: bool = False
    citation_budget: int = 8
    narrative_limit_ratio: float = 1.0
    workbook_limit_ratio: float = 0.0


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


def resolve_retrieval_profile(
    client_id: UUID | str,
    message: str,
) -> RetrievalProfile:
    signals = parse_query_signals(message, client_id)
    wb_intent = signals.get("workbook_intent") or "general"
    mixed = client_is_mixed(client_id)
    has_wb = client_has_workbook_chunks(client_id)

    domain = classify_query_domain(message)

    if query_has_narrative_personnel_signals(message):
        domain = "narrative"

    if mixed and domain == "general" and not query_has_workbook_signals(
        message, wb_intent
    ):
        domain = "narrative"

    if wb_intent in WORKBOOK_INTENTS and domain != "narrative":
        domain = "workbook"

    if _query_spans_both_domains(message):
        domain = "mixed"

    inject_catalog = wb_intent == "catalog"

    if domain == "narrative":
        narr_ratio, wb_ratio = 1.0, 0.0
        citation_types = frozenset({"row"})
    elif domain == "workbook":
        narr_ratio, wb_ratio = 0.0, 1.0
        citation_types = _citation_types_for_intent(wb_intent)
    else:
        if query_has_workbook_signals(message, wb_intent):
            narr_ratio, wb_ratio = 0.55, 0.45
        else:
            narr_ratio, wb_ratio = 0.75, 0.25
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
    )
