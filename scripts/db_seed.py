"""Seed the Postgres database with demo users and products.

This script is idempotent and will create the `users` and `products` tables
if they do not exist, then insert demo rows using ON CONFLICT DO NOTHING.

It also attempts to call the inventory-service `/api/inventory/reset` endpoint
to set the in-memory inventory for deterministic tests (best-effort).

Usage:
    python scripts/db_seed.py

The script reads DATABASE_URL from the environment; default matches docker-compose.
"""
import os
import sys
import psycopg2
from psycopg2.extras import execute_values
from urllib.parse import urlparse
from pathlib import Path

# Ensure project root is on sys.path so we can import shared helpers
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.auth_utils import get_password_hash
import httpx


DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@db:5432/vag_force_db",
)


def connect_db(dsn: str):
    try:
        conn = psycopg2.connect(dsn)
        conn.autocommit = True
        return conn
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        raise


def ensure_tables(conn):
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            full_name VARCHAR(255) NOT NULL,
            password_hash TEXT NOT NULL
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            price NUMERIC NOT NULL,
            description TEXT
        );
        """
    )
    cur.close()


def seed_users(conn):
    cur = conn.cursor()
    demo_users = [
        ("demo+db@example.com", "Demo DB User", get_password_hash("password123")),
    ]
    sql = "INSERT INTO users (email, full_name, password_hash) VALUES %s ON CONFLICT (email) DO NOTHING"
    try:
        execute_values(cur, sql, demo_users)
        print("Seeded users")
    finally:
        cur.close()


def seed_products(conn):
    cur = conn.cursor()
    # Use a curated fixed catalog of friendly product names and descriptions
    # so the demo always looks consistent and polished. This guarantees
    # deterministic product names/descriptions (for adding images later).
    FIXED_PRODUCTS = [
        {"name": "Воздушный фильтр VAG (1.4/1.8/2.0 TSI)", "price": 19.90, "description": "Оригинальный воздушный фильтр для двигателей VAG TSI — улучшенная очистка воздуха, продлевает ресурс двигателя и оптимизирует расход топлива."},
        {"name": "Тормозные колодки передние VAG", "price": 54.99, "description": "Комплект передних тормозных колодок для моделей Volkswagen/Skoda/Seat — высокая износостойкость и стабильное торможение в любых условиях."},
        {"name": "Свеча зажигания VAG (платиновая)", "price": 12.50, "description": "Платиновые свечи зажигания, рекомендованы для бензиновых двигателей VAG — повышенная стабильность искрообразования и длительный ресурс."},
        {"name": "Ремень ГРМ VAG (комплект)", "price": 129.00, "description": "Комплект ремня ГРМ с роликами для двигателей VAG — критически важная замена по регламенту для предотвращения серьёзных поломок."},
        {"name": "Амортизатор передний VAG (левый)", "price": 89.99, "description": "Передний амортизатор оригинального типа — обеспечивает комфорт и управляемость при любых дорожных условиях."},
        {"name": "Фара левая VAG (Halogen)", "price": 149.00, "description": "Левая фара с галогенной лампой для моделей VAG — простой монтаж, соответствие заводским характеристикам освещения."},
        {"name": "Радиатор охлаждения VAG (замена)", "price": 199.50, "description": "Охлаждающий радиатор высокого качества, предназначен для замены штатного радиатора на автомобилях VAG — надёжное охлаждение двигателя."},
        {"name": "Термостат VAG (оригинал)", "price": 29.90, "description": "Термостат с точной температурной калибровкой для корректной работы системы охлаждения VAG; снижает износ двигателя при прогреве."},
        {"name": "Диск сцепления VAG (комплект)", "price": 179.00, "description": "Комплект диска сцепления и выжимного подшипника для ручной коробки передач VAG — обеспечивает надёжную передачу крутящего момента."},
        {"name": "Масляный фильтр VAG (оригинал)", "price": 9.99, "description": "Оригинальный масляный фильтр VAG — эффективная фильтрация масла и продление срока службы двигателя."},
    ]

    # ensure description column exists (for older DBs)
    try:
        cur.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS description TEXT")
    except Exception:
        pass

    # ensure stock column exists and set a sensible default and NOT NULL constraint
    try:
        # Add column if missing (nullable)
        cur.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS stock INTEGER")
        # Set NULL stocks to a reasonable demo value (10)
        cur.execute("UPDATE products SET stock = 10 WHERE stock IS NULL")
        # Set default for future inserts
        cur.execute("ALTER TABLE products ALTER COLUMN stock SET DEFAULT 0")
        # Make column NOT NULL now that values exist
        cur.execute("ALTER TABLE products ALTER COLUMN stock SET NOT NULL")
    except Exception as e:
        # Surface errors in CI logs to help debugging
        print("Failed to ensure products.stock column exists:", e)
        # Re-raise so the seeder step fails loudly in CI instead of silently continuing
        raise

    # Always use the fixed product list for deterministic demo data
    NUM = len(FIXED_PRODUCTS)
    for idx, item in enumerate(FIXED_PRODUCTS, start=1):
        cur.execute(
            """
            INSERT INTO products (id, name, price, description, stock) VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, price = EXCLUDED.price, description = EXCLUDED.description, stock = EXCLUDED.stock
            """,
            (idx, item['name'], item['price'], item['description'], item.get('stock', 10)),
        )

    # remove any leftover demo products with id > NUM (keep DB tidy)
    cur.execute("DELETE FROM products WHERE id > %s", (NUM,))
    print(f"Seeded {NUM} fixed demo products")
    # Dump products table for debugging (id, name, stock)
    try:
        cur.execute("SELECT id, name, stock FROM products ORDER BY id")
        rows = cur.fetchall()
        print("DB products after seeding:")
        for r in rows:
            print(r)
    except Exception as e:
        print("Could not query products after seeding:", e)
    cur.close()


def try_reset_inventory():
    inv_url = os.environ.get("INVENTORY_URL", "http://localhost:8008/api/inventory/reset")
    payload = {"items": {1: 10, 2: 5, 3: 2}}
    try:
        r = httpx.post(inv_url, json=payload, timeout=5.0)
        print("Inventory reset status:", r.status_code, r.text)
    except Exception as e:
        print("Could not reset inventory (service may be down):", e)


def main():
    print("DB seed starting, DATABASE_URL=", DATABASE_URL)
    try:
        conn = connect_db(DATABASE_URL)
    except Exception:
        sys.exit(1)

    ensure_tables(conn)
    seed_users(conn)
    seed_products(conn)

    # Try to reset inventory via HTTP (best-effort). Useful for CI where services are up.
    try_reset_inventory()

    conn.close()
    print("DB seed complete")


if __name__ == "__main__":
    main()
