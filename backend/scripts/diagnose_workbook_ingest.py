#!/usr/bin/env python
"""Dry-run workbook chunking for ReportTitle / catalog (Section 4.3)."""

import os
import sys
from pathlib import Path

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from services.chunking.workbook_chunker import WorkbookDictionaryChunker
from services.graphrag.context_extractors import parse_table_names_from_catalog
from services.parsing.excel_parser import parse_excel


def main(xlsx_path: str) -> int:
    path = Path(xlsx_path)
    if not path.exists():
        print(f"File not found: {path}")
        return 1

    elements = parse_excel(str(path))
    _, children = WorkbookDictionaryChunker().chunk(elements)

    print("=== ReportTitle column chunks (after dedupe) ===")
    count = 0
    for c in children:
        if c.chunk_type == "column" and c.column_name and "report" in c.column_name.lower():
            count += 1
            print(f"  table={c.table_name} col={c.column_name}")
            print(f"    {c.text[:200]}")
    if count == 0:
        print("  (none)")

    print("\n=== table_catalog chunks ===")
    for c in children:
        if c.chunk_type == "table_catalog":
            names = parse_table_names_from_catalog(c.text)
            print(f"  parseable names: {len(names)}")
            print(f"  sample: {', '.join(names[:8])}...")

    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/diagnose_workbook_ingest.py <path-to-xlsx>")
        sys.exit(1)
    sys.exit(main(sys.argv[1]))
