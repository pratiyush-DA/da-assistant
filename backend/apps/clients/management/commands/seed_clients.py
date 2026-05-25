from django.core.management.base import BaseCommand

from services.neo4j.repositories import ClientRepository


class Command(BaseCommand):
    help = "Seed demo Client nodes in Neo4j"

    def handle(self, *args, **options):
        repo = ClientRepository()
        existing = {c["name"] for c in repo.list_all()}
        demos = ["Acme Corp", "Globex Industries", "Initech"]
        created = 0
        for name in demos:
            if name not in existing:
                repo.create(name=name)
                created += 1
                self.stdout.write(self.style.SUCCESS(f"Created client: {name}"))
        self.stdout.write(self.style.SUCCESS(f"Done. Created {created} client(s)."))
