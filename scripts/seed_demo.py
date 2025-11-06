"""Seed demo data by calling service HTTP APIs.

This script is intentionally simple and idempotent-ish: it will attempt to register
an example user (if auth service is available) and will print helpful info for
running the e2e checkout tests.

Usage:
    python scripts/seed_demo.py

Assumptions:
 - auth service: http://localhost:8001 (POST /api/auth/register)
 - inventory has in-memory products (the inventory-service ships with product ids 1..3)

This script is convenience only and does not require DB access.
"""
import uuid
import sys
import httpx

AUTH_URL = "http://localhost:8001/api/auth"
INVENTORY_URL = "http://localhost:8008/api/inventory"


def try_register_user(email: str, password: str, full_name: str = "Demo User"):
    url = f"{AUTH_URL}/register"
    payload = {"email": email, "password": password, "full_name": full_name}
    try:
        r = httpx.post(url, json=payload, timeout=5.0)
        if r.status_code in (200, 201):
            print(f"Registered user: {email} -> response: {r.json()}")
            # Try to return id if provided
            data = r.json()
            return data.get("id") if isinstance(data, dict) else None
        else:
            print(f"Register returned {r.status_code}: {r.text}")
            return None
    except Exception as e:
        print(f"Auth service unavailable: {e}")
        return None


def check_inventory(product_id: int):
    try:
        r = httpx.get(f"{INVENTORY_URL}/items/{product_id}", timeout=3.0)
        if r.status_code == 200:
            print(f"Inventory for product {product_id}: {r.json()}")
            return r.json()
        else:
            print(f"Inventory lookup returned {r.status_code}: {r.text}")
    except Exception as e:
        print(f"Inventory service unavailable: {e}")
    return None


def main():
    print("Seeding demo data (best-effort).")
    email = "demo+user@example.com"
    password = "password123"  # >=8 chars required by auth service

    user_id = try_register_user(email, password, full_name="Demo User")
    if user_id:
        print(f"Created user id: {user_id}")
    else:
        print("Could not obtain numeric user id from auth service; tests may use arbitrary user_id values.")

    # Check inventory for the known demo product ids (1..3)
    for pid in (1, 2, 3):
        check_inventory(pid)

    print("\nReady. Example checkout payload (use this in tests or scripts):")
    print("{" )
    print('  "user_id": 12345,')
    print('  "items": [{"product_id": 1, "quantity": 1}],')
    print('  "amount": 9.50,')
    print('  "currency": "USD",')
    print('  "payment_method": "card",')
    print(f'  "idempotency_key": "{uuid.uuid4()}"')
    print("}")


if __name__ == "__main__":
    main()
