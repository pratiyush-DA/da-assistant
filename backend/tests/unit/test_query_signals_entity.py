from unittest.mock import patch
from uuid import uuid4

from services.graphrag.query_signals import (
    extract_entity_table_name,
    parse_query_signals,
)
from services.graphrag.workbook_rag import classify_query_domain


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


def test_phase1_dictionary_cross_domain_is_general():
    q = (
        "How does Phase 1 document ingestion relate to the "
        "spreadsheet data dictionary metadata?"
    )
    assert classify_query_domain(q) == "general"
