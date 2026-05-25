from services.graphrag.workbook_rag import classify_workbook_query, intent_chunk_types


def test_database_intent():
    assert classify_workbook_query("What does the database represent?") == "database"


def test_table_intent():
    assert classify_workbook_query("What is the purpose of the Customer table?") == "table"


def test_column_intent():
    assert classify_workbook_query("What is OrderId datatype?") == "column"


def test_code_intent():
    assert classify_workbook_query("What is the meaning of status code 1?") == "code"


def test_catalog_intent():
    assert classify_workbook_query("List 5 tables in the dataset") == "catalog"


def test_intent_chunk_types_database():
    types = intent_chunk_types("database")
    assert "database" in types
