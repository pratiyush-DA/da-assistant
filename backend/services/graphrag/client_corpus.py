"""Client-scoped document corpus and workbook entity metadata from Neo4j."""

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from uuid import UUID

from django.conf import settings

from services.graphrag.workbook_rag import WORKBOOK_CHUNK_TYPES
from services.neo4j.driver import get_driver

_corpus_cache: dict[str, "ClientCorpusProfile"] = {}
_entity_index_cache: dict[str, "WorkbookEntityIndex"] = {}

NARRATIVE_CHUNK_TYPE = "row"


@dataclass(frozen=True)
class ClientDocument:
    id: str
    filename: str
    file_type: str
    chunk_types: frozenset[str]


@dataclass(frozen=True)
class ClientCorpusProfile:
    client_id: str
    documents: tuple[ClientDocument, ...]
    has_narrative: bool
    has_workbook: bool
    is_mixed: bool


@dataclass(frozen=True)
class WorkbookEntityIndex:
    table_names: frozenset[str]
    column_keys: frozenset[tuple[str, str]]


def clear_corpus_cache(client_id: UUID | str | None = None) -> None:
    if client_id is None:
        _corpus_cache.clear()
        _entity_index_cache.clear()
    else:
        key = str(client_id)
        _corpus_cache.pop(key, None)
        _entity_index_cache.pop(key, None)


def document_is_narrative_only(doc: ClientDocument) -> bool:
    if not doc.chunk_types:
        return False
    return doc.chunk_types <= {NARRATIVE_CHUNK_TYPE}


def document_is_workbook_only(doc: ClientDocument) -> bool:
    if not doc.chunk_types:
        return False
    return NARRATIVE_CHUNK_TYPE not in doc.chunk_types and bool(
        doc.chunk_types & WORKBOOK_CHUNK_TYPES
    )


def get_client_corpus_profile(client_id: UUID | str) -> ClientCorpusProfile:
    key = str(client_id)
    if key in _corpus_cache:
        return _corpus_cache[key]

    documents: list[ClientDocument] = []
    with get_driver().session(database=settings.NEO4J_DATABASE) as session:
        result = session.run(
            """
            MATCH (d:Document {client_id: $client_id})-[:HAS_CHUNK]->(:Chunk)
                  <-[:PART_OF]-(cc:ChildChunk)
            RETURN d.id AS id, d.filename AS filename, d.file_type AS file_type,
                   collect(DISTINCT cc.chunk_type) AS chunk_types
            """,
            client_id=key,
        )
        for record in result:
            types = frozenset(t for t in (record["chunk_types"] or []) if t)
            documents.append(
                ClientDocument(
                    id=str(record["id"]),
                    filename=record["filename"] or "",
                    file_type=record["file_type"] or "",
                    chunk_types=types,
                )
            )

    has_narrative = any(NARRATIVE_CHUNK_TYPE in d.chunk_types for d in documents)
    has_workbook = any(d.chunk_types & WORKBOOK_CHUNK_TYPES for d in documents)
    profile = ClientCorpusProfile(
        client_id=key,
        documents=tuple(documents),
        has_narrative=has_narrative,
        has_workbook=has_workbook,
        is_mixed=has_narrative and has_workbook,
    )
    _corpus_cache[key] = profile
    return profile


def get_workbook_entity_index(client_id: UUID | str) -> WorkbookEntityIndex:
    key = str(client_id)
    if key in _entity_index_cache:
        return _entity_index_cache[key]

    table_names: set[str] = set()
    column_keys: set[tuple[str, str]] = set()
    with get_driver().session(database=settings.NEO4J_DATABASE) as session:
        result = session.run(
            """
            MATCH (cc:ChildChunk {client_id: $client_id})
            WHERE cc.table_name IS NOT NULL AND cc.table_name <> ''
            RETURN DISTINCT cc.table_name AS table_name, cc.column_name AS column_name
            """,
            client_id=key,
        )
        for record in result:
            table = (record.get("table_name") or "").strip()
            if table:
                table_names.add(table)
            col = (record.get("column_name") or "").strip()
            if table and col:
                column_keys.add((table, col))

    index = WorkbookEntityIndex(
        table_names=frozenset(table_names),
        column_keys=frozenset(column_keys),
    )
    _entity_index_cache[key] = index
    return index


def _normalize_entity(token: str) -> str:
    return re.sub(r"\s+", " ", token.strip().lower())


def entity_resolves_to_workbook(
    client_id: UUID | str,
    token: str | None,
    *,
    threshold: float = 0.85,
) -> bool:
    if not token or not token.strip():
        return False
    index = get_workbook_entity_index(client_id)
    norm = _normalize_entity(token)
    for name in index.table_names:
        name_norm = _normalize_entity(name)
        if norm == name_norm:
            return True
        ratio = SequenceMatcher(None, norm, name_norm).ratio()
        if norm in name_norm or name_norm in norm:
            ratio = max(ratio, 0.9)
        if ratio >= threshold:
            return True
    for table, col in index.column_keys:
        for candidate in (col, f"{table}.{col}"):
            cand_norm = _normalize_entity(candidate)
            if norm == cand_norm:
                return True
            ratio = SequenceMatcher(None, norm, cand_norm).ratio()
            if ratio >= threshold:
                return True
    return False


def _tokenize_for_affinity(text: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9]{3,}", text.lower())
    return set(tokens)


def _filename_tokens(filename: str) -> set[str]:
    stem = re.sub(r"\.[^.]+$", "", filename.lower())
    parts = re.split(r"[-_\s.]+", stem)
    return {p for p in parts if len(p) >= 3}


def score_document_affinity(client_id: UUID | str, query: str) -> dict[str, float]:
    profile = get_client_corpus_profile(client_id)
    if not profile.documents:
        return {}

    query_tokens = _tokenize_for_affinity(query)
    scores: dict[str, float] = {}
    for doc in profile.documents:
        file_tokens = _filename_tokens(doc.filename)
        if not file_tokens and not query_tokens:
            scores[doc.id] = 0.0
            continue
        if not file_tokens:
            scores[doc.id] = 0.0
            continue
        intersection = query_tokens & file_tokens
        union = query_tokens | file_tokens
        jaccard = len(intersection) / len(union) if union else 0.0
        filename_lower = doc.filename.lower()
        query_lower = query.lower()
        substring_boost = 0.0
        for tok in file_tokens:
            if len(tok) >= 4 and tok in query_lower:
                substring_boost = max(substring_boost, 0.35)
        ratio = SequenceMatcher(None, query_lower, filename_lower).ratio()
        scores[doc.id] = min(1.0, max(jaccard, ratio * 0.5, substring_boost))
    return scores


def top_affinity_document_id(
    affinity: dict[str, float], profile: ClientCorpusProfile
) -> str | None:
    if not affinity:
        return None
    best_id = max(affinity, key=lambda k: affinity[k])
    if affinity[best_id] < getattr(settings, "RAG_AFFINITY_MIN_SCORE", 0.3):
        return None
    return best_id


def document_for_id(profile: ClientCorpusProfile, document_id: str) -> ClientDocument | None:
    for doc in profile.documents:
        if doc.id == document_id:
            return doc
    return None
