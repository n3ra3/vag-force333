import uuid
import httpx
import pytest

ORDERS_URL = "http://localhost:8004/api/orders/checkout"
INVENTORY_URL = "http://localhost:8008/api/inventory"


def service_available(url: str) -> bool:
    try:
        r = httpx.get(url.replace('/checkout', ''), timeout=2.0)
        return True
    except Exception:
        return False


def find_available_product(candidate_ids=(1, 2, 3)) -> int:
    """Return first product_id with quantity >= 1, or raise pytest.skip."""
    for pid in candidate_ids:
        try:
            r = httpx.get(f"{INVENTORY_URL}/items/{pid}", timeout=2.0)
            if r.status_code == 200:
                data = r.json()
                if data.get("quantity", 0) >= 1:
                    return pid
        except Exception:
            # inventory service might be down; let caller handle skip
            pass
    pytest.skip("No inventory available for candidate product ids or inventory service unreachable")


@pytest.mark.skipif(not service_available(ORDERS_URL), reason="orders service not reachable on localhost:8004")
def test_checkout_happy_path():
    product_id = find_available_product()
    idempotency_key = str(uuid.uuid4())
    payload = {
        "user_id": 12345,
        "items": [{"product_id": product_id, "quantity": 1}],
        "amount": 3.14,
        "currency": "USD",
        "payment_method": "card",
        "idempotency_key": idempotency_key,
    }

    r = httpx.post(ORDERS_URL, json=payload, timeout=15.0)
    assert r.status_code == 200, f"unexpected status: {r.status_code}, body: {r.text}"
    data = r.json()
    assert "order_id" in data
    assert data["status"] == "paid"


@pytest.mark.skipif(not service_available(ORDERS_URL), reason="orders service not reachable on localhost:8004")
def test_checkout_idempotent_duplicate():
    product_id = find_available_product()
    idempotency_key = str(uuid.uuid4())
    payload = {
        "user_id": 12345,
        "items": [{"product_id": product_id, "quantity": 1}],
        "amount": 3.14,
        "currency": "USD",
        "payment_method": "card",
        "idempotency_key": idempotency_key,
    }

    r1 = httpx.post(ORDERS_URL, json=payload, timeout=15.0)
    assert r1.status_code == 200, f"first request failed: {r1.status_code} {r1.text}"
    d1 = r1.json()

    r2 = httpx.post(ORDERS_URL, json=payload, timeout=15.0)
    assert r2.status_code == 200, f"second request failed: {r2.status_code} {r2.text}"
    d2 = r2.json()

    assert d1.get("order_id") == d2.get("order_id"), "idempotent requests returned different order ids"


@pytest.mark.skipif(not service_available(ORDERS_URL), reason="orders service not reachable on localhost:8004")
def test_compensation_on_payment_failure():
    # Use test endpoints to make deterministic inventory counts
    # Choose a product id and set its qty to 2, then attempt a payment that will fail
    pid = 2
    # reset inventory to 2
    try:
        httpx.post("http://localhost:8008/api/inventory/reset", json={"items": {str(pid): 2}}, timeout=3.0)
    except Exception:
        pytest.skip("Inventory reset endpoint not available")

    # Confirm inventory is 2
    r0 = httpx.get(f"http://localhost:8008/api/inventory/items/{pid}", timeout=3.0)
    assert r0.status_code == 200
    before_qty = r0.json().get("quantity", 0)

    idempotency_key = str(uuid.uuid4())
    payload = {
        "user_id": 99999,
        "items": [{"product_id": pid, "quantity": 1}],
        "amount": 1.00,
        "currency": "USD",
        "payment_method": "fail",  # triggers simulated failure in payments-service
        "idempotency_key": idempotency_key,
    }

    r = httpx.post(ORDERS_URL, json=payload, timeout=15.0)
    assert r.status_code != 200

    # After failure, inventory should be restored to original quantity (best-effort release)
    r2 = httpx.get(f"http://localhost:8008/api/inventory/items/{pid}", timeout=3.0)
    assert r2.status_code == 200
    after_qty = r2.json().get("quantity", 0)
    # best-effort release: inventory should be restored to at least the previous value
    assert after_qty >= before_qty, f"inventory not restored (expected >=): before={before_qty} after={after_qty}"
