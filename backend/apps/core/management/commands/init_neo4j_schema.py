from django.core.management.base import BaseCommand

from services.neo4j import init_schema, verify_connectivity


class Command(BaseCommand):
    help = "Initialize Neo4j constraints and vector index"

    def handle(self, *args, **options):
        verify_connectivity()
        init_schema()
        self.stdout.write(self.style.SUCCESS("Neo4j schema initialized."))
