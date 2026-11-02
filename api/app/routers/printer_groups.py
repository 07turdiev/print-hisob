"""`/api/printer-groups` — xodimlar guruhlari va printer ruxsatlari.

Guruh uchta siyosatdan birini oladi: barcha printerlar, faqat belgilanganlar,
yoki umuman chiqarmaslik. Bir xodim bir vaqtda faqat bitta guruhda bo'ladi;
guruhga kirmagan xodim cheklanmaydi.
"""

from fastapi import APIRouter, Depends, Security, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import USER_UNAUTHORIZED_RESPONSE, require_user
from app.db import get_session
from app.deps import period_params
from app.periods import Period
from app.schemas import (
    PolicyViolationOut,
    PrinterGroupIn,
    PrinterGroupOut,
    PrinterGroupPatchIn,
)
from app.services import printer_groups

router = APIRouter(tags=["printer-groups"], dependencies=[Security(require_user)])


def _to_out(row: printer_groups.GroupRow) -> PrinterGroupOut:
    return PrinterGroupOut(
        id=row.group.id,
        name=row.group.name,
        policy=row.group.policy,
        device_ids=row.device_ids,
        logins=row.logins,
    )


async def _one(session: AsyncSession, group_id: int) -> PrinterGroupOut:
    """Yangilangan guruhni to'liq (qurilmalari va a'zolari bilan) qaytaradi."""
    rows = {r.group.id: r for r in await printer_groups.list_groups(session)}
    return _to_out(rows[group_id])


@router.get(
    "/api/printer-groups",
    response_model=list[PrinterGroupOut],
    summary="Guruhlar ro'yxati",
    response_description="Nom bo'yicha tartiblangan guruhlar",
    responses=USER_UNAUTHORIZED_RESPONSE,
)
async def list_groups(session: AsyncSession = Depends(get_session)) -> list[PrinterGroupOut]:
    return [_to_out(row) for row in await printer_groups.list_groups(session)]


@router.get(
    "/api/printer-groups/violations",
    response_model=list[PolicyViolationOut],
    summary="Ruxsat etilmagan printerdan chiqarishlar",
    response_description="Sarf bo'yicha kamayish tartibida",
    responses=USER_UNAUTHORIZED_RESPONSE,
)
async def list_violations(
    period: Period = Depends(period_params),
    session: AsyncSession = Depends(get_session),
) -> list[PolicyViolationOut]:
    """Guruh siyosatini buzib chiqarilgan qog'oz.

    Agent hali `allowedPrinters` ni bilmagani uchun "faqat belgilangan"
    siyosati jismonan to'smaydi — shuning uchun bu hisobot hozircha yagona
    nazorat vositasi. Agent yangilangandan keyin ham kerak bo'ladi: eski
    versiyada qolgan mashinalarni aniqlab beradi.
    """
    rows = await printer_groups.violations(session, period.start, period.end)
    return [
        PolicyViolationOut(
            login=r.login,
            full_name=r.full_name,
            department=r.department,
            group_name=r.group_name,
            policy=r.policy,
            device_id=r.device_id,
            printer_name=r.printer_name,
            pages=r.pages,
            jobs=r.jobs,
            last_at=r.last_at,
        )
        for r in rows
    ]


@router.post(
    "/api/printer-groups",
    response_model=PrinterGroupOut,
    status_code=status.HTTP_201_CREATED,
    summary="Yangi guruh",
    response_description="Yaratilgan guruh",
    responses=USER_UNAUTHORIZED_RESPONSE,
)
async def create_group(
    payload: PrinterGroupIn,
    session: AsyncSession = Depends(get_session),
) -> PrinterGroupOut:
    group = await printer_groups.create_group(
        session, name=payload.name, policy=payload.policy
    )
    return PrinterGroupOut(id=group.id, name=group.name, policy=group.policy)


@router.put(
    "/api/printer-groups/{group_id}",
    response_model=PrinterGroupOut,
    summary="Guruhni o'zgartirish",
    response_description="Yangilangan guruh",
    responses=USER_UNAUTHORIZED_RESPONSE,
)
async def update_group(
    group_id: int,
    payload: PrinterGroupPatchIn,
    session: AsyncSession = Depends(get_session),
) -> PrinterGroupOut:
    """Qisman yangilash: faqat yuborilgan maydonlar o'zgaradi.

    `deviceIds` yoki `logins` yuborilsa ro'yxat butunlay almashtiriladi. Maydon
    umuman yuborilmasa tegilmaydi — shuning uchun "yuborilgan/yuborilmagan"
    farqi muhim.
    """
    sent = payload.model_fields_set
    await printer_groups.update_group(
        session,
        group_id,
        name=payload.name if "name" in sent else None,
        policy=payload.policy if "policy" in sent else None,
        device_ids=payload.device_ids if "device_ids" in sent else None,
        logins=payload.logins if "logins" in sent else None,
    )
    return await _one(session, group_id)


@router.delete(
    "/api/printer-groups/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Guruhni o'chirish",
    responses=USER_UNAUTHORIZED_RESPONSE,
)
async def delete_group(
    group_id: int,
    session: AsyncSession = Depends(get_session),
) -> None:
    """A'zolar guruhsiz qoladi, ya'ni cheklovsiz chop etadi — bu ataylab."""
    await printer_groups.delete_group(session, group_id)
