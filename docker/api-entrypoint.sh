#!/bin/sh
set -e

run_manage() {
  max_attempts="${DOCKER_STARTUP_RETRIES:-10}"
  attempt=1
  while [ "$attempt" -le "$max_attempts" ]; do
    if "$@"; then
      return 0
    fi
    echo "Command failed (attempt ${attempt}/${max_attempts}): $*"
    attempt=$((attempt + 1))
    sleep 3
  done
  return 1
}

if [ "${DOCKER_RUN_MIGRATE:-1}" = "1" ]; then
  run_manage python manage.py migrate --noinput
fi

if [ "${DOCKER_INIT_NEO4J_SCHEMA:-0}" = "1" ]; then
  run_manage python manage.py init_neo4j_schema
fi

if [ "${DOCKER_SEED_CLIENTS:-0}" = "1" ]; then
  run_manage python manage.py seed_clients
fi

exec "$@"
