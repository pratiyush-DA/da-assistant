import logging
from pathlib import Path

from django.conf import settings

from .driver import get_driver

logger = logging.getLogger(__name__)


def _cypher_dir() -> Path:
    """Resolve Cypher scripts: backend/infrastructure/neo4j in Docker; repo root when running locally."""
    candidates = [
        Path(settings.BASE_DIR) / "infrastructure" / "neo4j",
        Path(settings.BASE_DIR).parent / "infrastructure" / "neo4j",
    ]
    for path in candidates:
        if (path / "01_constraints.cypher").exists():
            return path
    return candidates[0]


def _run_cypher_file(session, filename: str, cypher_dir: Path) -> bool:
    path = cypher_dir / filename
    if not path.exists():
        logger.warning("Cypher file not found: %s", path)
        return False
    statements = [
        s.strip()
        for s in path.read_text(encoding="utf-8").split(";")
        if s.strip() and not s.strip().startswith("//")
    ]
    for statement in statements:
        session.run(statement)
    return True


def init_schema() -> None:
    cypher_dir = _cypher_dir()
    driver = get_driver()
    with driver.session(database=settings.NEO4J_DATABASE) as session:
        ok_constraints = _run_cypher_file(session, "01_constraints.cypher", cypher_dir)
        ok_index = _run_cypher_file(session, "02_vector_index.cypher", cypher_dir)
        ok_fulltext = _run_cypher_file(session, "03_fulltext_index.cypher", cypher_dir)
        ok_migration = _run_cypher_file(session, "04_migration_conversations.cypher", cypher_dir)
    logger.info(
        "Neo4j schema initialized (cypher_dir=%s, constraints=%s, vector_index=%s, fulltext=%s, migration=%s)",
        cypher_dir,
        ok_constraints,
        ok_index,
        ok_fulltext,
        ok_migration,
    )
