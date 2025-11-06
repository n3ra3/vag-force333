from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_session
from .models import Product

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("/", summary="List products")
async def list_products(limit: int = 200, session: AsyncSession = Depends(get_session)):
    stmt = select(Product).limit(limit)
    res = await session.execute(stmt)
    products = res.scalars().all()
    return [
        {"id": p.id, "name": p.name, "price": float(p.price), "description": (p.description or "")}
        for p in products
    ]


@router.get("/{product_id}", summary="Get product by id")
async def get_product(product_id: int, session: AsyncSession = Depends(get_session)):
    product = await session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"id": product.id, "name": product.name, "price": float(product.price), "description": (product.description or "")}
