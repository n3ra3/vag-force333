# app/cart.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import List

from .database import get_session
from .models import CartItem, Product, User
from .schemas import CartItemOut, CartItemCreate
from .auth import get_current_user

router = APIRouter(prefix="/api/cart", tags=["cart"])

@router.get("", response_model=List[CartItemOut])
async def get_cart(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    result = await session.execute(
        select(CartItem)
        .options(selectinload(CartItem.product))
        .where(CartItem.user_id == current_user.id)
        .order_by(CartItem.id.desc())
    )
    return result.scalars().all()

@router.get("/count")
async def get_cart_count(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    res = await session.execute(
        select(func.count()).select_from(CartItem).where(CartItem.user_id == current_user.id)
    )
    return {"count": res.scalar_one()}

@router.post("/add", response_model=CartItemOut, status_code=status.HTTP_201_CREATED)
async def add_to_cart(
    payload: CartItemCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    # Проверяем товар
    prod_res = await session.execute(select(Product).where(Product.id == payload.product_id))
    product = prod_res.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")

    if payload.quantity <= 0:
        raise HTTPException(status_code=400, detail="Количество должно быть > 0")

    # Ищем существующую позицию корзины
    ci_res = await session.execute(
        select(CartItem).where(
            CartItem.user_id == current_user.id,
            CartItem.product_id == payload.product_id,
        )
    )
    existing = ci_res.scalar_one_or_none()

    # Контроль остатков
    new_qty = (existing.quantity if existing else 0) + payload.quantity
    if product.stock is not None and new_qty > product.stock:
        raise HTTPException(status_code=400, detail="Недостаточно товара на складе")

    if existing:
        existing.quantity = new_qty
        await session.commit()
        # Гарантируем, что product уже загружен (без ленивых запросов при сериализации)
        await session.refresh(existing, attribute_names=["product"])
        return existing

    item = CartItem(
        user_id=current_user.id,
        product_id=payload.product_id,
        quantity=payload.quantity,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item, attribute_names=["product"])
    return item

@router.put("/{item_id}", response_model=CartItemOut)
async def update_cart_item(
    item_id: int,
    payload: CartItemCreate,  # product_id игнорируем, используем только quantity
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    res = await session.execute(
        select(CartItem)
        .options(selectinload(CartItem.product))
        .where(CartItem.id == item_id, CartItem.user_id == current_user.id)
    )
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Позиция корзины не найдена")

    if payload.quantity <= 0:
        raise HTTPException(status_code=400, detail="Количество должно быть > 0")

    # Контроль остатков
    prod_res = await session.execute(select(Product).where(Product.id == item.product_id))
    product = prod_res.scalar_one()
    if product.stock is not None and payload.quantity > product.stock:
        raise HTTPException(status_code=400, detail="Недостаточно товара на складе")

    item.quantity = payload.quantity
    await session.commit()
    await session.refresh(item, attribute_names=["product"])
    return item

@router.delete("/{item_id}", status_code=204)
async def remove_cart_item(
    item_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    res = await session.execute(
        select(CartItem).where(CartItem.id == item_id, CartItem.user_id == current_user.id)
    )
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Позиция корзины не найдена")

    await session.delete(item)
    await session.commit()
    return

@router.delete("/clear", status_code=204)
async def clear_cart(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    result = await session.execute(select(CartItem).where(CartItem.user_id == current_user.id))
    for it in result.scalars().all():
        await session.delete(it)
    await session.commit()
    return
