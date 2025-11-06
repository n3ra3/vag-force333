# app/schemas.py
from pydantic import BaseModel, EmailStr
from typing import Optional, List

# 👤 Пользователь
class UserBase(BaseModel):
    email: EmailStr
    full_name: str

class UserCreate(UserBase):
    password: str

class UserOut(UserBase):
    id: int
    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    email: EmailStr
    password: str


# 🛍️ Товар
class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    image_url: Optional[str] = None
    category: Optional[str] = None

class ProductCreate(ProductBase):
    # пусть при создании можно задать остаток; по умолчанию 0
    stock: int = 0

class ProductOut(ProductBase):
    id: int
    stock: int
    class Config:
        from_attributes = True


# 🛒 Элемент корзины
class CartItemBase(BaseModel):
    product_id: int
    quantity: int

class CartItemCreate(CartItemBase):
    pass

class CartItemOut(BaseModel):
    id: int
    product_id: int
    quantity: int
    user_id: int
    product: Optional[ProductOut] = None
    class Config:
        from_attributes = True


# 📦 Добавление в корзину
class CartAddRequest(BaseModel):
    product_id: int
    quantity: int


# 📊 Сводка корзины (единый формат ответа /api/cart)
class CartSummary(BaseModel):
    items: List[CartItemOut]
    count: int
    total: float
