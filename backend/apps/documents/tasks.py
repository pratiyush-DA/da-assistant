import logging
import tempfile
from pathlib import Path

from celery import shared_task

from apps.documents.spreadsheet import is_spreadsheet_type
from services.chunking import ParentChildChunker
from services.chunking.workbook_chunker import WorkbookDictionaryChunker
from services.embedding import embed_texts
from services.neo4j.repositories import DocumentRepository, IngestionRepository
from services.parsing import parse_document
from services.parsing.ocr_enrichment import cleanup_figure_artifacts
from services.parsing.sheet_profiles import is_workbook_dictionary
from services.storage import get_storage_backend

logger = logging.getLogger(__name__)


def _chunk_to_parent_payload(p) -> dict:
    return {
        "id": p.id,
        "text": p.text,
        "chunk_index": p.chunk_index,
        "page_number": p.page_number,
        "section_header": p.section_header,
        "token_count": p.token_count,
        "chunk_type": getattr(p, "chunk_type", "row"),
        "sheet_name": getattr(p, "sheet_name", None),
        "table_name": getattr(p, "table_name", None),
        "column_name": getattr(p, "column_name", None),
        "keywords": getattr(p, "keywords", "") or "",
    }


def _chunk_to_child_payload(c, vector) -> dict:
    return {
        "id": c.id,
        "parent_id": c.parent_id,
        "text": c.text,
        "child_index": c.child_index,
        "embedding": vector,
        "chunk_type": getattr(c, "chunk_type", "row"),
        "sheet_name": getattr(c, "sheet_name", None),
        "table_name": getattr(c, "table_name", None),
        "column_name": getattr(c, "column_name", None),
        "keywords": getattr(c, "keywords", "") or "",
    }


@shared_task(bind=True, max_retries=0)
def ingest_document(self, document_id: str):
    logger.info("Ingestion started for document %s", document_id)
    doc_repo = DocumentRepository()
    document = doc_repo.get(document_id)
    if not document:
        logger.error("Document %s not found", document_id)
        return

    client_id = document["client_id"]
    storage = get_storage_backend()
    tmp_path = None
    try:
        with storage.open(document["file_path"]) as f:
            suffix = Path(document["filename"]).suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(f.read())
                tmp_path = tmp.name

        elements = parse_document(tmp_path, document["file_type"])
        if is_spreadsheet_type(document["file_type"]):
            if is_workbook_dictionary(elements):
                parents, children = WorkbookDictionaryChunker().chunk(elements)
                logger.info("Using workbook dictionary chunker for document %s", document_id)
            else:
                parents, children = ParentChildChunker().chunk_elements(elements)
        else:
            parents, children = ParentChildChunker().chunk_elements(elements)

        if not parents or not children:
            raise ValueError("No text content could be extracted from the document.")

        ingestion_repo = IngestionRepository()
        ingestion_repo.clear_document_chunks(document_id)

        child_texts = [c.text for c in children]
        vectors = embed_texts(child_texts)

        parent_payloads = [_chunk_to_parent_payload(p) for p in parents]
        child_payloads = [
            _chunk_to_child_payload(c, vector) for c, vector in zip(children, vectors)
        ]

        ingestion_repo.write_chunks(
            document_id=document_id,
            client_id=client_id,
            parents=parent_payloads,
            children=child_payloads,
        )

        from services.graphrag.client_corpus import clear_corpus_cache

        clear_corpus_cache(client_id)
        if is_spreadsheet_type(document["file_type"]) and is_workbook_dictionary(
            elements
        ):
            from services.graphrag.client_catalog import clear_sheet_index_cache

            clear_sheet_index_cache(client_id)

        doc_repo.set_status(document_id, "ready", error_message="")
        logger.info(
            "Ingested document %s with %s parents and %s children",
            document_id,
            len(parents),
            len(children),
        )

    except Exception as exc:
        logger.exception("Ingestion failed for %s", document_id)
        doc_repo.set_status(document_id, "error", error_message=str(exc)[:2000])
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)
        cleanup_figure_artifacts()
