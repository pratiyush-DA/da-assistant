import pytest
from langchain_core.documents import Document

from services.langchain.retriever import documents_to_retrieved_chunks


def test_documents_to_retrieved_chunks():
    docs = [
        Document(
            page_content="Parent section text",
            metadata={
                "id": "child-1",
                "section_header": "3.2 Payment",
                "page_number": 4,
                "document_id": "doc-1",
                "source": "bcv.pdf",
                "score": 0.91,
            },
        )
    ]
    chunks = documents_to_retrieved_chunks(docs)
    assert len(chunks) == 1
    assert chunks[0].chunk_text == "Parent section text"
    assert chunks[0].section_header == "3.2 Payment"
    assert chunks[0].source == "bcv.pdf"
    assert chunks[0].score == pytest.approx(0.91)
