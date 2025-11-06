# app/orders.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from decimal import Decimal
from typing import List

from .database import get_session
from .models import CartItem, Order, OrderItem, Product, User
from .schemas import CartItemOut  # можно добавить Order схемы позже
from .auth import get_current_user

router = APIRouter(prefix="/api/orders", tags=["orders"])

# 🧾 История заказов текущего пользователя
@router.get("", response_model=list[dict])
async def list_orders(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy.orm import selectinload
    res = await session.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.user_id == current_user.id)
        .order_by(Order.created_at.desc())
    )
    orders = res.scalars().all()

    # простая выдача с суммой и количеством позиций
    out = []
    for o in orders:
        out.append({
            "id": o.id,
            "status": o.status,
            "created_at": o.created_at,
            "total_price": str(o.total_price),  # Decimal -> str
            "items_count": len(o.items),
        })
    return out

# 📦 Детали одного заказа
@router.get("/{order_id}", response_model=dict)
async def order_detail(
    order_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    res = await session.execute(select(Order).where(Order.id == order_id, Order.user_id == current_user.id))
    order = res.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")

    items_data = []
    for it in order.items:
        items_data.append({
            "id": it.id,
            "product_id": it.product_id,
            "product_name": it.product.name if it.product else None,
            "quantity": it.quantity,
            "price": str(it.price),
            "line_total": str(Decimal(it.quantity) * it.price),
        })

    return {
        "id": order.id,
        "status": order.status,
        "created_at": order.created_at,
        "total_price": str(order.total_price),
        "items": items_data,
    }

# ✅ Оформление заказа: перенос корзины в Order/OrderItem, проверка stock, уменьшение остатков
@router.post("/create", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_order(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    # 1) Берём корзину пользователя
    cart_res = await session.execute(select(CartItem).where(CartItem.user_id == current_user.id))
    cart_items = cart_res.scalars().all()
    if not cart_items:
        raise HTTPException(status_code=400, detail="Корзина пуста")

    # 2) Проверяем наличие товара на складе
    # и одновременно считаем сумму
    total = Decimal("0.00")
    products_map = {}  # product_id -> Product

    for ci in cart_items:
        prod_res = await session.execute(select(Product).where(Product.id == ci.product_id))
        product = prod_res.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=400, detail=f"Товар ID {ci.product_id} не найден")
        products_map[product.id] = product

        if product.stock < ci.quantity:
            raise HTTPException(status_code=400, detail=f"Недостаточно на складе: {product.name}")

        line_total = (Decimal(product.price) * Decimal(ci.quantity))
        total += line_total

    # 3) Создаём заказ
    order = Order(user_id=current_user.id, status="pending", total_price=total)
    session.add(order)
    await session.flush()  # получим order.id

    # 4) Создаём OrderItem'ы и уменьшаем stock
    for ci in cart_items:
        p = products_map[ci.product_id]
        oi = OrderItem(
            order_id=order.id,
            product_id=p.id,
            quantity=ci.quantity,
            price=p.price,  # фиксируем цену на момент покупки
        )
        session.add(oi)

        # уменьшаем остатки
        p.stock = p.stock - ci.quantity

    # 5) Очищаем корзину
    for ci in cart_items:
        await session.delete(ci)

    await session.commit()
    await session.refresh(order)

    return {
        "message": "Заказ создан",
        "order_id": order.id,
        "total_price": str(order.total_price),
        "status": order.status,
    }
