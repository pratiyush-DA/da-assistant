from unittest.mock import MagicMock, patch

import pytest
from rest_framework.test import APIRequestFactory

from apps.core.views import PlatformStatsView
from services.neo4j.repositories.platform_stats import PlatformStatsRepository


@patch("services.neo4j.repositories.platform_stats.get_driver")
def test_get_platform_stats_returns_counts(mock_driver):
    mock_session = MagicMock()
    mock_driver.return_value.session.return_value.__enter__.return_value = mock_session
    mock_session.run.return_value.single.return_value = {
        "client_count": 3,
        "documents_ready": 12,
        "user_count": 5,
        "documents_total": 15,
        "documents_processing": 2,
        "conversation_count": 8,
    }

    stats = PlatformStatsRepository().get_platform_stats()

    assert stats == {
        "client_count": 3,
        "documents_ready": 12,
        "user_count": 5,
        "documents_total": 15,
        "documents_processing": 2,
        "conversation_count": 8,
    }


@patch("services.neo4j.repositories.platform_stats.get_driver")
def test_get_platform_stats_empty_graph(mock_driver):
    mock_session = MagicMock()
    mock_driver.return_value.session.return_value.__enter__.return_value = mock_session
    mock_session.run.return_value.single.return_value = None

    stats = PlatformStatsRepository().get_platform_stats()

    assert stats["client_count"] == 0
    assert stats["documents_ready"] == 0
    assert stats["user_count"] == 0


@pytest.mark.django_db
@patch.object(PlatformStatsRepository, "get_platform_stats")
def test_platform_stats_view_returns_200(mock_get_stats):
    mock_get_stats.return_value = {
        "client_count": 2,
        "documents_ready": 7,
        "user_count": 4,
        "documents_total": 9,
        "documents_processing": 1,
        "conversation_count": 3,
    }
    factory = APIRequestFactory()
    request = factory.get("/api/stats/")
    response = PlatformStatsView.as_view()(request)

    assert response.status_code == 200
    assert response.data == {
        "client_count": 2,
        "documents_ready": 7,
        "user_count": 4,
        "documents_total": 9,
        "documents_processing": 1,
        "conversation_count": 3,
    }
