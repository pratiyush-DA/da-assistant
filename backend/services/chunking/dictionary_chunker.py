"""Schema-aware chunking for Excel data dictionaries (table + column + code_set)."""

import json
import re
import uuid

import tiktoken

from django.conf import settings
from services.parsing.dictionary_detect import (
    build_header_map,
    is_code_set_sheet,
)
from services.parsing.types import ParsedElement

from .parent_child import ChildChunk, ParentChunk

TABLE_ROW = "TableRow"


def _camel_variants(phrase: str) -> list[str]:
    words = re.findall(r"[A-Za-z0-9]+", phrase)
    if not words:
        return []
    joined = "".join(w.capitalize() for w in words)
    full = "".join(words)
    return list({joined, full, " ".join(words)})


def _build_keywords(*parts: str) -> str:
    tokens: list[str] = []
    for p in parts:
        if not p:
            continue
        tokens.append(p)
        tokens.extend(_camel_variants(p))
    return " ".join(dict.fromkeys(tokens))


class DictionaryChunker:
    """Deprecated: delegates to WorkbookDictionaryChunker for backward-compatible tests."""

    def __init__(self):
        self.encoding = tiktoken.get_encoding("cl100k_base")

    def _count_tokens(self, text: str) -> int:
        return len(self.encoding.encode(text))

    def chunk(self, elements: list[ParsedElement]) -> tuple[list[ParentChunk], list[ChildChunk]]:
        from .workbook_chunker import WorkbookDictionaryChunker

        return WorkbookDictionaryChunker().chunk(elements)

    def _chunk_legacy(self, elements: list[ParsedElement]) -> tuple[list[ParentChunk], list[ChildChunk]]:
        parents: list[ParentChunk] = []
        children: list[ChildChunk] = []
        parent_index = 0

        sheets: dict[str, list[ParsedElement]] = {}
        for el in elements:
            if el.category != TABLE_ROW:
                continue
            sheet = el.sheet_name or "Sheet1"
            sheets.setdefault(sheet, []).append(el)

        for sheet_name, rows in sheets.items():
            sample_keys: set[str] = set()
            for el in rows[:5]:
                sample_keys.update(json.loads(el.text).keys() if el.text.startswith("{") else [])
            sample_keys -= {"sheet", "row"}
            header_map = build_header_map(sample_keys)
            code_set = is_code_set_sheet(sheet_name, sample_keys)

            if code_set:
                p_idx, sheet_parents, sheet_children = self._chunk_code_set_sheet(
                    sheet_name, rows, header_map, parent_index
                )
                parents.extend(sheet_parents)
                children.extend(sheet_children)
                parent_index = p_idx
                continue

            p_idx, table_parents, table_children = self._chunk_dictionary_sheet(
                sheet_name, rows, header_map, parent_index
            )
            parents.extend(table_parents)
            children.extend(table_children)
            parent_index = p_idx

        return parents, children

    def _field(
        self, payload: dict[str, str], header_map: dict[str, str], role: str, default: str = ""
    ) -> str:
        key = header_map.get(role)
        if key and key in payload:
            return payload[key]
        return default

    def _chunk_dictionary_sheet(
        self,
        sheet_name: str,
        rows: list[ParsedElement],
        header_map: dict[str, str],
        parent_index: int,
    ) -> tuple[int, list[ParentChunk], list[ChildChunk]]:
        parents: list[ParentChunk] = []
        children: list[ChildChunk] = []

        table_key = header_map.get("table")
        col_key = header_map.get("column")
        def_key = header_map.get("definition")

        by_table: dict[str, list[dict[str, str]]] = {}
        for el in rows:
            try:
                payload = json.loads(el.text)
            except json.JSONDecodeError:
                continue
            row_data = {
                k: str(v).strip()
                for k, v in payload.items()
                if k not in ("sheet", "row")
            }
            table_name = self._field(row_data, header_map, "table") or sheet_name
            if not table_name:
                table_name = sheet_name
            by_table.setdefault(table_name, []).append(row_data)

        for table_name, table_rows in by_table.items():
            columns: list[str] = []
            for row_data in table_rows:
                col = self._field(row_data, header_map, "column")
                if col:
                    columns.append(col)

            col_list = ", ".join(columns[:50])
            if len(columns) > 50:
                col_list += f", ... (+{len(columns) - 50} more)"
            table_text = (
                f"Table: {table_name} | Sheet: {sheet_name}\n"
                f"Columns: {col_list}"
            )
            parent_id = str(uuid.uuid4())
            parents.append(
                ParentChunk(
                    id=parent_id,
                    text=table_text,
                    chunk_index=parent_index,
                    page_number=None,
                    section_header=f"{table_name} ({sheet_name})",
                    token_count=self._count_tokens(table_text),
                    chunk_type="table",
                    sheet_name=sheet_name,
                    table_name=table_name,
                    column_name=None,
                    keywords=_build_keywords(table_name, sheet_name, *columns[:20]),
                )
            )
            parent_index += 1

            child_index = 0
            for row_data in table_rows:
                column_name = self._field(row_data, header_map, "column")
                definition = self._field(row_data, header_map, "definition")
                if not column_name:
                    continue
                child_text = (
                    f"Table: {table_name} | Column: {column_name} | "
                    f"Definition: {definition} | Sheet: {sheet_name}"
                )
                children.append(
                    ChildChunk(
                        id=str(uuid.uuid4()),
                        parent_id=parent_id,
                        text=child_text,
                        child_index=child_index,
                        chunk_type="column",
                        sheet_name=sheet_name,
                        table_name=table_name,
                        column_name=column_name,
                        keywords=_build_keywords(
                            table_name, column_name, definition, sheet_name
                        ),
                    )
                )
                child_index += 1

        return parent_index, parents, children

    def _chunk_code_set_sheet(
        self,
        sheet_name: str,
        rows: list[ParsedElement],
        header_map: dict[str, str],
        parent_index: int,
    ) -> tuple[int, list[ParentChunk], list[ChildChunk]]:
        parents: list[ParentChunk] = []
        children: list[ChildChunk] = []

        summary = f"Code Sets sheet: {sheet_name}"
        parent_id = str(uuid.uuid4())
        parents.append(
            ParentChunk(
                id=parent_id,
                text=summary,
                chunk_index=parent_index,
                page_number=None,
                section_header=sheet_name,
                token_count=self._count_tokens(summary),
                chunk_type="table",
                sheet_name=sheet_name,
                table_name=None,
                column_name=None,
                keywords=_build_keywords(sheet_name, "code sets"),
            )
        )
        parent_index += 1

        child_index = 0
        for el in rows:
            try:
                payload = json.loads(el.text)
            except json.JSONDecodeError:
                continue
            row_data = {
                k: str(v).strip()
                for k, v in payload.items()
                if k not in ("sheet", "row")
            }
            code = self._field(row_data, header_map, "code")
            if not code:
                code_key = header_map.get("code")
                if code_key:
                    code = row_data.get(code_key, "")
            value = self._field(row_data, header_map, "value")
            if not value:
                value_key = header_map.get("value")
                if value_key:
                    value = row_data.get(value_key, "")
            definition = self._field(row_data, header_map, "definition")
            if not code and not value:
                continue
            child_text = (
                f"Code: {code} | Value: {value} | Definition: {definition} | "
                f"Sheet: {sheet_name}"
            )
            children.append(
                ChildChunk(
                    id=str(uuid.uuid4()),
                    parent_id=parent_id,
                    text=child_text,
                    child_index=child_index,
                    chunk_type="code_set",
                    sheet_name=sheet_name,
                    table_name=None,
                    column_name=code or None,
                    keywords=_build_keywords(code, value, sheet_name, "code sets"),
                )
            )
            child_index += 1

        return parent_index, parents, children
