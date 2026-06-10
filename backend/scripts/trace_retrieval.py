#!/usr/bin/env python
"""Trace retrieval path for a query (Section 4.4-4.5)."""

import os
import sys

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from services.graphrag.client_corpus import get_client_corpus_profile
from services.graphrag.context_extractors import catalog_names_from_chunks
from services.graphrag.query_signals import parse_query_signals
from services.graphrag.retrieval_profile import resolve_retrieval_profile
from services.graphrag.workbook_rag import (
    classify_query_domain,
    classify_workbook_query,
    client_has_workbook_chunks,
    client_is_mixed,
)
from services.langchain import streaming


def main(client_id: str, query: str) -> int:
    print(f"client_id: {client_id}")
    print(f"query: {query}")
    print(f"client_is_mixed: {client_is_mixed(client_id)}")
    print(f"classify_workbook_query: {classify_workbook_query(query)}")
    print(f"classify_query_domain: {classify_query_domain(query)}")
    print(f"client_has_workbook_chunks: {client_has_workbook_chunks(client_id)}")

    corpus = get_client_corpus_profile(client_id)
    print(f"\nClientCorpusProfile:")
    print(f"  documents: {len(corpus.documents)}")
    print(f"  has_narrative: {corpus.has_narrative}")
    print(f"  has_workbook: {corpus.has_workbook}")
    print(f"  is_mixed: {corpus.is_mixed}")
    for doc in corpus.documents[:8]:
        print(f"    - {doc.filename} types={sorted(doc.chunk_types)}")

    signals = parse_query_signals(query, client_id)
    entity = signals.get("entity_table") or signals.get("column_name")

    profile = resolve_retrieval_profile(client_id, query)
    print(f"\nretrieval_profile.domain: {profile.domain}")
    print(f"retrieval_profile.workbook_intent: {profile.workbook_intent}")
    print(f"retrieval_profile.narrative_score: {profile.narrative_score}")
    print(f"retrieval_profile.workbook_score: {profile.workbook_score}")
    print(f"retrieval_profile.workbook_confidence: {profile.workbook_confidence}")
    print(f"retrieval_profile.entity_in_workbook: {profile.entity_in_workbook}")
    print(f"retrieval_profile.inject_catalog: {profile.inject_catalog}")

    affinity = profile.document_affinity
    if affinity:
        top = sorted(affinity.items(), key=lambda kv: -kv[1])[:3]
        print(f"document_affinity (top 3): {top}")
    else:
        print("document_affinity: (none)")

    if entity:
        print(f"parsed entity token: {entity!r}")

    chunks = streaming._retrieve_chunks(client_id, query, profile)
    print(f"\nretrieved chunks: {len(chunks)}")
    for c in chunks:
        print(
            f"  - {c.chunk_type} doc={c.document_id[:8] if c.document_id else 'n/a'}... "
            f"table={c.table_name} col={c.column_name} source={c.source}"
        )

    result = streaming.retrieve_and_fit_context(client_id, query)
    print(f"\nfitted chunks: {len(result.fitted_chunks)}")
    for c in result.fitted_chunks:
        print(f"  - {c.chunk_type} source={c.source}")
    print(f"citation chunks: {len(result.citation_chunks)}")
    for c in result.citation_chunks:
        print(f"  - cite {c.chunk_type} source={c.source}")

    names = catalog_names_from_chunks(result.fitted_chunks)
    print(f"catalog_names_from_chunks: {len(names)} names")
    if names:
        print(f"  first 8: {', '.join(names[:8])}")

    print(f"\nuse_dictionary_prompt: {result.use_dictionary}")
    print(f"use_mixed_prompt: {result.use_mixed}")
    print(f"context starts with: {result.context[:120]!r}...")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/trace_retrieval.py <client_id> <query>")
        sys.exit(1)
    sys.exit(main(sys.argv[1], " ".join(sys.argv[2:])))
