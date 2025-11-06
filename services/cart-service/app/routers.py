from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/cart", tags=["cart"])


@router.get("/me")
async def get_my_cart():
    # placeholder: empty cart
    return {"items": [], "total": 0}


@router.post("/add")
async def add_to_cart(product_id: int, quantity: int = 1):
    # placeholder: echo
    return {"product_id": product_id, "quantity": quantity}
