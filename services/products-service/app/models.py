from sqlalchemy import Column, Integer, String, Numeric, Text
from shared.database import Base


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    price = Column(Numeric, nullable=False)
    description = Column(Text, nullable=True)
