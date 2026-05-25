import pytest

from apps.users.validators import validate_data_axle_email


def test_valid_email():
    assert validate_data_axle_email("jane.smith@data-axle.com") == "jane.smith@data-axle.com"


def test_normalizes_case():
    assert validate_data_axle_email("Jane@DATA-AXLE.COM") == "jane@data-axle.com"


def test_rejects_wrong_domain():
    with pytest.raises(ValueError, match="data-axle.com"):
        validate_data_axle_email("user@gmail.com")
