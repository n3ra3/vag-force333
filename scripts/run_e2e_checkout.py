#!/usr/bin/env python3
"""Простой e2e-скрипт: вызывает checkout в orders-service и печатает ответ."""
import uuid
import json
import urllib.request

URL = "http://localhost:8004/api/orders/checkout"

payload = {
    "user_id": 42,
    "items": [{"product_id": 1, "quantity": 1}],
    "amount": 3.14,
    "currency": "USD",
    "payment_method": "card",
    "idempotency_key": f"e2e-{uuid.uuid4()}"
}

data = json.dumps(payload).encode('utf-8')
req = urllib.request.Request(URL, data=data, headers={"Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = resp.read().decode('utf-8')
        print('Status:', resp.status)
        print(body)
except Exception as e:
    print('Request failed:', e)
