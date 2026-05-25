from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from services.neo4j.repositories import ClientRepository, DocumentRepository
from services.storage import get_storage_backend

from .file_types import extension_from_filename

from .serializers import (
    DocumentSerializer,
    DocumentStatusSerializer,
    DocumentUploadSerializer,
)
from .tasks import ingest_document


class DocumentListCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        client_id = request.query_params.get("client_id")
        if not client_id:
            return Response(
                {"detail": "client_id query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        repo = DocumentRepository()
        docs = repo.list_by_client(client_id)
        return Response(DocumentSerializer(docs, many=True).data)

    def post(self, request):
        upload_serializer = DocumentUploadSerializer(data=request.data)
        upload_serializer.is_valid(raise_exception=True)
        client_id = str(upload_serializer.validated_data["client_id"])
        if not ClientRepository().exists(client_id):
            return Response({"detail": "Client not found."}, status=status.HTTP_404_NOT_FOUND)

        uploaded = upload_serializer.validated_data["file"]
        ext = extension_from_filename(uploaded.name)

        doc_repo = DocumentRepository()
        file_size = getattr(uploaded, "size", None) or 0
        document = doc_repo.create(
            client_id=client_id,
            filename=uploaded.name,
            file_type=ext,
            file_path="",
            file_size_bytes=file_size,
        )
        storage_key = f"{client_id}/{document['id']}/{uploaded.name}"
        storage = get_storage_backend()
        storage.save(storage_key, uploaded)
        doc_repo.update_file(
            document_id=document["id"],
            filename=uploaded.name,
            file_type=ext,
            file_path=storage_key,
        )

        ingest_document.delay(document["id"])
        final = doc_repo.get(document["id"]) or document
        return Response(DocumentSerializer(final).data, status=status.HTTP_201_CREATED)


class DocumentDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def delete(self, request, pk):
        doc_repo = DocumentRepository()
        document = doc_repo.get(str(pk))
        if not document:
            return Response(status=status.HTTP_404_NOT_FOUND)
        storage = get_storage_backend()
        if document.get("file_path"):
            storage.delete(document["file_path"])
        doc_repo.delete_cascade(str(pk))
        return Response(status=status.HTTP_204_NO_CONTENT)

    def put(self, request, pk):
        doc_repo = DocumentRepository()
        document = doc_repo.get(str(pk))
        if not document:
            return Response(status=status.HTTP_404_NOT_FOUND)

        upload_serializer = DocumentUploadSerializer(data=request.data)
        upload_serializer.is_valid(raise_exception=True)
        if str(upload_serializer.validated_data["client_id"]) != document["client_id"]:
            return Response(
                {"detail": "client_id must match the existing document client."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        uploaded = upload_serializer.validated_data["file"]
        storage = get_storage_backend()
        if document.get("file_path"):
            storage.delete(document["file_path"])

        ext = extension_from_filename(uploaded.name)
        storage_key = f"{document['client_id']}/{pk}/{uploaded.name}"
        storage.save(storage_key, uploaded)

        from services.neo4j.repositories import IngestionRepository

        IngestionRepository().clear_document_chunks(str(pk))

        file_size = getattr(uploaded, "size", None) or 0
        updated = doc_repo.update_file(
            document_id=str(pk),
            filename=uploaded.name,
            file_type=ext,
            file_path=storage_key,
            file_size_bytes=file_size,
        )
        ingest_document.delay(str(pk))
        updated["chunk_count"] = 0
        return Response(DocumentSerializer(updated).data)


class DocumentStatusView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, pk):
        doc_repo = DocumentRepository()
        document = doc_repo.get(str(pk))
        if not document:
            return Response(status=status.HTTP_404_NOT_FOUND)
        data = {
            "status": document["status"],
            "error_message": document.get("error_message"),
            "chunk_count": doc_repo.chunk_count(str(pk)),
        }
        return Response(DocumentStatusSerializer(data).data)
