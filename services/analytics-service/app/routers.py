from fastapi import APIRouter

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

@router.get("/overview")
async def overview():
    # Placeholder: return sample metrics
    return {"visits": 12345, "orders": 321, "conversion": 0.025}
