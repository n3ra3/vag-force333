# app/shop.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from .database import get_session
from .models import Product, User
from .schemas import ProductOut, ProductCreate
from .auth import get_current_user  # если нужно ограничивать создание товаров

router = APIRouter(prefix="/api/products", tags=["products"])

@router.get("", response_model=List[ProductOut])
async def list_products(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Product).order_by(Product.id.desc()))
    return result.scalars().all()

@router.get("/{product_id}", response_model=ProductOut)
async def get_product(product_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")
    return product

# ниже 3 эндпоинта можно временно оставить открытыми, либо добавить проверку роли
@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),  # ограничиваем только для залогиненных (можно расширить до admin)
):
    product = Product(
        name=payload.name,
        description=payload.description,
        price=payload.price,
        image_url=payload.image_url,
        category=payload.category,
        stock=0,  # стартовый остаток; регулируйте через PUT
    )
    session.add(product)
    await session.commit()
    await session.refresh(product)
    return product

@router.put("/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: int,
    payload: ProductCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    result = await session.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")

    product.name = payload.name
    product.description = payload.description
    product.price = payload.price
    product.image_url = payload.image_url
    product.category = payload.category

    await session.commit()
    await session.refresh(product)
    return product

@router.delete("/{product_id}", status_code=204)
async def delete_product(
    product_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    result = await session.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")

    await session.delete(product)
    await session.commit()
    return
