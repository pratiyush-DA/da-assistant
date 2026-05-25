import pytest
from django.test import Client


@pytest.mark.django_db
def test_lineage_endpoints_return_501():
    api = Client()
    for path in ["/api/lineage/ingest/", "/api/lineage/ORDERS/", "/api/lineage/chat/"]:
        method = "post" if "chat" in path or "ingest" in path else "get"
        response = getattr(api, method)(path)
        assert response.status_code == 501
