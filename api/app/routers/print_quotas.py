"""`POST /api/print-quotas` — agent bilan kvota almashinuvi."""

from fastapi import APIRouter, Depends, Security
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import API_KEY_UNAUTHORIZED_RESPONSE, require_api_key
from app.db import get_session
from app.schemas import QuotaSyncIn, QuotaSyncOut
from app.services import quota_sync

router = APIRouter(tags=["quotas"])


@router.post(
    "/api/print-quotas",
    response_model=QuotaSyncOut,
    dependencies=[Security(require_api_key)],
    summary="Agent sarfni bildiradi va joriy limitlarni oladi",
    response_description="Joriy davr identifikatori, standart limit va foydalanuvchi limitlari",
    responses=API_KEY_UNAUTHORIZED_RESPONSE,
)
async def sync_print_quotas(
    payload: QuotaSyncIn,
    session: AsyncSession = Depends(get_session),
) -> QuotaSyncOut:
    """Ish stantsiyasidagi agent har necha daqiqada shu endpointga murojaat qiladi.

    So'rovda — shu mashinada hisoblangan varaqlar; javobda — server bilgan
    haqiqiy sarf va qo'llanishi kerak bo'lgan limitlar. Agent javobni keshlaydi
    va chop etish qarorini mahalliy (tarmoqqa bog'liq bo'lmagan) holda qabul
    qiladi, shuning uchun bu endpointning ishlamay qolishi chop etishni
    to'xtatmaydi — agent eski keshlangan limitlar bilan davom etadi.

    **Diqqat**: javobdagi `periodKey` o'zgarishi agentdagi hisoblagichlarni nolga
    tushiradi. Format `app.periods.period_key` orqali barqaror hosil qilinadi,
    shuning uchun bir xil davr uchun har doim bir xil satr qaytadi.
    """
    return await quota_sync.sync_quotas(session, payload)
