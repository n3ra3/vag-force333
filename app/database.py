# app/database.py
import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Use DATABASE_URL env var when available (makes containerized runs configurable)
# Fallback to a sensible default pointing to the compose Postgres service.
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@db:5432/vag_force_db",
)

# Create engine
engine = create_async_engine(DATABASE_URL, echo=True, future=True)

# Create session factory
async_session_maker = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# Base declarative
Base = declarative_base()

from typing import AsyncGenerator

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
