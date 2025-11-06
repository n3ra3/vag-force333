from fastapi import APIRouter

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

@router.get("/stats")
async def stats():
    # Minimal placeholder statistics; later we can query DB for real numbers
    return {
        "users": 10,
        "products": 25,
        "orders": 3,
        "revenue": 1234.56
    }
