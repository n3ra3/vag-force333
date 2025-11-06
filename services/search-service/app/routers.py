from fastapi import APIRouter

router = APIRouter(prefix="/api/search", tags=["search"])

@router.get("/q")
async def query(q: str):
    # dummy search (in real implementation call DB or search engine)
    sample = [
        {"id": 1, "name": "Tire"},
        {"id": 2, "name": "Oil"},
        {"id": 3, "name": "Brake pads"}
    ]
    return [p for p in sample if q.lower() in p["name"].lower()]
