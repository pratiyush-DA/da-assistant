#!/usr/bin/env python
"""Trace retrieval path for a query (Section 4.4-4.5)."""

import os
import sys

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from services.graphrag.context_extractors import catalog_names_from_chunks
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

    profile = resolve_retrieval_profile(client_id, query)
    print(f"retrieval_profile.domain: {profile.domain}")
    print(f"retrieval_profile.inject_catalog: {profile.inject_catalog}")

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
