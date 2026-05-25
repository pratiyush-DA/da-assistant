import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.exceptions import ValidationError

from apps.documents.serializers import DocumentUploadSerializer


@pytest.mark.django_db
def test_upload_serializer_rejects_zip():
    data = {
        "client_id": "00000000-0000-0000-0000-000000000001",
        "file": SimpleUploadedFile("bad.zip", b"data"),
    }
    ser = DocumentUploadSerializer(data=data)
    with pytest.raises(ValidationError):
        ser.is_valid(raise_exception=True)


@pytest.mark.django_db
def test_upload_serializer_accepts_xlsx():
    data = {
        "client_id": "00000000-0000-0000-0000-000000000001",
        "file": SimpleUploadedFile(
            "data.xlsx",
            b"placeholder",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
    }
    ser = DocumentUploadSerializer(data=data)
    assert ser.is_valid(), ser.errors
