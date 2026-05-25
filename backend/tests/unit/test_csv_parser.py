import json

import pytest

from services.parsing.csv_parser import parse_csv
from services.parsing.router import parse_document
from services.parsing.table_rows import rows_to_sheet_elements


@pytest.fixture
def sample_csv_path(tmp_path):
    path = tmp_path / "payments.csv"
    path.write_text(
        "Requirement ID,Description,Priority\n"
        "REQ-001,Process invoices,High\n"
        "REQ-002,Send reminders,Medium\n",
        encoding="utf-8",
    )
    return path


def test_parse_csv_sheet_title_and_rows(sample_csv_path):
    elements = parse_csv(str(sample_csv_path))
    sheets = [e for e in elements if e.category == "SheetTitle"]
    rows = [e for e in elements if e.category == "TableRow"]
    assert len(sheets) == 1
    assert sheets[0].sheet_name == "payments"
    assert len(rows) == 2


def test_csv_table_row_json_shape(sample_csv_path):
    elements = parse_csv(str(sample_csv_path))
    row = next(e for e in elements if e.category == "TableRow")
    payload = json.loads(row.text)
    assert payload["sheet"] == "payments"
    assert payload["Requirement ID"] == "REQ-001"
    assert payload["Description"] == "Process invoices"


def test_parse_document_routes_csv_to_table_parser(sample_csv_path):
    elements = parse_document(str(sample_csv_path), "csv")
    assert any(e.category == "TableRow" for e in elements)
    assert any(e.category == "SheetTitle" for e in elements)
    assert not any(e.category == "NarrativeText" for e in elements)


def test_rows_to_sheet_elements_empty_returns_empty():
    assert rows_to_sheet_elements("Empty", []) == []


def test_validate_upload_accepts_xls():
    from apps.documents.file_types import validate_upload_filename

    assert validate_upload_filename("legacy.xls") == "xls"


@pytest.fixture
def sample_xls_path(tmp_path):
    xlwt = pytest.importorskip("xlwt")
    path = tmp_path / "requirements.xls"
    wb = xlwt.Workbook()
    ws = wb.add_sheet("Payments")
    ws.write(0, 0, "Requirement ID")
    ws.write(0, 1, "Description")
    ws.write(1, 0, "REQ-001")
    ws.write(1, 1, "Process invoices")
    wb.save(str(path))
    return path


def test_parse_xls_produces_table_rows(sample_xls_path):
    from services.parsing.xls_parser import parse_xls

    elements = parse_xls(str(sample_xls_path))
    rows = [e for e in elements if e.category == "TableRow"]
    assert len(rows) == 1
    payload = json.loads(rows[0].text)
    assert payload["Requirement ID"] == "REQ-001"


def test_parse_document_routes_xls(sample_xls_path):
    elements = parse_document(str(sample_xls_path), "xls")
    assert any(e.category == "TableRow" for e in elements)


def test_csv_chunker_uses_file_stem_as_section_header(sample_csv_path):
    from services.chunking import ParentChildChunker

    elements = parse_csv(str(sample_csv_path))
    chunker = ParentChildChunker(parent_tokens=500, child_tokens=150)
    parents, children = chunker.chunk_elements(elements)
    assert len(parents) >= 1
    assert any("payments" in p.section_header for p in parents)
    assert len(children) >= 1
