import os

import pytest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")


@pytest.fixture(scope="session")
def django_db_setup():
    """Use SQLite for Django framework only; domain data lives in Neo4j."""
    pass


def neo4j_available() -> bool:
    try:
        from services.neo4j import verify_connectivity

        verify_connectivity()
        return True
    except Exception:
        return False


requires_neo4j = pytest.mark.skipif(
    not neo4j_available(),
    reason="Neo4j is not reachable; start docker compose neo4j service.",
)
