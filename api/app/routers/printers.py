"""`/api/printers` — printerlar reyestri: nom qo'yish, birlashtirish, qayta qurish.

Reyestr chop etish tarixidan avtomatik to'ladi: har bir yangi MAC, IP yoki
drayver nomi uchun qurilma yaratiladi. Admin ikki ishni qiladi — qurilmaga
qulay nom qo'yadi va bir xil printerga tegishli qatorlarni birlashtiradi.
"""

from fastapi import APIRouter, Depends, Security
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import USER_UNAUTHORIZED_RESPONSE, require_user
from app.db import get_session
from app.models import PrinterAlias, PrinterDevice
from app.schemas import PrinterAliasOut, PrinterMergeIn, PrinterNameIn, PrinterOut
from app.services import printers

router = APIRouter(tags=["printers"], dependencies=[Security(require_user)])


def _to_out(device: PrinterDevice, aliases: list[PrinterAlias]) -> PrinterOut:
    """Ko'rsatish uchun nom: admin nomi -> so'nggi drayver nomi -> birinchi nishon."""
    fallback = aliases[0].value if aliases else f"#{device.id}"
    return PrinterOut(
        id=device.id,
        name=device.name,
        display_name=device.name or device.last_driver_name or fallback,
        last_ip=device.last_ip,
        last_driver_name=device.last_driver_name,
        last_seen=device.last_seen,
        first_seen=device.first_seen,
        # Nishonlar ishonchlilik tartibida: mac -> ip -> nom.
        aliases=[
            PrinterAliasOut.model_validate(a)
            for a in sorted(aliases, key=lambda a: (printers.KINDS.index(a.kind), a.value))
        ],
    )


@router.get(
    "/api/printers",
    response_model=list[PrinterOut],
    summary="Printerlar reyestri",
    response_description="Eng so'nggi ko'rilganidan boshlab tartiblangan printerlar",
    responses=USER_UNAUTHORIZED_RESPONSE,
)
async def list_printers(session: AsyncSession = Depends(get_session)) -> list[PrinterOut]:
    rows = await printers.list_devices(session)
    return [_to_out(device, aliases) for device, aliases in rows]


@router.put(
    "/api/printers/{device_id}",
    response_model=PrinterOut,
    summary="Printerga qulay nom qo'yish",
    response_description="Yangilangan printer",
    responses=USER_UNAUTHORIZED_RESPONSE,
)
async def set_printer_name(
    device_id: int,
    payload: PrinterNameIn,
    session: AsyncSession = Depends(get_session),
) -> PrinterOut:
    """Nom butun tizimda ishlatiladi: jurnalda ham, statistikada ham.

    Bo'sh nom (`""`) nomni tozalaydi — shunda so'nggi drayver nomi ko'rsatiladi.
    """
    device = await printers.rename(session, device_id, payload.name)
    rows = {d.id: al for d, al in await printers.list_devices(session)}
    return _to_out(device, rows.get(device.id, []))


@router.post(
    "/api/printers/{device_id}/merge",
    response_model=PrinterOut,
    summary="Ikki printerni birlashtirish",
    response_description="Birlashtirilgan printer va uning barcha nishonlari",
    responses=USER_UNAUTHORIZED_RESPONSE,
)
async def merge_printers(
    device_id: int,
    payload: PrinterMergeIn,
    session: AsyncSession = Depends(get_session),
) -> PrinterOut:
    """Bitta jismoniy printer turli nomlar bilan yozilgan bo'lsa shu amal birlashtiradi.

    `sourceId` ning barcha nishonlari shu printerga ko'chadi va o'zi o'chiriladi.
    Tarix ham, statistika ham shu zahoti bitta nom ostida ko'rinadi — chunki
    chop etish yozuvlari nishonlar orqali bog'lanadi, nusxalanmaydi.
    """
    device = await printers.merge(session, device_id, payload.source_id)
    rows = {d.id: al for d, al in await printers.list_devices(session)}
    return _to_out(device, rows.get(device.id, []))


@router.post(
    "/api/printers/reconcile",
    summary="Reyestrni chop etish tarixidan qayta qurish",
    response_description="Yaratilgan va jami qurilmalar soni",
    responses=USER_UNAUTHORIZED_RESPONSE,
)
async def reconcile_printers(session: AsyncSession = Depends(get_session)) -> dict[str, int]:
    """Tarixdagi har bir MAC, IP va nom uchun reyestrda qator borligini ta'minlaydi.

    Idempotent — qayta ishga tushirish xavfsiz, faqat yangi nishonlar qo'shiladi.
    Mavjud nomlar va birlashtirishlar saqlanadi.
    """
    return await printers.reconcile(session)
