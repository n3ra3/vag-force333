from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict
import os

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


class InventoryItem(BaseModel):
    product_id: int
    quantity: int


# simple in-memory store for dev/demo
"""Simple in-memory inventory store for local dev/demo.

Products not present in the `INVENTORY` map will be treated as having
ample demo stock (DEFAULT_QTY) to avoid spurious reservation failures
when the seeder doesn't explicitly set inventory counts for every
product. In production this would be backed by a real DB.
"""

DEFAULT_QTY = 100

INVENTORY: Dict[int, int] = {
    1: 10,
    2: 5,
    3: 0,
}


@router.get("/items/{product_id}")
async def get_item(product_id: int):
    qty = INVENTORY.get(product_id, 0)
    return {"product_id": product_id, "quantity": qty}


@router.post("/reserve")
async def reserve_item(item: InventoryItem):
    # Treat missing product ids as having DEFAULT_QTY for demo purposes.
    qty = INVENTORY.get(item.product_id, DEFAULT_QTY)
    if item.quantity <= 0 or item.quantity > qty:
        return {"reserved": False}
    INVENTORY[item.product_id] = qty - item.quantity
    return {"reserved": True, "product_id": item.product_id, "remaining": INVENTORY[item.product_id]}


class InventoryReset(BaseModel):
    items: Dict[int, int]


@router.post("/reset")
async def reset_inventory(payload: InventoryReset):
    """Test-only endpoint: set inventory quantities.

    Enabled by default for local development. To disable in CI or production,
    set environment variable ALLOW_TEST_ENDPOINTS to '0'.
    """
    if os.getenv("ALLOW_TEST_ENDPOINTS", "1") != "1":
        raise HTTPException(status_code=403, detail="Test endpoints disabled")

    for pid_raw, qty in payload.items.items():
        # JSON object keys are strings; coerce to int when possible
        try:
            pid = int(pid_raw)
        except Exception:
            pid = pid_raw
        if qty < 0:
            raise HTTPException(status_code=400, detail="Quantity must be >= 0")
        INVENTORY[pid] = qty

    return {"ok": True, "inventory": INVENTORY}


@router.post("/release")
async def release_inventory(item: InventoryItem):
    """Return previously reserved quantity back to inventory.

    This is a best-effort test/dev endpoint used by orders-service for compensation.
    """
    if item.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be > 0")
    INVENTORY[item.product_id] = INVENTORY.get(item.product_id, 0) + item.quantity
    return {"released": True, "product_id": item.product_id, "quantity": INVENTORY[item.product_id]}
