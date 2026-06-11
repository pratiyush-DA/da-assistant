from dataclasses import dataclass, field


@dataclass
class ParsedElement:
    text: str
    category: str
    page_number: int | None = None
    sheet_name: str | None = None
    row_index: int | None = None
    source_kind: str = "text"
    element_index: int | None = None


@dataclass
class RawElementMarker:
    """Empty-text visual element from fast unstructured pass."""

    category: str
    page_number: int | None = None
    element_index: int = 0


@dataclass
class FastParseResult:
    elements: list[ParsedElement]
    raw_markers: list[RawElementMarker] = field(default_factory=list)
    page_count: int = 0
