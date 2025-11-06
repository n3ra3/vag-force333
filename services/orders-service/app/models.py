from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from shared.database import Base


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    status = Column(String, nullable=False)
    amount = Column(Float, nullable=True)
    currency = Column(String(10), nullable=True)
    idempotency_key = Column(String(128), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
