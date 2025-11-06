from sqlalchemy import (
    Column, Integer, String, Text, ForeignKey, DateTime, func,
    Numeric, CheckConstraint, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from .database import Base

# 👤 Пользователь
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)

    # ✅ связь с корзиной и заказами
    cart_items = relationship("CartItem", back_populates="user", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)         # 💰 точные деньги
    image_url = Column(String(255), nullable=True)
    category = Column(String(100), nullable=True)
    stock = Column(Integer, nullable=False, default=0)      # 📦 остаток на складе

    cart_items = relationship("CartItem", back_populates="product", cascade="all, delete-orphan", passive_deletes=True)
    order_items = relationship("OrderItem", back_populates="product", cascade="all, delete-orphan", passive_deletes=True)

    __table_args__ = (
        CheckConstraint("price >= 0", name="ck_products_price_nonneg"),
        CheckConstraint("stock >= 0", name="ck_products_stock_nonneg"),
        Index("ix_products_category_name", "category", "name"),
    )


class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"))
    quantity = Column(Integer, nullable=False, default=1)

    user = relationship("User", back_populates="cart_items", passive_deletes=True)
    product = relationship("Product", back_populates="cart_items", passive_deletes=True)

    __table_args__ = (
        UniqueConstraint("user_id", "product_id", name="uq_cart_user_product"),  # 🚫 дубли в корзине
        CheckConstraint("quantity > 0", name="ck_cartitem_quantity_pos"),
        Index("ix_cart_items_user", "user_id"),
    )


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String(50), nullable=False, default="pending")  # pending/paid/shipped/delivered/cancelled
    total_price = Column(Numeric(12, 2), nullable=False, default=0)  # 💰 сумма заказа

    user = relationship("User", back_populates="orders", passive_deletes=True)
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan", passive_deletes=True)

    __table_args__ = (
        CheckConstraint("total_price >= 0", name="ck_orders_total_nonneg"),
        Index("ix_orders_user_created", "user_id", "created_at"),
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"))
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"))
    quantity = Column(Integer, nullable=False, default=1)
    price = Column(Numeric(10, 2), nullable=False)  # 💰 фиксируем цену на момент покупки

    order = relationship("Order", back_populates="items", passive_deletes=True)
    product = relationship("Product", back_populates="order_items", passive_deletes=True)

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_orderitem_quantity_pos"),
        CheckConstraint("price >= 0", name="ck_orderitem_price_nonneg"),
    )
