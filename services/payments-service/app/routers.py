from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
import uuid
from datetime import datetime

router = APIRouter(prefix="/api/payments", tags=["payments"])

class PaymentCreate(BaseModel):
    order_id: int
    amount: float
    currency: str = "USD"
    payment_method: str
    idempotency_key: str | None = None

class PaymentOut(BaseModel):
    payment_id: str
    order_id: int
    status: str
    amount: float
    currency: str
    processed_at: datetime

@router.post("/charge", response_model=PaymentOut)
async def charge(payload: PaymentCreate):
    # Simulate charging (in real life integrate PSP)
    if payload.amount <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid amount")

    # Test hook: if client submits payment_method == 'fail', simulate a failure
    if payload.payment_method == "fail":
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Simulated payment failure")

    payment_id = str(uuid.uuid4())
    return PaymentOut(
        payment_id=payment_id,
        order_id=payload.order_id,
        status="succeeded",
        amount=payload.amount,
        currency=payload.currency,
        processed_at=datetime.utcnow()
    )
