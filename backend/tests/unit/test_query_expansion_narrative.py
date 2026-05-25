from services.graphrag.query_expansion import expand_query


def test_table_query_no_columns_suffix():
    expanded = expand_query("What is the purpose of the Customer table?")
    lower = [q.lower() for q in expanded]
    assert not any(q.endswith("columns") for q in lower)


def test_narrative_query_no_columns_suffix():
    expanded = expand_query("what is the phase 1 of the project")
    lower = [q.lower() for q in expanded]
    assert not any("columns" in q for q in lower)


def test_narrative_query_camel_variants_only():
    expanded = expand_query("what is the phase 1 of the project")
    assert expanded[0] == "what is the phase 1 of the project"
    assert len(expanded) >= 1
