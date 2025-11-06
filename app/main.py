# app/main.py
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
import uvicorn
from . import shop
from . import auth, pages
from .database import engine, Base
from . import shop, cart, orders
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
app = FastAPI(
    title="VAG FORCE",
    description="🚀 API для регистрации, логина и управления автомобилями",
    version="1.0.0",
)

# ✅ Абсолютный путь к /static
BASE_DIR = Path(__file__).resolve().parent.parent  # .../vag-force
STATIC_DIR = BASE_DIR / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ✅ CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
templates = Jinja2Templates(directory="templates")

# ✅ Роутеры
app.include_router(auth.router)
app.include_router(pages.router)
app.include_router(shop.router)
app.include_router(cart.router)
app.include_router(orders.router)

@app.get("/")
async def root():
    return {"message": "🚀 API работает!"}

@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# ✅ OpenAPI с OAuth2 (если нужно видеть Authorize в /docs)
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schema.setdefault("components", {}).setdefault("securitySchemes", {})
    schema["components"]["securitySchemes"]["OAuth2PasswordBearer"] = {
        "type": "oauth2",
        "flows": {"password": {"tokenUrl": "/api/auth/login", "scopes": {}}}
    }
    schema["security"] = [{"OAuth2PasswordBearer": []}]
    app.openapi_schema = schema
    return app.openapi_schema

app.openapi = custom_openapi

@app.get("/")
async def root():
    return {"message": "VAG FORCE API работает"}

@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)


# 📍 Маршрут магазина
@app.get("/shop", response_class=HTMLResponse)
async def shop_page(request: Request):
    return templates.TemplateResponse("shop.html", {"request": request})

# 📍 Маршрут корзины
@app.get("/cart", response_class=HTMLResponse)
async def cart_page(request: Request):
    return templates.TemplateResponse("cart.html", {"request": request})