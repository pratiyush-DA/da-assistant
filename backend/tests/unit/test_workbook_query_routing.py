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
    assert classify_workbook_query("What tables are in the dictionary?") == "catalog"
    assert classify_workbook_query("How many tables are in the workbook?") == "catalog"


def test_narrative_list_questions_are_not_catalog():
    q1 = "List the five key client requirements defined in the change request for TABLE_A"
    q2 = "How many new fields are being added to the promotional history tables and views?"
    q3 = "What are the seven explicitly named rewards fields that must be added to tables?"
    assert classify_workbook_query(q1) != "catalog"
    assert classify_workbook_query(q2) != "catalog"
    assert classify_workbook_query(q3) != "catalog"


def test_intent_chunk_types_database():
    types = intent_chunk_types("database")
    assert "database" in types


def test_table_by_definition_intent():
    q = (
        'which table name has the following table definition '
        '"Organization responsible for issuing the FOIA annual report"'
    )
    assert classify_workbook_query(q) == "table_by_definition"
    types = intent_chunk_types("table_by_definition")
    assert types == ["table_definition", "table_catalog"]


def test_column_intent_with_table_and_column():
    q = (
        "On the FOIA Fields sheet, for table SectionI-1, what is the "
        "ColumnDefinition for the column FullNameofPointofContact?"
    )
    assert classify_workbook_query(q) == "column"
