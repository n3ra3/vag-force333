from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

class NotificationPayload(BaseModel):
    to: str
    channel: str = "email"
    template: str
    ctx: dict | None = None

@router.post("/send")
async def send_notification(payload: NotificationPayload):
    # Placeholder - in real app integrate with SMTP/SMS/push providers
    return {
        "to": payload.to,
        "channel": payload.channel,
        "template": payload.template,
        "sent_at": datetime.utcnow()
    }
