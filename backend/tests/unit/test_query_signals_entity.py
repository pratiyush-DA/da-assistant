from unittest.mock import patch
from uuid import uuid4

from services.graphrag.query_signals import (
    extract_column_name,
    extract_entity_table_name,
    extract_quoted_definition,
    extract_table_for_column,
    parse_query_signals,
)
from services.graphrag.workbook_rag import classify_query_domain, classify_workbook_query


def test_extract_customer_table():
    assert (
        extract_entity_table_name("What is the purpose of the Customer table?")
        == "Customer"
    )


@patch("services.graphrag.client_catalog.get_sheet_index")
def test_sheet_hint_from_client_index(mock_index):
    client_id = uuid4()
    mock_index.return_value = {
        "Fields": frozenset({"column"}),
        "Tables": frozenset({"table_catalog", "table_definition"}),
    }
    signals = parse_query_signals("columns on the Fields sheet", client_id)
    assert signals["sheet_hint"] == "Fields"


def test_extract_column_combined_definition_datatype():
    q = "What is the definition and datatype of OrderId?"
    from services.graphrag.query_signals import extract_column_name

    assert extract_column_name(q) == "OrderId"


def test_extract_table_for_column_section():
    q = (
        "On the FOIA Fields sheet, for table SectionI-1, what is the "
        "ColumnDefinition for the column FullNameofPointofContact?"
    )
    assert extract_table_for_column(q) == "SectionI-1"
    assert extract_column_name(q) == "FullNameofPointofContact"


def test_quoted_definition_for_reverse_lookup():
    q = (
        'which table name has the following table definition '
        '"Organization responsible for issuing the FOIA annual report"'
    )
    assert extract_quoted_definition(q) is not None
    assert classify_workbook_query(
        q, quoted_definition=extract_quoted_definition(q)
    ) == "table_by_definition"


@patch("services.graphrag.client_catalog.get_sheet_index")
def test_fuzzy_sheet_hint_foia_tables(mock_index):
    client_id = uuid4()
    mock_index.return_value = {
        "FOIA Tables": frozenset({"table_definition"}),
        "FOIA Fields": frozenset({"column"}),
    }
    signals = parse_query_signals(
        "in FOIA Table sheet, which table has a definition", client_id
    )
    assert signals["sheet_hint"] == "FOIA Tables"


def test_phase1_dictionary_cross_domain_is_general():
    q = (
        "How does Phase 1 document ingestion relate to the "
        "spreadsheet data dictionary metadata?"
    )
    assert classify_query_domain(q) == "general"
