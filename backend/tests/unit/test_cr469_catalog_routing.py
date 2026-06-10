"""Regression: CR-469-shaped narrative questions must not route to catalog."""

from services.graphrag.workbook_rag import classify_workbook_query, query_is_strict_catalog

FAILING_SHAPES = [
    "List the five key client requirements defined in CR-469 for the MONETARY_DETAIL table",
    "How many new fields are being added to the Promotional History tables and views?",
    "What are the seven explicitly named Rewards fields that must be added to the tables?",
]

PASSING_CATALOG = [
    "List 5 tables in the dataset",
    "What tables are in the dictionary?",
    "How many tables are in the workbook?",
]


def test_cr469_list_count_questions_not_catalog():
    for q in FAILING_SHAPES:
        assert classify_workbook_query(q) != "catalog", q
        assert not query_is_strict_catalog(q), q


def test_real_dictionary_catalog_questions_still_catalog():
    for q in PASSING_CATALOG:
        assert classify_workbook_query(q) == "catalog", q
        assert query_is_strict_catalog(q), q
