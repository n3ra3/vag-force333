from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

from .routers import router as auth_router
from shared.database import engine, Base, ensure_database_exists
import asyncio

app = FastAPI(title="auth-service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.on_event("startup")
async def on_startup():
    # Ensure the database exists (creates DB if missing) — run in thread to avoid blocking.
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, ensure_database_exists)
    except Exception:
        # Ignore — if creation fails, metadata.create_all will still attempt to connect and raise a clear error.
        pass

    # Создаём таблицы (в development). В production используйте миграции (alembic).
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=True)


# Добавим простую настройку OpenAPI, чтобы в /docs появился Authorize для Bearer JWT
from fastapi.openapi.utils import get_openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version="1.0.0",
        description="Auth service API",
        routes=app.routes,
    )
    schema.setdefault("components", {}).setdefault("securitySchemes", {})
    schema["components"]["securitySchemes"]["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT"
    }
    schema["security"] = [{"BearerAuth": []}]
    app.openapi_schema = schema
    return app.openapi_schema

app.openapi = custom_openapi
