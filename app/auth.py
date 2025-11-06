from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from passlib.context import CryptContext
from passlib.exc import UnknownHashError
from jose import jwt, JWTError
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .database import get_session
from .models import User
from .schemas import UserCreate, UserOut, UserLogin

router = APIRouter(prefix="/api/auth", tags=["auth"])

# 🔑 Настройки шифрования и JWT
# Prefer Argon2 when available, fall back to bcrypt. This avoids relying solely on
# a possibly-misinstalled bcrypt binary in dev containers.
pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")
SECRET_KEY = "supersecretkey"  # ⚠️ Вынеси в .env позже
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# 🔐 Утилиты
def get_password_hash(password: str) -> str:
    # hashing can fail if the native backend is missing or broken inside the container;
    # raise a clear exception so the caller can return a friendly HTTP error instead
    try:
        return pwd_context.hash(password)
    except Exception:
        # re-raise so callers can map to HTTP 503 / friendly message
        raise

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except UnknownHashError:
        # Hash stored in DB is not recognizable by our pwd_context (possible corruption
        # or different scheme). Treat as authentication failure rather than a 500.
        return False
    except Exception:
        # Any other passlib error -> treat as verification failure
        return False

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# ✅ Регистрация пользователя
@router.post("/register", response_model=UserOut, status_code=201)
async def register_user(payload: UserCreate, session: AsyncSession = Depends(get_session)):
    try:
        result = await session.execute(select(User).where(User.email == payload.email))
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким email уже существует"
            )

        try:
            password_hash = get_password_hash(payload.password)
        except Exception:
            # Hashing backend not available (bcrypt native lib missing or similar)
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
    except IntegrityError:
        # Unique constraint or similar
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пользователь с таким email уже существует (DB)")
    except SQLAlchemyError:
        # DB is unavailable or other SQL error
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Служба базы данных временно недоступна, попробуйте позже")
    except HTTPException:
        # re-raise HTTP errors we intentionally threw above
        raise
    except Exception:
        # Generic fallback - return friendly message instead of raw 500 stack
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при регистрации. Попробуйте позже.")

# ✅ Логин (через JSON)
@router.post("/login")
async def login_user(payload: UserLogin, session: AsyncSession = Depends(get_session), response: Response = None):
    result = await session.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль"
        )

    access_token = create_access_token({"sub": user.email})
    # Set a non-HttpOnly cookie for demo convenience so server-side templates can read it.
    # In production, prefer HttpOnly and secure cookies and server-side session handling.
    try:
        # FastAPI will inject a Response if declared; ensure we set cookie when possible
        if response is not None:
            response.set_cookie("vf_token", access_token, max_age=ACCESS_TOKEN_EXPIRE_MINUTES*60, path='/', httponly=False)
    except Exception:
        pass
    return {"access_token": access_token, "token_type": "bearer"}

# ✅ Проверка токена
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session)
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Невалидный токен")
    except JWTError:
        raise HTTPException(status_code=401, detail="Невалидный токен")

    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="Пользователь не найден")
    return user


async def get_user_from_request(request, session: AsyncSession):
    """Попытаться получить пользователя по токену из заголовка Authorization или из cookie vf_token.
    Возвращает объект User или None.
    """
    token = None
    auth = request.headers.get('Authorization')
    if auth and auth.lower().startswith('bearer '):
        token = auth.split(None, 1)[1].strip()
    if not token:
        token = request.cookies.get('vf_token')
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get('sub')
        if not email:
            return None
    except JWTError:
        return None
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    return user

@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
