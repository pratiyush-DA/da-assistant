from services.graphrag.query_expansion import expand_query


def test_expand_catalog_intent():
    queries = expand_query("List all tables in the dataset")
    lower = [q.lower() for q in queries]
    assert "table catalog" in lower or "list of tables" in lower


def test_expand_column_intent_adds_definition_suffix():
    queries = expand_query("What is the datatype of OrderId?")
    assert any("OrderId definition" in q or "OrderId datatype" in q for q in queries)


def test_expand_includes_original():
    q = "code set meaning for status"
    queries = expand_query(q)
    assert queries[0] == q


def test_expand_table_by_definition_uses_quote_only():
    q = (
        'which table has table definition '
        '"Organization responsible for issuing the FOIA annual report"'
    )
    from services.graphrag.query_signals import parse_query_signals

    signals = parse_query_signals(q)
    queries = expand_query(q, signals=signals)
    assert signals["workbook_intent"] == "table_by_definition"
    assert not any(q.endswith(" columns") for q in queries)
    assert any("Organization responsible" in q for q in queries)


def test_expand_column_with_table_skips_columns_suffix():
    q = (
        "On FOIA Fields sheet, for table SectionI-1, ColumnDefinition for "
        "column FullNameofPointofContact"
    )
    from services.graphrag.query_signals import parse_query_signals

    signals = parse_query_signals(q)
    queries = expand_query(q, signals=signals)
    assert not any(qq.endswith(" columns") for qq in queries)
