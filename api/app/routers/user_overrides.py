"""`/api/user-overrides` — chop etishni bloklash va xodimni xodimga biriktirish."""

from fastapi import APIRouter, Depends, Security
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import USER_UNAUTHORIZED_RESPONSE, require_user
from app.db import get_session
from app.schemas import UserOverrideIn, UserOverrideOut
from app.services import user_overrides

router = APIRouter(tags=["user-overrides"])


@router.get(
    "/api/user-overrides",
    response_model=list[UserOverrideOut],
    dependencies=[Security(require_user)],
    summary="Bloklangan va biriktirilgan loginlar ro'yxati",
    responses=USER_UNAUTHORIZED_RESPONSE,
)
async def list_user_overrides(
    session: AsyncSession = Depends(get_session),
) -> list[UserOverrideOut]:
    """Faqat qo'lda belgilangan qatorlar qaytadi — tegilmagan xodimlar bu yerda yo'q."""
    rows = await user_overrides.list_overrides(session)
    return [UserOverrideOut.model_validate(row) for row in rows]


@router.put(
    "/api/user-overrides/{login}",
    response_model=UserOverrideOut,
    summary="Xodimni bloklash/blokdan chiqarish yoki boshqasiga biriktirish",
    response_description="Yangilangan sozlama",
    responses=USER_UNAUTHORIZED_RESPONSE,
)
async def set_user_override(
    login: str,
    payload: UserOverrideIn,
    session: AsyncSession = Depends(get_session),
    actor: str = Security(require_user),
) -> UserOverrideOut:
    """Qisman yangilash: faqat yuborilgan maydonlar o'zgaradi.

    * `{"blocked": true}` — chop etishni to'sadi (agentga `limit: 0` ketadi);
    * `{"blocked": false}` — ruxsat beradi;
    * `{"chargeToLogin": "a.karimov"}` — varaqlari Karimov hisobida ham ko'rsatiladi;
    * `{"chargeToLogin": null}` — biriktirishni bekor qiladi.

    Bloklash **biriktirilgan xodimga tarqalmaydi** — har bir login alohida
    boshqariladi, shunda "nega men bloklandim?" degan savol tug'ilmaydi.

    Agent javobni o'zi so'rab oladi (`POST /api/print-quotas`), shuning uchun
    o'zgarish `QuotaSyncIntervalMinutes` oralig'ida kuchga kiradi.
    """
    return await user_overrides.apply_override(session, login, payload, actor)
