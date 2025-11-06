#!/usr/bin/env bash
set -euo pipefail

echo "Running migrations for auth, products, cart, orders..."

services=(auth-service products-service cart-service orders-service)

for s in "${services[@]}"; do
  echo "-> Migrating $s"
  docker compose exec $s alembic -c /app/alembic.ini upgrade head || {
    echo "alembic upgrade failed for $s, attempting stamp head"
    docker compose exec $s alembic -c /app/alembic.ini stamp head
  }
done

echo "All migrations attempted."
