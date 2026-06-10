import re
import uuid
from dataclasses import dataclass

import spacy
import spacy.cli
import tiktoken

from django.conf import settings
from services.parsing.types import ParsedElement

TITLE_CATEGORIES = {"Title", "Header", "Heading"}
TABLE_ROW_CATEGORY = "TableRow"
SECTION_HEADER_PATTERN = re.compile(
    r"^(?:Section\s+\d+|\d+(?:\.\d+)+\s+\S)",
    re.I,
)


def _looks_like_section_header(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if SECTION_HEADER_PATTERN.match(stripped):
        return True
    if len(stripped) <= 120 and stripped.isupper() and " " in stripped:
        return True
    return False


@dataclass
class ParentChunk:
    id: str
    text: str
    chunk_index: int
    page_number: int | None
    section_header: str
    token_count: int
    chunk_type: str = "row"
    sheet_name: str | None = None
    table_name: str | None = None
    column_name: str | None = None
    keywords: str = ""


@dataclass
class ChildChunk:
    id: str
    parent_id: str
    text: str
    child_index: int
    chunk_type: str = "row"
    sheet_name: str | None = None
    table_name: str | None = None
    column_name: str | None = None
    keywords: str = ""


class ParentChildChunker:
    def __init__(
        self,
        parent_tokens: int | None = None,
        child_tokens: int | None = None,
        model_name: str = "en_core_web_sm",
    ):
        self.parent_tokens = parent_tokens or settings.PARENT_CHUNK_TOKENS
        self.child_tokens = child_tokens or settings.CHILD_CHUNK_TOKENS
        self.encoding = tiktoken.get_encoding("cl100k_base")
        try:
            self.nlp = spacy.load(model_name)
        except OSError:
            spacy.cli.download(model_name)
            self.nlp = spacy.load(model_name)

    def _count_tokens(self, text: str) -> int:
        return len(self.encoding.encode(text))

    def _split_sentences(self, text: str) -> list[str]:
        doc = self.nlp(text)
        return [sent.text.strip() for sent in doc.sents if sent.text.strip()]

    def _is_table_document(self, elements: list[ParsedElement]) -> bool:
        return any(el.category == TABLE_ROW_CATEGORY for el in elements)

    def chunk_elements(
        self, elements: list[ParsedElement]
    ) -> tuple[list[ParentChunk], list[ChildChunk]]:
        if self._is_table_document(elements):
            return self._chunk_table_elements(elements)
        return self._chunk_narrative_elements(elements)

    def _chunk_table_elements(
        self, elements: list[ParsedElement]
    ) -> tuple[list[ParentChunk], list[ChildChunk]]:
        """Group Excel rows by sheet and token budget; do not sentence-split rows."""
        parents: list[ParentChunk] = []
        children: list[ChildChunk] = []

        current_sheet = ""
        row_buf: list[str] = []
        row_start: int | None = None
        row_end: int | None = None
        buf_tokens = 0
        parent_index = 0

        def section_label() -> str:
            if not current_sheet:
                return "Spreadsheet"
            if row_start is not None and row_end is not None and row_start != row_end:
                return f"{current_sheet} (rows {row_start}-{row_end})"
            if row_start is not None:
                return f"{current_sheet} (row {row_start})"
            return current_sheet

        def flush_parent():
            nonlocal parent_index, row_buf, buf_tokens, row_start, row_end
            if not row_buf:
                return
            text = "\n".join(row_buf)
            parents.append(
                ParentChunk(
                    id=str(uuid.uuid4()),
                    text=text,
                    chunk_index=parent_index,
                    page_number=None,
                    section_header=section_label(),
                    token_count=self._count_tokens(text),
                )
            )
            parent_index += 1
            row_buf = []
            buf_tokens = 0
            row_start = None
            row_end = None

        for el in elements:
            if el.category in ("SheetTitle", "TableHeader"):
                if row_buf:
                    flush_parent()
                if el.sheet_name:
                    current_sheet = el.sheet_name
                continue

            if el.category != TABLE_ROW_CATEGORY:
                continue

            sheet = el.sheet_name or current_sheet
            if sheet and sheet != current_sheet:
                flush_parent()
                current_sheet = sheet

            row_tokens = self._count_tokens(el.text)
            if row_buf and buf_tokens + row_tokens > self.parent_tokens:
                flush_parent()

            if not row_buf:
                row_start = el.row_index
            row_buf.append(el.text)
            row_end = el.row_index
            buf_tokens += row_tokens

        flush_parent()

        for parent in parents:
            row_lines = parent.text.split("\n")
            child_buf: list[str] = []
            child_tokens = 0
            child_index = 0

            def flush_child():
                nonlocal child_index, child_buf, child_tokens
                if not child_buf:
                    return
                children.append(
                    ChildChunk(
                        id=str(uuid.uuid4()),
                        parent_id=parent.id,
                        text="\n".join(child_buf),
                        child_index=child_index,
                    )
                )
                child_index += 1
                child_buf = []
                child_tokens = 0

            for line in row_lines:
                lt = self._count_tokens(line)
                if child_buf and child_tokens + lt > self.child_tokens:
                    flush_child()
                child_buf.append(line)
                child_tokens += lt
            flush_child()

        if not children and parents:
            for parent in parents:
                children.append(
                    ChildChunk(
                        id=str(uuid.uuid4()),
                        parent_id=parent.id,
                        text=parent.text[:4000],
                        child_index=0,
                    )
                )

        return parents, children

    def _chunk_narrative_elements(
        self, elements: list[ParsedElement]
    ) -> tuple[list[ParentChunk], list[ChildChunk]]:
        sentences: list[tuple[str, int | None, str]] = []
        current_header = ""

        for el in elements:
            header_candidate = el.text.strip()
            if el.category in TITLE_CATEGORIES or _looks_like_section_header(
                header_candidate
            ):
                current_header = header_candidate
            for sent in self._split_sentences(el.text):
                sentences.append((sent, el.page_number, current_header))

        if not sentences:
            return [], []

        parents: list[ParentChunk] = []
        children: list[ChildChunk] = []

        buf_sents: list[str] = []
        buf_pages: list[int | None] = []
        buf_headers: list[str] = []
        buf_tokens = 0
        parent_index = 0

        def flush_parent():
            nonlocal parent_index, buf_sents, buf_pages, buf_headers, buf_tokens
            if not buf_sents:
                return None
            text = " ".join(buf_sents)
            page = next((p for p in buf_pages if p is not None), None)
            header = next((h for h in reversed(buf_headers) if h), "")
            parent = ParentChunk(
                id=str(uuid.uuid4()),
                text=text,
                chunk_index=parent_index,
                page_number=page,
                section_header=header,
                token_count=self._count_tokens(text),
            )
            parents.append(parent)
            parent_index += 1
            buf_sents = []
            buf_pages = []
            buf_headers = []
            buf_tokens = 0
            return parent

        for sent, page, header in sentences:
            sent_tokens = self._count_tokens(sent)
            if buf_tokens + sent_tokens > self.parent_tokens and buf_sents:
                flush_parent()
            buf_sents.append(sent)
            buf_pages.append(page)
            buf_headers.append(header)
            buf_tokens += sent_tokens

        flush_parent()

        for parent in parents:
            child_sents = self._split_sentences(parent.text)
            child_buf: list[str] = []
            child_tokens = 0
            child_index = 0

            def flush_child():
                nonlocal child_index, child_buf, child_tokens
                if not child_buf or not child_buf[0].strip():
                    return
                text = " ".join(child_buf)
                children.append(
                    ChildChunk(
                        id=str(uuid.uuid4()),
                        parent_id=parent.id,
                        text=text,
                        child_index=child_index,
                    )
                )
                child_index += 1
                child_buf = []
                child_tokens = 0

            for sent in child_sents:
                st = self._count_tokens(sent)
                if child_tokens + st > self.child_tokens and child_buf:
                    flush_child()
                child_buf.append(sent)
                child_tokens += st
            flush_child()

        if not children and parents:
            for parent in parents:
                children.append(
                    ChildChunk(
                        id=str(uuid.uuid4()),
                        parent_id=parent.id,
                        text=parent.text[:4000],
                        child_index=0,
                    )
                )

        return parents, children
