from unittest.mock import patch
from uuid import uuid4

from services.graphrag.client_catalog import sheet_hint_from_query
from services.graphrag.query_signals import parse_query_signals


def test_sheet_hint_longest_match():
    index = {
        "Field Sheet": frozenset({"column"}),
        "Fields": frozenset({"column"}),
        "Tables": frozenset({"table_catalog"}),
    }
    assert sheet_hint_from_query("show Fields sheet columns", index) == "Fields"


@patch("services.graphrag.client_catalog.get_sheet_index")
def test_parse_query_signals_sheet_hint(mock_index):
    client_id = uuid4()
    mock_index.return_value = {"Dim": frozenset({"column"})}
    signals = parse_query_signals("columns on Dim sheet", client_id)
    assert signals["sheet_hint"] == "Dim"


def test_sheet_hint_none_when_no_match():
    assert (
        sheet_hint_from_query(
            "random question", {"Tables": frozenset({"table_catalog"})}
        )
        is None
    )
