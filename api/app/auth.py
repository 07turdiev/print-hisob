"""Dashboard foydalanuvchisi uchun JWT autentifikatsiya.

E'tibor bering: bu **ikkinchi**, alohida autentifikatsiya mexanizmi. Ish
stantsiyalaridagi agentlar (.exe) hamon `X-API-Key` bilan ishlaydi
(`app.main.require_api_key`) — bu modul ularga tegishli emas.

Dashboard foydalanuvchisi login/parol bilan `/api/auth/login`'ga murojaat qiladi,
javobda JWT bearer token oladi va keyingi so'rovlarda `Authorization: Bearer <token>`
sarlavhasini yuboradi. `require_user` shu tokenni tekshiradi.
"""

import hmac
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

JWT_ALGORITHM = "HS256"

bearer_scheme = HTTPBearer(
    auto_error=False,
    description="`/api/auth/login`dan olingan JWT token (`Authorization: Bearer <token>`).",
)

# ---------------------------------------------------------------------------
# Mashina agentlari uchun (.exe, AD skripti) — X-API-Key
# ---------------------------------------------------------------------------

api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
    description="Server `API_KEY` bilan ishga tushirilgandagina talab qilinadi.",
)

# HTTP sarlavhalari registrga sezgir emas, shuning uchun agent yuboradigan
# `X-Api-Key` ham shu tekshiruvdan o'tadi (sinovdan o'tkazilgan).

API_KEY_UNAUTHORIZED_RESPONSE = {
    status.HTTP_401_UNAUTHORIZED: {"description": "Noto'g'ri yoki yo'q API kalit"}
}

USER_UNAUTHORIZED_RESPONSE = {
    status.HTTP_401_UNAUTHORIZED: {"description": "Token yo'q, yaroqsiz yoki muddati tugagan"}
}


async def require_api_key(key: str | None = Security(api_key_header)) -> None:
    """`API_KEY` .env'da o'rnatilgan bo'lsagina tekshiradi.

    Bu **agentlar** (.exe, AD sinxronizatsiya skripti) uchun — dashboard
    foydalanuvchilari uchun emas; ular `require_user` (JWT bearer) bilan o'tadi.
    """
    if not settings.api_key:
        return
    if key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Noto'g'ri yoki yo'q API kalit"
        )


def verify_credentials(username: str, password: str) -> bool:
    """Login/parolni `.env`dagi qiymatlar bilan doimiy vaqtda (constant-time) solishtiradi."""
    username_ok = hmac.compare_digest(username, settings.auth_username)
    password_ok = hmac.compare_digest(password, settings.auth_password)
    return username_ok and password_ok


def create_access_token(username: str) -> tuple[str, int]:
    """Berilgan foydalanuvchi uchun JWT token yaratadi.

    `JWT_SECRET` bo'sh bo'lsa xavfsizlik uchun token berilmaydi (fail-closed).
    Qaytaradi: `(token, expires_in_seconds)`.
    """
    if not settings.jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server konfiguratsiyasi to'liq emas: JWT_SECRET o'rnatilmagan",
        )

    now = datetime.now(timezone.utc)
    expires_in = settings.jwt_expire_minutes * 60
    payload = {
        "sub": username,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)
    return token, expires_in


async def require_user(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> str:
    """Dashboard endpointlari uchun: `Authorization: Bearer <token>` tekshiradi.

    Token yo'q, imzosi noto'g'ri yoki muddati tugagan bo'lsa 401 qaytaradi.
    Muvaffaqiyatli bo'lsa tokendagi foydalanuvchi nomini (`sub`) qaytaradi.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token berilmagan (Authorization: Bearer <token> kerak)",
        )
    if not settings.jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server konfiguratsiyasi to'liq emas: JWT_SECRET o'rnatilmagan",
        )
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token yaroqsiz yoki muddati tugagan",
        ) from exc
    return str(payload.get("sub", ""))
