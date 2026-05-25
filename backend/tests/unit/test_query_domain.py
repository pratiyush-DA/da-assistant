from services.graphrag.workbook_rag import classify_query_domain


def test_phase1_project_is_narrative():
    assert classify_query_domain("what is the phase 1 of the project") == "narrative"


def test_database_metadata_is_workbook():
    assert classify_query_domain("What does the database represent?") == "workbook"


def test_customer_table_purpose_is_workbook():
    assert (
        classify_query_domain("What is the purpose of the Customer table?") == "workbook"
    )


def test_ambiguous_defaults_general():
    assert classify_query_domain("tell me about the system") == "general"
