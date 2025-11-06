from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_session
from shared.auth_utils import (
    get_password_hash, verify_password, create_access_token, decode_access_token
)
from shared.schemas import UserCreate, UserOut, UserLogin
from .models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Небольшой in-memory fallback для разработки без Postgres.
# Формат: { email: {"password_hash": ..., "full_name": ...} }
USERS_FALLBACK: dict = {}


# Регистрация пользователя
@router.post("/register", response_model=UserOut, status_code=201)
async def register_user(payload: UserCreate, session: AsyncSession = Depends(get_session)):
    # Enforce a minimum password length (at least 8 characters).
    if not isinstance(payload.password, str) or len(payload.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long."
        )

    # Пытаемся сохранить в БД; если БД недоступна, используем in-memory fallback.
    try:
        result = await session.execute(select(User).where(User.email == payload.email))
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким email уже существует"
            )

        # Compute password hash; if hashing backend is unavailable, return 503
        try:
            password_hash = get_password_hash(payload.password)
        except Exception:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                                detail="Сервис аутентификации временно недоступен")

        user = User(
            email=payload.email,
            password_hash=password_hash,
            full_name=payload.full_name
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user
    except Exception:
        # fallback: store in-memory for development without DB
        if payload.email in USERS_FALLBACK:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пользователь с таким email уже существует (fallback)")
        try:
            USERS_FALLBACK[payload.email] = {
                "password_hash": get_password_hash(payload.password),
                "full_name": payload.full_name
            }
        except Exception:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                                detail="Сервис аутентификации временно недоступен (fallback)")
        return {"email": payload.email, "full_name": payload.full_name}


# Логин (через JSON)
@router.post("/login")
async def login_user(payload: UserLogin, session: AsyncSession = Depends(get_session)):
    try:
        result = await session.execute(select(User).where(User.email == payload.email))
        user = result.scalar_one_or_none()

        if user and verify_password(payload.password, user.password_hash):
            access_token = create_access_token({"sub": user.email})
            return {"access_token": access_token, "token_type": "bearer"}
    except Exception:
        user = None

    # Фallback: проверяем in-memory хранилище
    fallback = USERS_FALLBACK.get(payload.email)
    if fallback and verify_password(payload.password, fallback["password_hash"]):
        access_token = create_access_token({"sub": payload.email})
        return {"access_token": access_token, "token_type": "bearer"}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Неверный email или пароль"
    )


from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme), session: AsyncSession = Depends(get_session)):
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Невалидный токен")

    email: str = payload.get("sub")
    if email is None:
        raise HTTPException(status_code=401, detail="Невалидный токен")

    try:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user is not None:
            return user
    except Exception:
        pass

    # fallback check
    fallback = USERS_FALLBACK.get(email)
    if fallback:
        # Возвращаем минимальный объект, совместимый с ожиданиями
        return User(email=email, full_name=fallback.get("full_name"), password_hash=fallback.get("password_hash"))

    raise HTTPException(status_code=401, detail="Пользователь не найден")


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
