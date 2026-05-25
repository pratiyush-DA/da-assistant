"""Multi-sheet workbook dictionary chunking (spreadsheet-only ingest path)."""

import json
import re
import uuid

import tiktoken

from services.parsing.sheet_profiles import (
    SheetProfile,
    detect_sheet_profile,
    field_value,
    map_headers,
)
from services.parsing.types import ParsedElement

from .parent_child import ChildChunk, ParentChunk

TABLE_ROW = "TableRow"


def _normalize_column_key(name: str) -> str:
    return re.sub(r"[\s_]+", "", name).lower()


def _field_row_quality(chunk: ChildChunk) -> int:
    text = chunk.text or ""
    text_l = text.lower()
    score = len(text)
    if "datatype:" in text_l:
        dt = text_l.split("datatype:", 1)[-1].split("|")[0].strip()
        if dt and dt not in ("", "n/a", "none"):
            score += 200
    if "definition:" in text_l:
        def_part = text_l.split("definition:", 1)[-1].split("|")[0].strip()
        if def_part and def_part not in ("", "n/a", "none"):
            score += min(len(def_part), 150)
    return score


def _dedupe_column_children(children: list[ChildChunk]) -> list[ChildChunk]:
    """Keep the best column chunk per normalized column name for RAG."""
    non_column = [c for c in children if c.chunk_type != "column" or not c.column_name]
    best_by_key: dict[str, ChildChunk] = {}
    for c in children:
        if c.chunk_type != "column" or not c.column_name:
            continue
        key = _normalize_column_key(c.column_name)
        if key not in best_by_key or _field_row_quality(c) > _field_row_quality(
            best_by_key[key]
        ):
            best_by_key[key] = c
    return non_column + list(best_by_key.values())


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


class WorkbookDictionaryChunker:
    def __init__(self):
        self.encoding = tiktoken.get_encoding("cl100k_base")

    def _count_tokens(self, text: str) -> int:
        return len(self.encoding.encode(text))

    def _row_payload(self, el: ParsedElement) -> dict[str, str]:
        try:
            data = json.loads(el.text)
        except json.JSONDecodeError:
            return {}
        return {k: str(v).strip() for k, v in data.items() if k not in ("sheet", "row")}

    def chunk(self, elements: list[ParsedElement]) -> tuple[list[ParentChunk], list[ChildChunk]]:
        parents: list[ParentChunk] = []
        children: list[ChildChunk] = []
        parent_index = 0
        catalog_table_names: list[str] = []
        catalog_sheet = ""

        sheets: dict[str, list[ParsedElement]] = {}
        for el in elements:
            if el.category != TABLE_ROW:
                continue
            sheets.setdefault(el.sheet_name or "Sheet1", []).append(el)

        for sheet_name, rows in sheets.items():
            headers = set()
            for el in rows[:8]:
                headers.update(self._row_payload(el).keys())
            profile = detect_sheet_profile(sheet_name, headers)
            header_map = map_headers(headers, profile)

            if profile == SheetProfile.SKIP:
                continue
            if profile == SheetProfile.DATABASE:
                parent_index = self._chunk_database(
                    sheet_name, rows, header_map, parents, children, parent_index
                )
            elif profile == SheetProfile.TABLE_CATALOG:
                parent_index, names = self._chunk_table_catalog(
                    sheet_name, rows, header_map, parents, children, parent_index
                )
                catalog_table_names.extend(names)
                catalog_sheet = sheet_name
            elif profile == SheetProfile.FIELD:
                parent_index = self._chunk_fields(
                    sheet_name, rows, header_map, parents, children, parent_index
                )
            elif profile == SheetProfile.CODE_SET:
                parent_index = self._chunk_code_set(
                    sheet_name, rows, header_map, parents, children, parent_index
                )
            elif profile == SheetProfile.OVERVIEW:
                parent_index = self._chunk_overview(
                    sheet_name, rows, parents, children, parent_index
                )

        if catalog_table_names:
            parent_index = self._emit_table_catalog(
                catalog_sheet,
                catalog_table_names,
                parents,
                children,
                parent_index,
            )

        children = _dedupe_column_children(children)
        return parents, children

    def _chunk_database(
        self,
        sheet_name: str,
        rows: list[ParsedElement],
        header_map: dict[str, str],
        parents: list[ParentChunk],
        children: list[ChildChunk],
        parent_index: int,
    ) -> int:
        parent_id = str(uuid.uuid4())
        parent_text = f"Database metadata sheet: {sheet_name}"
        parents.append(
            ParentChunk(
                id=parent_id,
                text=parent_text,
                chunk_index=parent_index,
                page_number=None,
                section_header=sheet_name,
                token_count=self._count_tokens(parent_text),
                chunk_type="database",
                sheet_name=sheet_name,
                table_name=None,
                column_name=None,
                keywords=_build_keywords(sheet_name, "database"),
            )
        )
        parent_index += 1

        for i, el in enumerate(rows):
            row_data = self._row_payload(el)
            if not any(row_data.values()):
                continue
            name = field_value(row_data, "name", header_map) or field_value(
                row_data, "formal_name", header_map
            )
            desc = field_value(row_data, "description", header_map)
            notes = field_value(row_data, "notes", header_map)
            steward = field_value(row_data, "steward_org", header_map)
            contact = field_value(row_data, "steward_contact", header_map)
            child_text = (
                f"Database: {name} | Description: {desc} | Notes: {notes} | "
                f"Steward: {steward} | Contact: {contact} | Sheet: {sheet_name}"
            )
            children.append(
                ChildChunk(
                    id=str(uuid.uuid4()),
                    parent_id=parent_id,
                    text=child_text,
                    child_index=i,
                    chunk_type="database",
                    sheet_name=sheet_name,
                    table_name=None,
                    column_name=name or None,
                    keywords=_build_keywords(name, desc, sheet_name, "database"),
                )
            )
        return parent_index

    def _chunk_table_catalog(
        self,
        sheet_name: str,
        rows: list[ParsedElement],
        header_map: dict[str, str],
        parents: list[ParentChunk],
        children: list[ChildChunk],
        parent_index: int,
    ) -> tuple[int, list[str]]:
        table_names: list[str] = []
        parent_id = str(uuid.uuid4())
        parent_text = f"Table catalog sheet: {sheet_name}"
        parents.append(
            ParentChunk(
                id=parent_id,
                text=parent_text,
                chunk_index=parent_index,
                page_number=None,
                section_header=sheet_name,
                token_count=self._count_tokens(parent_text),
                chunk_type="table",
                sheet_name=sheet_name,
                table_name=None,
                column_name=None,
                keywords=_build_keywords(sheet_name, "table catalog"),
            )
        )
        parent_index += 1
        child_index = 0

        for el in rows:
            row_data = self._row_payload(el)
            table_name = field_value(row_data, "table", header_map)
            if not table_name:
                continue
            definition = field_value(row_data, "definition", header_map)
            english = field_value(row_data, "english_name", header_map)
            table_names.append(table_name)
            child_text = (
                f"Table: {table_name} | Definition: {definition} | "
                f"EnglishName: {english} | Sheet: {sheet_name}"
            )
            children.append(
                ChildChunk(
                    id=str(uuid.uuid4()),
                    parent_id=parent_id,
                    text=child_text,
                    child_index=child_index,
                    chunk_type="table_definition",
                    sheet_name=sheet_name,
                    table_name=table_name,
                    column_name=None,
                    keywords=_build_keywords(table_name, definition, english, sheet_name),
                )
            )
            child_index += 1

        return parent_index, table_names

    def _chunk_fields(
        self,
        sheet_name: str,
        rows: list[ParsedElement],
        header_map: dict[str, str],
        parents: list[ParentChunk],
        children: list[ChildChunk],
        parent_index: int,
    ) -> int:
        by_table: dict[str, list[dict[str, str]]] = {}
        for el in rows:
            row_data = self._row_payload(el)
            table_name = field_value(row_data, "table", header_map) or sheet_name
            by_table.setdefault(table_name, []).append(row_data)

        for table_name, table_rows in by_table.items():
            columns = [
                field_value(r, "column", header_map)
                for r in table_rows
                if field_value(r, "column", header_map)
            ]
            col_preview = ", ".join(columns[:40])
            if len(columns) > 40:
                col_preview += f", ... (+{len(columns) - 40} more)"
            parent_id = str(uuid.uuid4())
            parent_text = f"Table: {table_name} | Sheet: {sheet_name}\nColumns: {col_preview}"
            parents.append(
                ParentChunk(
                    id=parent_id,
                    text=parent_text,
                    chunk_index=parent_index,
                    page_number=None,
                    section_header=f"{table_name} ({sheet_name})",
                    token_count=self._count_tokens(parent_text),
                    chunk_type="table",
                    sheet_name=sheet_name,
                    table_name=table_name,
                    column_name=None,
                    keywords=_build_keywords(table_name, sheet_name, *columns[:15]),
                )
            )
            parent_index += 1

            for i, row_data in enumerate(table_rows):
                column_name = field_value(row_data, "column", header_map)
                if not column_name:
                    continue
                english = field_value(row_data, "english_name", header_map)
                datatype = field_value(row_data, "datatype", header_map)
                definition = field_value(row_data, "definition", header_map)
                child_text = (
                    f"Table: {table_name} | Column: {column_name} | "
                    f"EnglishName: {english} | Datatype: {datatype} | "
                    f"Definition: {definition} | Sheet: {sheet_name}"
                )
                children.append(
                    ChildChunk(
                        id=str(uuid.uuid4()),
                        parent_id=parent_id,
                        text=child_text,
                        child_index=i,
                        chunk_type="column",
                        sheet_name=sheet_name,
                        table_name=table_name,
                        column_name=column_name,
                        keywords=_build_keywords(
                            table_name, column_name, english, definition, datatype, sheet_name
                        ),
                    )
                )
        return parent_index

    def _chunk_code_set(
        self,
        sheet_name: str,
        rows: list[ParsedElement],
        header_map: dict[str, str],
        parents: list[ParentChunk],
        children: list[ChildChunk],
        parent_index: int,
    ) -> int:
        parent_id = str(uuid.uuid4())
        parent_text = f"Code set sheet: {sheet_name}"
        parents.append(
            ParentChunk(
                id=parent_id,
                text=parent_text,
                chunk_index=parent_index,
                page_number=None,
                section_header=sheet_name,
                token_count=self._count_tokens(parent_text),
                chunk_type="table",
                sheet_name=sheet_name,
                table_name=None,
                column_name=None,
                keywords=_build_keywords(sheet_name, "code set", "code sets"),
            )
        )
        parent_index += 1
        child_index = 0

        for el in rows:
            row_data = self._row_payload(el)
            set_name = field_value(row_data, "set_name", header_map)
            code = field_value(row_data, "code", header_map)
            meaning = field_value(row_data, "meaning", header_map)
            if not code and not meaning:
                continue
            child_text = (
                f"CodeSet: {set_name} | Code: {code} | Meaning: {meaning} | Sheet: {sheet_name}"
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
                    keywords=_build_keywords(set_name, code, meaning, sheet_name, "Region"),
                )
            )
            child_index += 1
        return parent_index

    def _chunk_overview(
        self,
        sheet_name: str,
        rows: list[ParsedElement],
        parents: list[ParentChunk],
        children: list[ChildChunk],
        parent_index: int,
    ) -> int:
        lines: list[str] = []
        for el in rows:
            row_data = self._row_payload(el)
            line = " ".join(v for v in row_data.values() if v)
            if line:
                lines.append(line)
        if not lines:
            return parent_index

        parent_id = str(uuid.uuid4())
        body = "\n".join(lines)
        parent_text = f"Workbook overview: {sheet_name}\n{body[:2000]}"
        parents.append(
            ParentChunk(
                id=parent_id,
                text=parent_text,
                chunk_index=parent_index,
                page_number=None,
                section_header=sheet_name,
                token_count=self._count_tokens(parent_text),
                chunk_type="overview",
                sheet_name=sheet_name,
                table_name=None,
                column_name=None,
                keywords=_build_keywords(
                    sheet_name, "overview", "database", "tables", "fields", "relationship"
                ),
            )
        )
        parent_index += 1

        child_text = (
            f"Overview: {body[:4000]} | Sheet: {sheet_name} | "
            "Relationships: database contains tables; tables contain fields/columns."
        )
        children.append(
            ChildChunk(
                id=str(uuid.uuid4()),
                parent_id=parent_id,
                text=child_text,
                child_index=0,
                chunk_type="overview",
                sheet_name=sheet_name,
                table_name=None,
                column_name=None,
                keywords=_build_keywords(
                    "database", "table", "field", "column", "relationship", sheet_name
                ),
            )
        )
        return parent_index

    def _emit_table_catalog(
        self,
        sheet_name: str,
        table_names: list[str],
        parents: list[ParentChunk],
        children: list[ChildChunk],
        parent_index: int,
    ) -> int:
        unique = sorted(set(table_names))
        parent_id = str(uuid.uuid4())
        listing = ", ".join(unique)
        parent_text = f"Table catalog ({len(unique)} tables) | Sheet: {sheet_name}"
        parents.append(
            ParentChunk(
                id=parent_id,
                text=parent_text,
                chunk_index=parent_index,
                page_number=None,
                section_header=f"Catalog ({sheet_name})",
                token_count=self._count_tokens(parent_text),
                chunk_type="table_catalog",
                sheet_name=sheet_name,
                table_name=None,
                column_name=None,
                keywords=_build_keywords("table catalog", "list tables", *unique[:30]),
            )
        )
        parent_index += 1

        child_text = (
            f"Table catalog | Sheet: {sheet_name} | Tables ({len(unique)}): {listing}"
        )
        children.append(
            ChildChunk(
                id=str(uuid.uuid4()),
                parent_id=parent_id,
                text=child_text,
                child_index=0,
                chunk_type="table_catalog",
                sheet_name=sheet_name,
                table_name=None,
                column_name=None,
                keywords=_build_keywords("table catalog", *unique),
            )
        )
        return parent_index
