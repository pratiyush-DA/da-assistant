from langchain_core.output_parsers import StrOutputParser

from services.graphrag.retriever import RetrievedChunk
from services.langchain.factory import get_chat_model
from services.langchain.prompts import DATA_DICTIONARY_RAG_PROMPT, MIXED_RAG_PROMPT, RAG_PROMPT


_CHUNK_LABELS = {
    "database": "DATABASE",
    "table_definition": "TABLE_DEF",
    "table_catalog": "CATALOG",
    "code_set": "CODE_SET",
    "column": "COLUMN",
    "overview": "OVERVIEW",
    "table": "TABLE",
    "row": "ROW",
}


def _chunk_label(chunk: RetrievedChunk) -> str:
    ctype = _CHUNK_LABELS.get(chunk.chunk_type or "", (chunk.chunk_type or "chunk").upper())
    parts = [ctype]
    if (chunk.chunk_type or "") == "row" and chunk.source:
        parts.append(chunk.source)
    if chunk.section_header:
        parts.append(chunk.section_header)
    if chunk.table_name:
        parts.append(f"Table {chunk.table_name}")
    if chunk.column_name:
        parts.append(f"Column {chunk.column_name}")
    if chunk.sheet_name:
        parts.append(f"Sheet {chunk.sheet_name}")
    return " | ".join(parts)


def format_context_from_chunks(chunks: list[RetrievedChunk]) -> str:
    parts = []
    for i, chunk in enumerate(chunks, start=1):
        label = _chunk_label(chunk)
        source = f" ({chunk.source})" if chunk.source else ""
        page = f", page {chunk.page_number}" if chunk.page_number else ""
        ctype = chunk.chunk_type or ""
        if ctype in _CHUNK_LABELS and chunk.child_text:
            body = chunk.child_text
        else:
            body = chunk.child_text or chunk.chunk_text
        parts.append(f"[{i}] {label}{source}{page}\n{body}")
    return "\n\n---\n\n".join(parts)


def build_rag_chain(use_dictionary_prompt: bool = False, use_mixed_prompt: bool = False):
    """LCEL chain: context + question -> prompt -> ChatGroq -> text."""
    if use_dictionary_prompt:
        prompt = DATA_DICTIONARY_RAG_PROMPT
    elif use_mixed_prompt:
        prompt = MIXED_RAG_PROMPT
    else:
        prompt = RAG_PROMPT
    return prompt | get_chat_model() | StrOutputParser()


def stream_rag_tokens(
    question: str,
    context: str,
    use_dictionary_prompt: bool = False,
    use_mixed_prompt: bool = False,
):
    """Stream text tokens from the RAG chain."""
    chain = build_rag_chain(
        use_dictionary_prompt=use_dictionary_prompt,
        use_mixed_prompt=use_mixed_prompt,
    )
    for chunk in chain.stream({"question": question, "context": context}):
        if chunk:
            yield chunk
