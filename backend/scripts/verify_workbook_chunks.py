#!/usr/bin/env python
"""
Ops verification (Step 0): chunk_type counts and spot-checks for a client.

Usage (from backend/ with Django settings):
  python scripts/verify_workbook_chunks.py <client_id>
"""

import os
import sys

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from django.conf import settings  # noqa: E402
from services.graphrag.context_extractors import parse_table_names_from_catalog
from services.neo4j.driver import get_driver  # noqa: E402


def main(client_id: str) -> int:
    with get_driver().session(database=settings.NEO4J_DATABASE) as session:
        print("=== chunk_type counts ===")
        for r in session.run(
            """
            MATCH (cc:ChildChunk {client_id: $id})
            RETURN cc.chunk_type AS t, count(*) AS n
            ORDER BY n DESC
            """,
            id=client_id,
        ):
            print(f"  {r['t']}: {r['n']}")

        print("\n=== table_catalog sample ===")
        rec = session.run(
            """
            MATCH (cc:ChildChunk {client_id: $id, chunk_type: 'table_catalog'})
            RETURN cc.text AS text LIMIT 1
            """,
            id=client_id,
        ).single()
        if rec:
            text = rec["text"] or ""
            print(text[:500])
            names = parse_table_names_from_catalog(text)
            print(f"  parseable table names: {len(names)}")
        else:
            print("(none)")

        print("\n=== ReportTitle column rows (normalized column_name) ===")
        rt_count = 0
        for r in session.run(
            """
            MATCH (cc:ChildChunk {client_id: $id, chunk_type: 'column'})
            WHERE toLower(replace(cc.column_name, ' ', '')) = 'reporttitle'
            RETURN cc.table_name AS tbl, cc.text AS text
            """,
            id=client_id,
        ):
            rt_count += 1
            text = (r["text"] or "")[:300]
            has_dt = "datatype:" in text.lower() and "datatype: |" not in text.lower()
            flag = "HAS_DATATYPE" if has_dt else "EMPTY_DATATYPE"
            print(f"  [{flag}] table={r['tbl']}: {text}")
        if rt_count == 0:
            print("  (none — re-ingest may be needed)")

    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/verify_workbook_chunks.py <client_id>")
        sys.exit(1)
    sys.exit(main(sys.argv[1]))
