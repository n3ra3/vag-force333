import os
import urllib.parse
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

# По умолчанию используем локальную БД `vag_force_db` (локально в pgAdmin).
# Для контейнеров на Windows можно указать host.docker.internal в DATABASE_URL.
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:12345@localhost:5432/vag_force_db")

engine = create_async_engine(DATABASE_URL, echo=True, future=True)

async_session_maker = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

Base = declarative_base()

from typing import AsyncGenerator

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


def ensure_database_exists():
    """
    Проверяет, существует ли база данных, указанная в DATABASE_URL, и создаёт её
    при необходимости, подключаясь к maintenance DB (postgres).

    Использует psycopg2 (psycopg2-binary). Если модуля нет — функция тихо выходит.
    """
    try:
        import psycopg2 
        import psycopg2.extensions 
    except Exception:
        return

    url = os.getenv("DATABASE_URL", DATABASE_URL)
    parsed = urllib.parse.urlparse(url)
    dbname = parsed.path.lstrip('/') if parsed.path else ''
    if not dbname:
        return

    user = parsed.username or 'postgres'
    password = parsed.password or ''
    host = parsed.hostname or 'localhost'
    port = parsed.port or 5432

    try:
        conn = psycopg2.connect(dbname='postgres', user=user, password=password, host=host, port=port)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
        exists = cur.fetchone() is not None
        if not exists:
            cur.execute("CREATE DATABASE %s", (psycopg2.extensions.AsIs(dbname),))
        cur.close()
        conn.close()
    except Exception:
        # Не ломаем стартап приложения — в логах будет явное сообщение об ошибке подключения
        return
