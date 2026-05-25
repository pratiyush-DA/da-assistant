import json

import pytest
from openpyxl import Workbook

from services.chunking import ParentChildChunker
from services.parsing.excel_parser import parse_excel


@pytest.fixture
def excel_elements(tmp_path):
    path = tmp_path / "chunk_test.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "BCV"
    ws.append(["ID", "Rule"])
    for i in range(30):
        ws.append([f"R-{i}", f"Business rule number {i} with detail"])
    wb.save(path)
    wb.close()
    return parse_excel(str(path))


def test_table_chunker_uses_sheet_section_headers(excel_elements):
    chunker = ParentChildChunker(parent_tokens=500, child_tokens=150)
    parents, children = chunker.chunk_elements(excel_elements)
    assert len(parents) >= 1
    assert all("BCV" in p.section_header for p in parents)
    assert len(children) >= 1


def test_table_chunker_preserves_json_rows_intact(excel_elements):
    chunker = ParentChildChunker(parent_tokens=10000, child_tokens=5000)
    parents, children = chunker.chunk_elements(excel_elements)
    combined = "\n".join(c.text for c in children)
    assert '"ID": "R-0"' in combined or '"ID": "R-1"' in combined
    first_row = next(e for e in excel_elements if e.category == "TableRow")
    parsed = json.loads(first_row.text)
    assert parsed["ID"] in combined


def test_table_chunker_splits_parents_by_token_budget(excel_elements):
    chunker = ParentChildChunker(parent_tokens=200, child_tokens=80)
    parents, _children = chunker.chunk_elements(excel_elements)
    assert len(parents) > 1


def test_narrative_path_not_used_for_excel(excel_elements):
    chunker = ParentChildChunker(parent_tokens=500, child_tokens=100)
    parents, _ = chunker.chunk_elements(excel_elements)
    for p in parents:
        assert "\n" in p.text or "{" in p.text
