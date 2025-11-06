
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from .database import get_session
from .auth import get_user_from_request
import os
import httpx
import asyncio

templates = Jinja2Templates(directory="templates")
router = APIRouter()


@router.get("/__routes")
async def _list_routes(request: Request):
    # debug endpoint: вернёт список всех путей, зарегистрированных в приложении
    routes = []
    for r in request.app.routes:
        try:
            routes.append({"path": getattr(r, 'path', str(r)), "name": getattr(r, 'name', None)})
        except Exception:
            continue
    return {"routes": routes}

@router.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

# Страница оформления заказа
@router.get("/order", response_class=HTMLResponse)
async def order_page(request: Request):
    return templates.TemplateResponse("order.html", {"request": request})


@router.get("/checkout", response_class=HTMLResponse)
async def checkout_page(request: Request):
    return templates.TemplateResponse("checkout.html", {"request": request})


@router.get("/order-confirmation", response_class=HTMLResponse)
async def order_confirmation_page(request: Request):
    return templates.TemplateResponse("order_confirmation.html", {"request": request})


# Личный кабинет
@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, session = Depends(get_session)):
    # Resolve current user from cookie or Authorization header using a request-scoped
    # DB session injected by FastAPI. This avoids manually opening/closing the
    # async session which could lead to overlapping operations on the same
    # asyncpg connection ("another operation is in progress").
    user = await get_user_from_request(request, session)

    # attempt to fetch recent orders for this user from orders-service
    orders = None
    # When running under Docker Compose the orders service hostname is 'orders-service'.
    # Use that as the default so server-side fetch works from inside containers.
    ORDERS_URL = os.getenv("ORDERS_URL", "http://orders-service:8004")
    if user is not None:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{ORDERS_URL}/api/orders/user/{user.id}")
                if resp.status_code == 200:
                    orders = resp.json()
                else:
                    # try one quick retry in case orders-service is still starting
                    print(f"pages.profile_page: orders-service returned {resp.status_code} for user {user.id}, retrying once")
                    await asyncio.sleep(0.25)
                    resp2 = await client.get(f"{ORDERS_URL}/api/orders/user/{user.id}")
                    if resp2.status_code == 200:
                        orders = resp2.json()
                    else:
                        print(f"pages.profile_page: orders-service retry returned {resp2.status_code} for user {user.id}")
        except Exception:
            # best-effort: leave orders as None (client-side can still try)
            import traceback
            print(f"pages.profile_page: error fetching orders for user {getattr(user,'id',None)}")
            traceback.print_exc()
            orders = None

    ctx = {"request": request, "user": user, "orders": orders}
    return templates.TemplateResponse("profile.html", ctx)

