# Docker workflow (fast day-to-day):
#   make build      — after requirements.txt or Dockerfile changes
#   make up         — start stack (no image rebuild)
#   make logs       — follow api/worker logs
#
# First clone / fresh Neo4j volume:
#   make bootstrap  — build images, start stack, init schema + seed clients

.PHONY: bootstrap up up-ui down build build-ui schema seed test lint logs

bootstrap: build
	docker compose up -d
	docker compose exec api python manage.py init_neo4j_schema
	docker compose exec api python manage.py seed_clients

up:
	docker compose up -d

up-ui:
	docker compose --profile ui up -d

down:
	docker compose down

build:
	docker compose build api worker

build-ui:
	docker compose --profile ui build frontend

schema:
	docker compose exec api python manage.py init_neo4j_schema

seed:
	docker compose exec api python manage.py seed_clients

test:
	docker compose exec api pytest -q

lint:
	docker compose exec api ruff check .

logs:
	docker compose logs -f api worker
