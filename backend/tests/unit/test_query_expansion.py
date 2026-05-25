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
