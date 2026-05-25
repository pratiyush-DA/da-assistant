from functools import lru_cache

from django.conf import settings
from neo4j import GraphDatabase, Driver


@lru_cache(maxsize=1)
def get_driver() -> Driver:
    return GraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
    )


def verify_connectivity() -> bool:
    driver = get_driver()
    driver.verify_connectivity()
    return True
