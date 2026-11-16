"""`/api/portal/v1` — ichki xizmatlar portali uchun xodim kabineti.

Portal serveri chaqiradi (`X-Portal-Key`), brauzer emas. Batafsil:
`docs/PORTAL-API.uz.md`.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, Security
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import PORTAL_UNAUTHORIZED_RESPONSE, require_portal_key
from app.db import get_session
from app.periods import Period, PeriodType, current_period, period_bounds
from app.schemas import (
    PortalDepartmentEmployeesOut,
    PortalDepartmentsOut,
    PortalHistoryItemOut,
    PortalJobOut,
    PortalPeriodsOut,
    PortalPrintingOut,
)
from app.services import portal
from app.services.quota_sync import agent_period_type

router = APIRouter(
    prefix="/api/portal/v1",
    tags=["portal"],
    dependencies=[Security(require_portal_key)],
)

_NOT_FOUND = {404: {"description": "Bunday xodim AD'da ham, chop etish tarixida ham yo'q"}}
_DEPARTMENT_NOT_FOUND = {404: {"description": "Bunday bo'lim AD'da yo'q"}}

LoginPath = Path(
    min_length=1,
    max_length=255,
    description="Xodim logini, masalan `e.turdiyev`. `MADANIYAT\\e.turdiyev` ham qabul qilinadi",
)


async def portal_period(
    period_type: PeriodType | None = Query(
        default=None,
        description="`quarter` yoki `month`. Berilmasa agentlar hisoblaydigan davr (hozir chorak)",
    ),
    year: int | None = Query(default=None, ge=2000, le=2100, description="Yil"),
    period_no: int | None = Query(
        default=None, description="Chorak uchun 1..4, oy uchun 1..12. Berilmasa joriy davr"
    ),
) -> Period:
    """Davr ixtiyoriy: berilmasa joriy davr olinadi, kabinet odatda shuni ko'rsatadi."""
    kind = period_type or agent_period_type()
    if year is None and period_no is None:
        return current_period(kind)
    if year is None or period_no is None:
        raise HTTPException(status_code=422, detail="`year` va `period_no` birga beriladi")
    try:
        start, end = period_bounds(kind, year, period_no)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return Period(period_type=kind, year=year, period_no=period_no, start=start, end=end)


@router.get(
    "/employees/{login}/printing",
    response_model=PortalPrintingOut,
    summary="Xodimning normasi, printer ruxsati va sarfi",
    responses={**PORTAL_UNAUTHORIZED_RESPONSE, **_NOT_FOUND},
)
async def employee_printing(
    login: str = LoginPath,
    period: Period = Depends(portal_period),
    session: AsyncSession = Depends(get_session),
) -> PortalPrintingOut:
    """Kabinetdagi "Printer" bo'limi uchun bitta so'rov.

    Raqamlar dashboard bilan bir xil. Norma chop etishni to'xtatmaydi: u faqat
    ko'rsatkich. Chop eta olish-olmasligi `access.canPrint` da.
    """
    return await portal.printing(session, login, period)


@router.get(
    "/employees/{login}/jobs",
    response_model=list[PortalJobOut],
    summary="Xodimning chop etishlari",
    response_description="Eng yangisidan boshlab. Jami soni `X-Total-Count` sarlavhasida",
    responses={**PORTAL_UNAUTHORIZED_RESPONSE, **_NOT_FOUND},
)
async def employee_jobs(
    response: Response,
    login: str = LoginPath,
    since: datetime | None = Query(default=None, description="Shu vaqtdan boshlab (ISO-8601)"),
    until: datetime | None = Query(default=None, description="Shu vaqtgacha, chegara kirmaydi"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[PortalJobOut]:
    """Faqat xodimning o'z ishlari. Normaga kirmaydiganlari ham ko'rinadi (`counted: false`)."""
    rows, total = await portal.jobs(
        session, login, since=since, until=until, limit=limit, offset=offset
    )
    response.headers["X-Total-Count"] = str(total)
    return rows


@router.get(
    "/employees/{login}/history",
    response_model=list[PortalHistoryItemOut],
    summary="Xodimning so'nggi davrlardagi normasi va sarfi",
    response_description="Joriy davr va undan oldingilari, eng yangisi birinchi",
    responses={**PORTAL_UNAUTHORIZED_RESPONSE, **_NOT_FOUND},
)
async def employee_history(
    login: str = LoginPath,
    period_type: PeriodType | None = Query(
        default=None, description="`quarter` yoki `month`. Berilmasa agentlar hisoblaydigan davr"
    ),
    count: int = Query(default=4, ge=1, le=12, description="Nechta davr, joriy davr bilan birga"),
    session: AsyncSession = Depends(get_session),
) -> list[PortalHistoryItemOut]:
    """Har bir davr raqamlari shu davr uchun `/printing` dagi `quota` bilan bir xil.

    Biriktirish hozirgi holat bo'yicha barcha davrlarga qo'llanadi.
    """
    return await portal.history(session, login, period_type or agent_period_type(), count)


@router.get(
    "/periods",
    response_model=PortalPeriodsOut,
    summary="Davr tanlash uchun chegaralar",
    responses=PORTAL_UNAUTHORIZED_RESPONSE,
)
async def available_periods(session: AsyncSession = Depends(get_session)) -> PortalPeriodsOut:
    """Joriy chorak va oy hamda chop etish tarixidagi birinchi chorak va oy."""
    return await portal.periods(session)


@router.get(
    "/departments",
    response_model=PortalDepartmentsOut,
    summary="Bo'limlar kesimi (rahbariyat uchun)",
    responses=PORTAL_UNAUTHORIZED_RESPONSE,
)
async def departments_summary(
    period: Period = Depends(portal_period),
    session: AsyncSession = Depends(get_session),
) -> PortalDepartmentsOut:
    """Faqat yig'ma raqamlar. Kimga ko'rsatishni portal hal qiladi.

    Oxirgi qator (`department: null`) AD'da yo'q yoki bo'limi bo'sh loginlarning
    sarfi. Barcha qatorlar yig'indisi davrning umumiy sarfiga teng.
    """
    return await portal.departments(session, period)


@router.get(
    "/departments/{department:path}/employees",
    response_model=PortalDepartmentEmployeesOut,
    summary="Bo'lim xodimlarining normasi va sarfi (rahbariyat uchun)",
    responses={**PORTAL_UNAUTHORIZED_RESPONSE, **_DEPARTMENT_NOT_FOUND},
)
async def department_employees(
    department: str = Path(
        min_length=1,
        max_length=255,
        description="Bo'lim nomi `/departments` javobidagi `department` dan, URL uchun kodlangan",
    ),
    period: Period = Depends(portal_period),
    session: AsyncSession = Depends(get_session),
) -> PortalDepartmentEmployeesOut:
    """Hujjat, kompyuter va printer ma'lumoti qaytmaydi, faqat xodim raqamlari."""
    return await portal.department_employees(session, department, period)
