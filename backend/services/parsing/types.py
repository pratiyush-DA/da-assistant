from dataclasses import dataclass


@dataclass
class ParsedElement:
    text: str
    category: str
    page_number: int | None = None
    sheet_name: str | None = None
    row_index: int | None = None
