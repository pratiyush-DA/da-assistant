from unittest.mock import patch

import pytest
from rest_framework.test import APIRequestFactory

from apps.clients.views import ClientDetailView
from services.neo4j.repositories.client import ClientRepository


@pytest.mark.django_db
@patch.object(ClientRepository, "delete_cascade")
def test_client_detail_delete_returns_204(mock_delete):
    mock_delete.return_value = True
    factory = APIRequestFactory()
    request = factory.delete("/api/clients/00000000-0000-0000-0000-000000000001/")
    response = ClientDetailView.as_view()(
        request, pk="00000000-0000-0000-0000-000000000001"
    )

    assert response.status_code == 204
    mock_delete.assert_called_once_with("00000000-0000-0000-0000-000000000001")


@pytest.mark.django_db
@patch.object(ClientRepository, "delete_cascade")
def test_client_detail_delete_returns_404(mock_delete):
    mock_delete.return_value = False
    factory = APIRequestFactory()
    request = factory.delete("/api/clients/00000000-0000-0000-0000-000000000002/")
    response = ClientDetailView.as_view()(
        request, pk="00000000-0000-0000-0000-000000000002"
    )

    assert response.status_code == 404
