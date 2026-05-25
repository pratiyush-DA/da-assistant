import pytest

from apps.documents.file_types import validate_upload_filename


def test_validate_allowed_extensions():
    assert validate_upload_filename("report.xlsx") == "xlsx"
    assert validate_upload_filename("doc.PDF") == "pdf"
    assert validate_upload_filename("data.csv") == "csv"
    assert validate_upload_filename("legacy.xls") == "xls"


def test_validate_rejects_unknown():
    with pytest.raises(ValueError, match="Unsupported"):
        validate_upload_filename("archive.zip")
