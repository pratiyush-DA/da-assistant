"""Multi-hop retrieval: tables -> columns/code_sets with query expansion."""

import math
import re
from uuid import UUID

from django.conf import settings

from services.graphrag.client_catalog import get_distinct_table_names
from services.graphrag.context_extractors import catalog_chunk_has_parseable_names
from services.graphrag.hybrid_retriever import hybrid_search, rrf_merge
from services.graphrag.metadata_lookup import (
    fetch_catalog_chunk,
    fetch_table_definition,
    lookup_column_chunks,
)
from services.graphrag.query_expansion import expand_query
from services.graphrag.query_signals import parse_query_signals
from services.graphrag.retriever import RetrievedChunk, rerank_chunks
from services.graphrag.workbook_rag import (
    NO_COLUMN_SECONDARY_INTENTS,
    classify_query_domain,
    classify_workbook_query,
    client_has_workbook_chunks,
    intent_chunk_types,
)


def _unique_table_names(chunks: list[RetrievedChunk]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for c in chunks:
        if c.table_name and c.table_name not in seen:
            seen.add(c.table_name)
            names.append(c.table_name)
    return names


def _hits_to_dicts(hits: list[RetrievedChunk]) -> list[dict]:
    return [
        {
            "id": h.id,
            "chunk_text": h.chunk_text,
            "child_text": h.child_text,
            "section_header": h.section_header,
            "page_number": h.page_number,
            "document_id": h.document_id,
            "source": h.source,
            "chunk_type": h.chunk_type,
            "sheet_name": h.sheet_name,
            "table_name": h.table_name,
            "column_name": h.column_name,
            "score": h.score,
        }
        for h in hits
    ]


def _dicts_to_chunks(merged: list[RetrievedChunk], limit: int) -> list[RetrievedChunk]:
    seen: set[str] = set()
    out: list[RetrievedChunk] = []
    for c in merged:
        key = f"{c.document_id}:{c.chunk_type}:{c.table_name}:{c.column_name}:{c.id}"
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
        if len(out) >= limit:
            break
    return out


def pin_anchor_chunks(
    chunks: list[RetrievedChunk],
    anchors: list[RetrievedChunk],
    limit: int,
) -> list[RetrievedChunk]:
    """Prepend required chunks (database, catalog, named table) then fill to limit."""
    if not anchors:
        return _dicts_to_chunks(chunks, limit)

    seen: set[str] = set()
    out: list[RetrievedChunk] = []
    for a in anchors:
        key = f"{a.document_id}:{a.id}"
        if key in seen:
            continue
        seen.add(key)
        out.append(a)

    for c in chunks:
        if len(out) >= limit:
            break
        key = f"{c.document_id}:{c.id}"
        if key in seen:
            continue
        seen.add(key)
        out.append(c)

    return out[:limit]


def _column_anchor_score(col: str, hit: RetrievedChunk) -> int:
    """Rank column hits: identifier match, Definition content, Datatype present."""
    body = hit.child_text or hit.chunk_text or ""
    body_l = body.lower()
    col_norm = col.lower().replace(" ", "")
    if col_norm not in body_l.replace(" ", ""):
        return -1
    score = 0
    if "definition:" in body_l:
        def_part = body_l.split("definition:", 1)[-1].strip()
        if def_part and def_part not in ("", "n/a", "none"):
            score += 100 + min(len(def_part), 200)
    if "datatype:" in body_l:
        score += 50
    return score


def _synthetic_catalog_chunk(table_names: list[str]) -> RetrievedChunk | None:
    if not table_names:
        return None
    names = ", ".join(table_names)
    text = f"Table catalog (derived): {names}"
    return RetrievedChunk(
        id="catalog-derived",
        chunk_text=text,
        section_header="Table catalog",
        page_number=None,
        document_id="",
        source="derived",
        score=1.0,
        chunk_type="table_catalog",
        child_text=text,
    )


def _rank_table_def(entity: str | None, hits: list[RetrievedChunk]) -> list[RetrievedChunk]:
    if not entity:
        return hits
    ent_lower = entity.lower()

    def key(c: RetrievedChunk) -> tuple:
        match = (c.table_name or "").lower() == ent_lower
        return (0 if match else 1, -c.score)

    return sorted(hits, key=key)


def _anchor_is_sufficient_column(anchor: RetrievedChunk) -> bool:
    body = (anchor.child_text or anchor.chunk_text or "").lower()
    return "definition:" in body and "datatype:" in body


def catalog_fallback_anchor(client_id: UUID | str) -> RetrievedChunk | None:
    """When no table_catalog chunk exists, list tables from table_definition rows."""
    return _synthetic_catalog_chunk(get_distinct_table_names(client_id))


def fetch_anchor_chunks(
    client_id: UUID | str,
    query: str,
    intent: str,
    signals: dict,
    limit: int,
) -> list[RetrievedChunk]:
    """Fetch must-have chunks for table/database/catalog/column intents."""
    sheet_hint = signals.get("sheet_hint")
    anchors: list[RetrievedChunk] = []

    if intent == "database":
        hits = hybrid_search(
            client_id,
            query,
            limit=3,
            chunk_types=["database"],
            sheet_hint=sheet_hint,
        )
        if hits:
            anchors.append(hits[0])

    elif intent == "catalog":
        meta_catalog = fetch_catalog_chunk(client_id)
        if meta_catalog:
            anchors.append(meta_catalog)
        else:
            hits = hybrid_search(
                client_id,
                query,
                limit=3,
                chunk_types=["table_catalog"],
                sheet_hint=sheet_hint,
            )
            for h in hits:
                if catalog_chunk_has_parseable_names(h):
                    anchors.append(h)
                    break
            if not anchors:
                fallback = catalog_fallback_anchor(client_id)
                if fallback:
                    anchors.append(fallback)

    elif intent == "table":
        entity = signals.get("entity_table") or signals.get("table_hint")
        if entity:
            meta_def = fetch_table_definition(client_id, entity)
            if meta_def:
                anchors.append(meta_def)
        if not anchors:
            table_names = [entity] if entity else None
            search_q = f"Table: {entity}" if entity else query
            hits = hybrid_search(
                client_id,
                search_q,
                limit=5,
                chunk_types=["table_definition"],
                table_names=table_names,
                sheet_hint=sheet_hint,
            )
            ranked = _rank_table_def(entity, hits)
            if ranked:
                anchors.append(ranked[0])

    elif intent == "column":
        col = signals.get("column_name")
        if col:
            meta_hits = lookup_column_chunks(client_id, col, limit=5)
            if meta_hits:
                anchors.append(meta_hits[0])
            else:
                hits = hybrid_search(
                    client_id,
                    col,
                    limit=8,
                    chunk_types=["column"],
                    sheet_hint=sheet_hint,
                    column_names=[col],
                )
                scored = [(h, _column_anchor_score(col, h)) for h in hits]
                scored = [(h, s) for h, s in scored if s >= 0]
                if scored:
                    scored.sort(key=lambda x: x[1], reverse=True)
                    anchors.append(scored[0][0])
                elif hits:
                    anchors.append(hits[0])

    return anchors


def _intent_exclusive_chunks(
    intent: str,
    anchors: list[RetrievedChunk],
    merged: list[RetrievedChunk],
    limit: int,
    *,
    column_name: str | None = None,
) -> list[RetrievedChunk]:
    """Restrict merged context to intent-appropriate chunk types."""
    if intent == "catalog":
        allowed = {"table_catalog"}
        filtered = [c for c in merged if (c.chunk_type or "") in allowed]
        if not filtered and anchors:
            return pin_anchor_chunks([], anchors, min(limit, 2))
        return pin_anchor_chunks(filtered, anchors, min(limit, 2))

    if intent == "column" and column_name:
        filtered = [c for c in merged if (c.chunk_type or "") == "column"]
        return pin_anchor_chunks(filtered, anchors, min(limit, 3))

    if intent not in NO_COLUMN_SECONDARY_INTENTS or not anchors:
        return merged

    allowed = set(intent_chunk_types(intent))
    if intent == "table":
        allowed = {"table_definition"}
    elif intent == "database":
        allowed = {"database", "overview"}
    filtered = [c for c in merged if (c.chunk_type or "") in allowed]
    cap = 1 if intent in ("table", "database") else limit
    return pin_anchor_chunks(filtered, anchors, min(limit, cap))


def apply_document_diversity(
    chunks: list[RetrievedChunk],
    limit: int,
    min_documents: int = 2,
) -> list[RetrievedChunk]:
    """Ensure chunks span multiple documents when available."""
    if len(chunks) <= limit:
        return chunks

    doc_ids = {c.document_id for c in chunks if c.document_id}
    if len(doc_ids) < min_documents:
        return _dicts_to_chunks(chunks, limit)

    selected: list[RetrievedChunk] = []
    seen_ids: set[str] = set()
    seen_docs: set[str] = set()

    for c in chunks:
        if c.document_id and c.document_id not in seen_docs:
            key = f"{c.document_id}:{c.id}"
            if key not in seen_ids:
                selected.append(c)
                seen_ids.add(key)
                seen_docs.add(c.document_id)
        if len(seen_docs) >= min_documents:
            break

    for c in chunks:
        if len(selected) >= limit:
            break
        key = f"{c.document_id}:{c.id}"
        if key in seen_ids:
            continue
        selected.append(c)
        seen_ids.add(key)

    return selected[:limit]


def mixed_document_search(
    client_id: UUID | str,
    query: str,
    limit: int | None = None,
) -> list[RetrievedChunk]:
    """Dual-path retrieval for clients with both workbook and narrative documents."""
    limit = limit or settings.VECTOR_SEARCH_LIMIT
    domain = classify_query_domain(query)
    if domain == "narrative":
        narr_limit = limit
        wb_limit = 0
    elif domain == "workbook":
        narr_limit = 0
        wb_limit = limit
    else:
        q_lower = query.lower()
        has_wb_tokens = bool(
            re.search(
                r"\b(column|table|datatype|database|dictionary|spreadsheet|schema|catalog)\b",
                q_lower,
                re.I,
            )
        )
        if not has_wb_tokens:
            narr_limit = max(math.ceil(limit * 0.75), 1)
            wb_limit = max(math.floor(limit * 0.25), 0)
        else:
            narr_limit = max(math.ceil(limit * 0.55), 1)
            wb_limit = max(math.floor(limit * 0.45), 1)

    narrative_hits: list[RetrievedChunk] = []
    workbook_hits: list[RetrievedChunk] = []
    if narr_limit > 0:
        narrative_hits = hybrid_search(
            client_id, query, limit=narr_limit, chunk_types=["row"]
        )
    if wb_limit > 0:
        workbook_hits = workbook_multi_hop_search(client_id, query, limit=wb_limit)

    lists: list[list[dict]] = []
    if narrative_hits:
        lists.append(_hits_to_dicts(narrative_hits))
    if workbook_hits:
        lists.append(_hits_to_dicts(workbook_hits))

    if not lists:
        return hybrid_search(client_id, query, limit=limit)

    merged = rrf_merge(lists)
    diversified = apply_document_diversity(merged, limit)
    return rerank_chunks(query, diversified)


def workbook_multi_hop_search(
    client_id: UUID | str,
    query: str,
    limit: int | None = None,
) -> list[RetrievedChunk]:
    limit = limit or settings.VECTOR_SEARCH_LIMIT
    signals = parse_query_signals(query, client_id)
    expanded = expand_query(query)
    intent = classify_workbook_query(query)
    anchors = fetch_anchor_chunks(client_id, query, intent, signals, limit)
    col_name = signals.get("column_name")
    col_names_param = [col_name] if col_name else None

    if intent == "catalog":
        if anchors:
            return pin_anchor_chunks([], anchors, min(limit, 2))
        primary_lists: list[list] = []
        for q in expanded[:3]:
            hits = hybrid_search(
                client_id,
                q,
                limit=4,
                chunk_types=["table_catalog"],
                sheet_hint=signals.get("sheet_hint"),
            )
            if hits:
                primary_lists.append(_hits_to_dicts(hits))
        primary_chunks = rrf_merge(primary_lists) if primary_lists else []
        exclusive = _intent_exclusive_chunks(
            intent, anchors, primary_chunks, min(limit, 2)
        )
        return rerank_chunks(query, exclusive)

    if intent == "column" and anchors and _anchor_is_sufficient_column(anchors[0]):
        return pin_anchor_chunks([], anchors, min(limit, 3))

    primary_types = intent_chunk_types(intent)
    if intent == "catalog":
        primary_types = ["table_catalog"]
    entity_table = signals.get("entity_table")
    table_names_filter = [entity_table] if entity_table and intent == "table" else None

    primary_lists = []
    search_limit = 3 if intent == "column" else limit
    for q in expanded[:4]:
        hits = hybrid_search(
            client_id,
            q,
            limit=search_limit,
            chunk_types=primary_types,
            table_names=table_names_filter,
            sheet_hint=signals.get("sheet_hint"),
            column_names=col_names_param if intent == "column" else None,
        )
        if hits:
            primary_lists.append(_hits_to_dicts(hits))

    primary_chunks = rrf_merge(primary_lists) if primary_lists else []

    table_names = _unique_table_names(primary_chunks)
    if entity_table and entity_table not in table_names:
        table_names.append(entity_table)

    if intent in ("column", "general") and not table_names:
        table_lists: list[list] = []
        for q in expanded[:3]:
            hits = hybrid_search(
                client_id,
                q,
                limit=5,
                chunk_types=["table_definition", "table_catalog"],
                sheet_hint=signals.get("sheet_hint"),
            )
            if hits:
                table_lists.append(_hits_to_dicts(hits))
        if table_lists:
            table_chunks = rrf_merge(table_lists)
            table_names = _unique_table_names(table_chunks)
            primary_chunks = rrf_merge(
                [_hits_to_dicts(primary_chunks), _hits_to_dicts(table_chunks)]
            )

    secondary_chunks: list[RetrievedChunk] = []
    skip_secondary = intent == "column" and anchors and _anchor_is_sufficient_column(
        anchors[0]
    )
    if intent not in NO_COLUMN_SECONDARY_INTENTS and not skip_secondary:
        secondary_types = ["column", "code_set"]
        if signals.get("wants_code_sets"):
            secondary_types = ["code_set", "column", "table_definition"]

        col_filter = table_names if table_names else None
        secondary_limit = 3 if intent == "column" else limit

        secondary_lists: list[list] = []
        for q in expanded[:3] if intent == "column" else expanded:
            hits = hybrid_search(
                client_id,
                q,
                limit=secondary_limit,
                chunk_types=secondary_types,
                table_names=col_filter,
                sheet_hint=signals.get("sheet_hint"),
                column_names=col_names_param if intent == "column" else None,
            )
            if hits:
                secondary_lists.append(_hits_to_dicts(hits))
        secondary_chunks = rrf_merge(secondary_lists) if secondary_lists else []

    merge_inputs: list[list[dict]] = []
    if primary_chunks:
        merge_inputs.append(_hits_to_dicts(primary_chunks))
    if secondary_chunks:
        merge_inputs.append(_hits_to_dicts(secondary_chunks))
    merged = rrf_merge(merge_inputs) if merge_inputs else []

    if len(merged) < 3 and intent in NO_COLUMN_SECONDARY_INTENTS:
        fallback_lists = []
        fallback_types = (
            ["table_catalog"] if intent == "catalog" else primary_types
        )
        for q in expanded[:2]:
            hits = hybrid_search(
                client_id,
                q,
                limit=settings.FULLTEXT_SEARCH_LIMIT,
                chunk_types=fallback_types,
                table_names=table_names_filter,
                sheet_hint=signals.get("sheet_hint"),
                column_names=col_names_param if intent == "column" else None,
                vector_only=False,
            )
            if hits:
                fallback_lists.append(_hits_to_dicts(hits))
        if fallback_lists:
            all_lists = list(fallback_lists)
            if merged:
                all_lists.insert(0, _hits_to_dicts(merged))
            merged = rrf_merge(all_lists)

    cap = min(limit, 3) if intent == "column" else limit
    capped = _dicts_to_chunks(merged, cap)
    exclusive = _intent_exclusive_chunks(
        intent, anchors, capped, cap, column_name=col_name
    )
    ranked = rerank_chunks(query, exclusive)
    return pin_anchor_chunks(ranked, anchors, cap)


def multi_hop_search(
    client_id: UUID | str,
    query: str,
    limit: int | None = None,
) -> list[RetrievedChunk]:
    """Legacy dictionary multi-hop; delegates to workbook path when workbook chunks exist."""
    if client_has_workbook_chunks(client_id):
        return workbook_multi_hop_search(client_id, query, limit=limit)

    limit = limit or settings.VECTOR_SEARCH_LIMIT
    signals = parse_query_signals(query, client_id)
    expanded = expand_query(query)

    table_lists: list[list] = []
    for q in expanded[:3]:
        hits = hybrid_search(
            client_id,
            q,
            limit=5,
            chunk_types=["table"],
            sheet_hint=signals.get("sheet_hint"),
        )
        if hits:
            table_lists.append(_hits_to_dicts(hits))

    table_chunks = rrf_merge(table_lists) if table_lists else []
    table_names = _unique_table_names(table_chunks)

    column_lists: list[list] = []
    chunk_types = ["column", "code_set"]
    if signals.get("wants_code_sets"):
        chunk_types = ["code_set", "column", "table"]

    for q in expanded:
        hits = hybrid_search(
            client_id,
            q,
            limit=limit,
            chunk_types=chunk_types,
            table_names=table_names if table_names else None,
            sheet_hint=signals.get("sheet_hint"),
        )
        if hits:
            column_lists.append(_hits_to_dicts(hits))

    column_chunks = rrf_merge(column_lists) if column_lists else []
    merged = rrf_merge(
        [_hits_to_dicts(table_chunks), _hits_to_dicts(column_chunks)]
    ) if table_chunks or column_chunks else []

    if len(merged) < 3:
        fallback_lists = []
        for q in expanded:
            hits = hybrid_search(
                client_id,
                q,
                limit=settings.FULLTEXT_SEARCH_LIMIT,
                chunk_types=["column", "code_set", "table"],
                vector_only=False,
            )
            if hits:
                fallback_lists.append(_hits_to_dicts(hits))
        if fallback_lists:
            all_lists = list(fallback_lists)
            if merged:
                all_lists.insert(0, _hits_to_dicts(merged))
            merged = rrf_merge(all_lists)

    return rerank_chunks(query, _dicts_to_chunks(merged, limit))


def client_has_dictionary_chunks(client_id: UUID | str) -> bool:
    """Backward-compatible alias for workbook chunk detection."""
    return client_has_workbook_chunks(client_id)
