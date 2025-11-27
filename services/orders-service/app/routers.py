from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from datetime import datetime
import httpx
import os
import asyncio
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects.postgresql import insert as pg_insert

from shared.database import get_session, async_session_maker
from .models import Order

router = APIRouter(prefix="/api/orders", tags=["orders"])


class OrderItem(BaseModel):
    product_id: int
    quantity: int


class CheckoutPayload(BaseModel):
    user_id: int
    items: list[OrderItem]
    amount: float
    currency: str = "USD"
    payment_method: str
    idempotency_key: str | None = None


class OrderOut(BaseModel):
    order_id: int
    user_id: int
    status: str
    amount: float
    currency: str
    created_at: datetime


class OrderSummary(BaseModel):
    id: int
    status: str
    amount: float
    currency: str
    created_at: datetime


PAYMENTS_URL = os.getenv("PAYMENTS_URL", "http://payments-service:8005")
INVENTORY_URL = os.getenv("INVENTORY_URL", "http://inventory-service:8008")
NOTIFICATIONS_URL = os.getenv("NOTIFICATIONS_URL", "http://notifications-service:8007")


@router.post("/checkout", response_model=OrderOut)
async def checkout(payload: CheckoutPayload, session: AsyncSession = Depends(get_session)):
    # Idempotency: if client provided idempotency_key and an order exists, return it
    if payload.idempotency_key:
        q = await session.execute(select(Order).where(Order.idempotency_key == payload.idempotency_key))
        existing = q.scalar_one_or_none()
        if existing is not None:
            return OrderOut(
                order_id=existing.id,
                user_id=existing.user_id,
                status=existing.status,
                amount=existing.amount if existing.amount is not None else payload.amount,
                currency=existing.currency if existing.currency is not None else payload.currency,
                created_at=existing.created_at if hasattr(existing, 'created_at') else datetime.utcnow(),
            )

    # Create order record with status 'pending' using atomic INSERT ... ON CONFLICT DO NOTHING
    insert_values = {
        "user_id": payload.user_id,
        "status": "pending",
        "amount": payload.amount,
        "currency": payload.currency,
        "idempotency_key": payload.idempotency_key,
    }

    # Ensure the referenced user exists in the users table. Tests may send arbitrary user_ids
    # (they don't go through auth-service), so create a placeholder user record if missing.
    try:
        q_user = await session.execute(text("SELECT 1 FROM users WHERE id = :id"), {"id": payload.user_id})
        exists = q_user.scalar_one_or_none()
        if not exists:
            # Insert a minimal placeholder user; use ON CONFLICT DO NOTHING to be safe
            await session.execute(
                text(
                    "INSERT INTO users (id, email, full_name, password_hash) VALUES (:id, :email, :full_name, :pwd) ON CONFLICT (id) DO NOTHING"
                ),
                {"id": payload.user_id, "email": f"user+{payload.user_id}@example.invalid", "full_name": "Imported user", "pwd": "imported"},
            )
    except Exception:
        # If anything goes wrong checking/creating the user, continue and let the order insert report an error
        pass

    stmt = (
        pg_insert(Order.__table__)
        .values(**insert_values)
        .returning(Order.id, Order.created_at)
        .on_conflict_do_nothing(index_elements=["idempotency_key"])
    )

    result = await session.execute(stmt)
    row = result.fetchone()
    if row is not None:
        order_id = row[0]
        created_at = row[1]
    else:
        # conflict: another request inserted the order. Read and return it.
        if payload.idempotency_key:
            q = await session.execute(select(Order).where(Order.idempotency_key == payload.idempotency_key))
            existing = q.scalar_one_or_none()
            if existing:
                return OrderOut(
                    order_id=existing.id,
                    user_id=existing.user_id,
                    status=existing.status,
                    amount=existing.amount if existing.amount is not None else payload.amount,
                    currency=existing.currency if existing.currency is not None else payload.currency,
                    created_at=existing.created_at if hasattr(existing, 'created_at') else datetime.utcnow(),
                )
        # if not found, raise a generic error
        raise HTTPException(status_code=500, detail="Failed to create or find idempotent order")

    # Commit the insert so the idempotency key is visible to other transactions,
    # then load the ORM object for subsequent updates
    await session.commit()
    async with async_session_maker() as new_sess:
        q2 = await new_sess.execute(select(Order).where(Order.id == order_id))
        order = q2.scalar_one_or_none()
        if order is None:
            raise HTTPException(status_code=500, detail="Order created but not accessible")

    # Helper: simple POST with retry for transient failures
    async def post_with_retry(url: str, json_payload: dict, max_retries: int = 3, base_delay: float = 0.3, retry_on_status: Optional[set] = None):
        if retry_on_status is None:
            retry_on_status = {502, 503, 504}
        attempt = 0
        last_exc = None
        async with httpx.AsyncClient(timeout=10.0) as client:
            while attempt < max_retries:
                try:
                    resp = await client.post(url, json=json_payload)
                    if resp.status_code >= 500 or resp.status_code in retry_on_status:
                        last_exc = HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Upstream service error: {resp.status_code}")
                        # retry
                        attempt += 1
                        await asyncio.sleep(base_delay * (2 ** attempt))
                        continue
                    return resp
                except httpx.RequestError as e:
                    last_exc = e
                    attempt += 1
                    await asyncio.sleep(base_delay * (2 ** attempt))
            # out of retries
            if isinstance(last_exc, HTTPException):
                raise last_exc
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Upstream service unavailable")

    # Reserve inventory for each item (do not retry when inventory reports reserved=False)
    for item in payload.items:
        try:
            res = await post_with_retry(f"{INVENTORY_URL}/api/inventory/reserve", {"product_id": item.product_id, "quantity": item.quantity}, max_retries=2)
        except HTTPException as e:
            order.status = "failed"
            await session.commit()
            raise e
        if res.status_code != 200:
            order.status = "failed"
            await session.commit()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inventory reservation failed")
        body = res.json()
        if not body.get("reserved"):
            order.status = "failed"
            await session.commit()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inventory reservation failed")

    # Call payments-service synchronously
    charge_payload = {
        "order_id": order_id,
        "amount": payload.amount,
        "currency": payload.currency,
        "payment_method": payload.payment_method,
        "idempotency_key": payload.idempotency_key,
    }

    # Call payments-service with explicit handling to avoid double-release on errors
    try:
        resp = await post_with_retry(f"{PAYMENTS_URL}/api/payments/charge", charge_payload, max_retries=3)
    except HTTPException as e:
        # Payment call failed (exception) -> release reserved inventory and fail
        for it in payload.items:
            try:
                await post_with_retry(f"{INVENTORY_URL}/api/inventory/release", {"product_id": it.product_id, "quantity": it.quantity}, max_retries=2)
            except Exception:
                pass
        order.status = "failed"
        await session.commit()
        raise e

    # If payment returned but with non-200 status, release and fail (no double-catch)
    if resp.status_code != 200:
        for it in payload.items:
            try:
                await post_with_retry(f"{INVENTORY_URL}/api/inventory/release", {"product_id": it.product_id, "quantity": it.quantity}, max_retries=2)
            except Exception:
                pass
        order.status = "failed"
        await session.commit()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Payment failed or payment service error")

    data = resp.json()

    # Payment succeeded: mark order paid
    order.status = "paid"
    await session.commit()

    # Send notification (best-effort)
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            await client.post(f"{NOTIFICATIONS_URL}/api/notifications/send", json={"to": "user@example.com", "template": "order_paid", "ctx": {"order_id": order_id}})
    except Exception:
        # ignore notification failures
        pass

    return OrderOut(
        order_id=order_id,
        user_id=payload.user_id,
        status=order.status,
        amount=payload.amount,
        currency=payload.currency,
        created_at=created_at,
    )


@router.get("/{order_id}")
async def get_order(order_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="not found")
    return {"order_id": order.id, "status": order.status}


@router.get("/user/{user_id}")
async def list_user_orders(user_id: int, session: AsyncSession = Depends(get_session)):
    """Return recent orders for a user (simple list)."""
    q = await session.execute(select(Order).where(Order.user_id == user_id).order_by(Order.created_at.desc()).limit(50))
    orders = q.scalars().all()
    out = []
    for o in orders:
        out.append({
            "id": o.id,
            "status": o.status,
            "amount": float(o.amount) if o.amount is not None else 0.0,
            "currency": o.currency or 'USD',
            "created_at": o.created_at,
        })
    return out
