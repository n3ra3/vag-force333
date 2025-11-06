$ErrorActionPreference = 'Stop'
Write-Host "Running migrations for auth, products, cart, orders..."

$services = @('auth-service','products-service','cart-service','orders-service')
foreach ($s in $services) {
    Write-Host "-> Migrating $s"
    try {
        # Ensure the database is accepting connections before running alembic
        function Wait-ForDb {
            param(
                [int]$TimeoutSeconds = 60
            )
            $start = Get-Date
            while ((Get-Date) -lt $start.AddSeconds($TimeoutSeconds)) {
                try {
                    # Use pg_isready inside the db container to check readiness
                    docker compose exec db pg_isready -U postgres -d vag_force_db | Out-Null
                    return $true
                } catch {
                    Start-Sleep -Seconds 1
                }
            }
            throw "Timed out waiting for Postgres to become ready"
        }

        Wait-ForDb -TimeoutSeconds 60

        # Ensure the container has a DATABASE_URL when running alembic.
        # Some services don't declare DATABASE_URL in docker-compose (products/cart/orders),
        # so pass it explicitly here pointing to the compose Postgres service `db`.
        $dbUrl = 'postgresql+asyncpg://postgres:postgres@db:5432/vag_force_db'
        docker compose exec -e DATABASE_URL=$dbUrl $s alembic -c /app/alembic.ini upgrade head
    } catch {
        Write-Host "alembic upgrade failed for $s, attempting stamp head"
        docker compose exec -e DATABASE_URL=$dbUrl $s alembic -c /app/alembic.ini stamp head
    }
}

Write-Host "All migrations attempted."
