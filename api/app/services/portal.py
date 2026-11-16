"""Ichki xizmatlar portali: xodim o'z normasi, printer ruxsati va sarfini ko'radi.

Portal serveri xodimni o'zi tanib oladi (AD orqali kirish) va bizga uning
loginini `X-Portal-Key` bilan yuboradi. Biz kim so'rayotganini tekshirmaymiz,
faqat kalitni. Shuning uchun portal faqat kirgan xodimning o'z loginini
yuborishi shart, aks holda bir xodim boshqasining ma'lumotini ko'rib qoladi.
Rahbariyat uchun bo'limlar kesimini kimga ko'rsatishni ham portal hal qiladi.

Raqamlar dashboard bilan bir manbadan olinadi (`app.services.reports`):
portaldagi "ishlatildi 356 varaq" dashboarddagi son bilan bir xil bo'ladi.

**Norma chop etishni to'smaydi.** U hisobot ko'rsatkichi, xolos. Chop etishni
faqat admin bloklashi to'xtatadi (`access.canPrint = false`), printer
cheklovi esa qaysi printerlardan chop etish mumkinligini belgilaydi.
"""

from collections import Counter
from collections.abc import Sequence
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.logins import login_key, normalize_login
from app.models import (
    Employee,
    EmployeeQuota,
    PrinterDevice,
    PrinterGroup,
    PrinterGroupMember,
    PrinterGroupPrinter,
    PrintJob,
    PrintUserOverride,
)
from app.periods import (
    Period,
    PeriodType,
    current_period,
    default_quota_for,
    is_current,
    period_at,
    period_label,
    recent_periods,
)
from app.rules import counted_job
from app.schemas import (
    EmployeeStatOut,
    PortalAccessOut,
    PortalDayOut,
    PortalDepartmentEmployeeOut,
    PortalDepartmentEmployeesOut,
    PortalDepartmentOut,
    PortalDepartmentsOut,
    PortalEmployeeOut,
    PortalEmployeeRefOut,
    PortalHistoryItemOut,
    PortalJobOut,
    PortalLinkedLoginOut,
    PortalPeriodChoiceOut,
    PortalPeriodOut,
    PortalPeriodsOut,
    PortalPrinterOut,
    PortalPrinterUsageOut,
    PortalPrintingOut,
    PortalQuotaOut,
)
from app.services import printer_groups, reports
from app.services import printers as printer_registry
from app.services.quota_sync import agent_period_type

# Bo'limi aniqlanmagan sarf qatorining nomi (`department: null`).
UNASSIGNED_DEPARTMENT_LABEL = "Bo'limi aniqlanmagan"

# ---------------------------------------------------------------------------
# Xodimni topish
# ---------------------------------------------------------------------------


async def _resolve(session: AsyncSession, login: str) -> tuple[str, Employee | None]:
    """Normallashtirilgan login va AD yozuvi.

    AD'da yo'q, lekin chop etish tarixida bor login ham qabul qilinadi (masalan
    AD'dan yaqinda o'chirilgan xodim). Ikkalasida ham yo'q bo'lsa 404.
    """
    key = normalize_login(login)
    if key:
        employee = (
            (await session.execute(select(Employee).where(login_key(Employee.login) == key)))
            .scalars()
            .first()
        )
        if employee is not None:
            return key, employee
        has_jobs = (
            await session.execute(
                select(PrintJob.id).where(login_key(PrintJob.user_name) == key).limit(1)
            )
        ).first()
        if has_jobs is not None:
            return key, None
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Xodim topilmadi")


def _status(employee: Employee | None) -> str:
    if employee is None:
        return "unknown"
    return "active" if employee.is_active else "inactive"


def _employee_out(key: str, employee: Employee | None) -> PortalEmployeeOut:
    if employee is None:
        return PortalEmployeeOut(
            login=key, full_name=None, department=None, position=None, status="unknown"
        )
    return PortalEmployeeOut(
        login=employee.login,
        full_name=employee.full_name,
        department=employee.department,
        position=employee.position,
        status=_status(employee),
    )


async def _employees_by_key(session: AsyncSession, logins: Sequence[str]) -> dict[str, Employee]:
    """AD yozuvlari normallashtirilgan login bo'yicha, bitta so'rovda."""
    keys = sorted({normalize_login(login) for login in logins if login})
    if not keys:
        return {}
    rows = (
        (await session.execute(select(Employee).where(login_key(Employee.login).in_(keys))))
        .scalars()
        .all()
    )
    return {normalize_login(e.login): e for e in rows}


def _period_out(period: Period) -> PortalPeriodOut:
    return PortalPeriodOut(
        period_type=period.period_type,
        year=period.year,
        period_no=period.period_no,
        label=f"{period.year}-yil, {period_label(period.period_type, period.period_no)}",
        start=period.start,
        end=period.end,
        is_current=is_current(period),
    )


def _percent(used: int, allocated: int | None) -> float | None:
    return round(used / allocated * 100, 1) if allocated else None


# ---------------------------------------------------------------------------
# Norma
# ---------------------------------------------------------------------------


async def _explicit_quotas(
    session: AsyncSession, key: str, periods: Sequence[Period]
) -> dict[tuple[int, int], int]:
    """Admin alohida belgilagan normalar: `{(yil, davr): varaq}`, bitta so'rovda."""
    if not periods:
        return {}
    rows = await session.execute(
        select(EmployeeQuota.year, EmployeeQuota.period_no, EmployeeQuota.allocated_pages).where(
            EmployeeQuota.login == key,
            EmployeeQuota.period_type == periods[0].period_type,
            tuple_(EmployeeQuota.year, EmployeeQuota.period_no).in_(
                [(p.year, p.period_no) for p in periods]
            ),
        )
    )
    return {(year, period_no): pages for year, period_no, pages in rows.all()}


def _quota_numbers(period: Period, row: EmployeeStatOut | None, explicit: int | None) -> dict:
    """Bitta davrning norma raqamlari. `/printing` ham, `/history` ham shundan oladi."""
    allocated = explicit if explicit is not None else default_quota_for(period.period_type)
    used = row.used if row else 0
    used_from_linked = row.used_from_linked if row else 0
    used_total = used + used_from_linked
    return {
        "allocated": allocated,
        "used": used,
        "used_from_linked": used_from_linked,
        "used_total": used_total,
        "remaining": allocated - used_total,
        "percent": _percent(used_total, allocated),
        "over_limit": used_total > allocated,
        "is_default": explicit is None,
    }


async def _quota(
    session: AsyncSession, key: str, period: Period, override: PrintUserOverride | None
) -> PortalQuotaOut:
    rows = await reports.employee_stats(session, period, login=key)
    explicit = await _explicit_quotas(session, key, [period])
    numbers = _quota_numbers(
        period, rows[0] if rows else None, explicit.get((period.year, period.period_no))
    )

    linked_logins = sorted(
        (
            await session.execute(
                select(PrintUserOverride.login).where(PrintUserOverride.charge_to_login == key)
            )
        )
        .scalars()
        .all()
    )
    charged_to = override.charge_to_login if override else None
    usage = await reports.usage_by_login(session, period, linked_logins)
    employees = await _employees_by_key(session, [*linked_logins, *([charged_to] if charged_to else [])])

    def ref(login: str) -> dict:
        employee = employees.get(login)
        return {
            "login": login,
            "full_name": employee.full_name if employee else None,
            "status": _status(employee),
        }

    return PortalQuotaOut(
        **numbers,
        allocated_source="default" if numbers["is_default"] else "explicit",
        linked_logins=linked_logins,
        charged_to=charged_to,
        linked=[
            PortalLinkedLoginOut(
                **ref(login), pages=usage.get(login, (0, 0))[0], jobs=usage.get(login, (0, 0))[1]
            )
            for login in linked_logins
        ],
        charged_to_employee=PortalEmployeeRefOut(**ref(charged_to)) if charged_to else None,
    )


async def history(
    session: AsyncSession, login: str, period_type: PeriodType, count: int
) -> list[PortalHistoryItemOut]:
    """Joriy davr va undan oldingilari, eng yangisi birinchi.

    So'rovlar soni `count` ga bog'liq emas: sarf bitta so'rovda
    (`reports.employee_stats_by_period`), normalar bitta so'rovda olinadi.
    """
    key, _ = await _resolve(session, login)
    periods = recent_periods(period_type, count)
    rows = await reports.employee_stats_by_period(session, periods, login=key)
    explicit = await _explicit_quotas(session, key, periods)
    return [
        PortalHistoryItemOut(
            period=_period_out(period),
            **_quota_numbers(
                period,
                period_rows[0] if period_rows else None,
                explicit.get((period.year, period.period_no)),
            ),
        )
        for period, period_rows in zip(periods, rows)
    ]


async def periods(session: AsyncSession) -> PortalPeriodsOut:
    """Davr tanlash ro'yxati chegaralari: joriy davr va tarixdagi birinchi davr."""
    first = (
        await session.execute(select(func.min(PrintJob.printed_at)).where(counted_job()))
    ).scalar()
    return PortalPeriodsOut(
        default_period_type=agent_period_type(),
        current=PortalPeriodChoiceOut(
            quarter=_period_out(current_period("quarter")),
            month=_period_out(current_period("month")),
        ),
        earliest=None
        if first is None
        else PortalPeriodChoiceOut(
            quarter=_period_out(period_at("quarter", first)),
            month=_period_out(period_at("month", first)),
        ),
    )


# ---------------------------------------------------------------------------
# Bo'limlar kesimi (rahbariyat uchun, faqat yig'ma raqamlar)
# ---------------------------------------------------------------------------


async def departments(session: AsyncSession, period: Period) -> PortalDepartmentsOut:
    """Bo'limlar va bo'limi aniqlanmagan sarf. Yig'indisi davrning umumiy sarfiga teng.

    `used` haqiqiy qog'oz: har bir ish chop etgan xodimning bo'limida bir marta
    sanaladi. `overLimitCount` esa xodim darajasida, `usedTotal > norma` bo'yicha.
    """
    rollup = await reports.department_rollup(session, period)
    stats = await reports.employee_stats(session, period)
    over_limit = Counter(row.department for row in stats if row.department and row.over_limit)
    unassigned_pages, unassigned_jobs = await reports.unassigned_usage(session, period)

    rows = [
        PortalDepartmentOut(
            department=d.name,
            name=d.name,
            employee_count=d.employee_count,
            allocated=d.total_allocated,
            used=d.pages,
            jobs=d.jobs,
            percent=_percent(d.pages, d.total_allocated),
            over_limit_count=over_limit.get(d.name, 0),
        )
        for d in rollup
    ]
    rows.append(
        PortalDepartmentOut(
            department=None,
            name=UNASSIGNED_DEPARTMENT_LABEL,
            employee_count=None,
            allocated=None,
            used=unassigned_pages,
            jobs=unassigned_jobs,
            percent=None,
            over_limit_count=None,
        )
    )
    return PortalDepartmentsOut(
        period=_period_out(period),
        departments=rows,
        total_used=sum(r.used for r in rows),
        total_jobs=sum(r.jobs for r in rows),
    )


async def department_employees(
    session: AsyncSession, department: str, period: Period
) -> PortalDepartmentEmployeesOut:
    """Bo'limning faol xodimlari va davrda chop etgan ketgan xodimlari.

    Ularning `used` yig'indisi `/departments` dagi shu bo'lim `used` iga teng.
    """
    members = (
        (await session.execute(select(Employee).where(Employee.department == department)))
        .scalars()
        .all()
    )
    if not members:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bo'lim topilmadi")

    stats = await reports.employee_stats(session, period, department)
    with_usage = {normalize_login(row.login) for row in stats}
    idle = [e for e in members if e.is_active and normalize_login(e.login) not in with_usage]
    idle_keys = [normalize_login(e.login) for e in idle]

    explicit: dict[str, int] = {}
    blocked: set[str] = set()
    if idle_keys:
        explicit = dict(
            (
                await session.execute(
                    select(EmployeeQuota.login, EmployeeQuota.allocated_pages).where(
                        EmployeeQuota.login.in_(idle_keys),
                        EmployeeQuota.period_type == period.period_type,
                        EmployeeQuota.year == period.year,
                        EmployeeQuota.period_no == period.period_no,
                    )
                )
            ).all()
        )
        blocked = set(
            (
                await session.execute(
                    select(PrintUserOverride.login).where(
                        PrintUserOverride.login.in_(idle_keys), PrintUserOverride.blocked.is_(True)
                    )
                )
            )
            .scalars()
            .all()
        )

    # Statistikadagi login chop etish yozuvidagi ko'rinishda (`MADANIYAT\Ali`),
    # ro'yxatda esa AD'dagi login ko'rsatiladi.
    member_login = {normalize_login(e.login): e.login for e in members}
    rows = [
        PortalDepartmentEmployeeOut(
            login=member_login.get(normalize_login(row.login), normalize_login(row.login)),
            full_name=row.full_name,
            status="active" if row.match_status == "active" else "inactive",
            allocated=row.allocated,
            used=row.used,
            used_from_linked=row.used_from_linked,
            used_total=row.used_total,
            percent=_percent(row.used_total, row.allocated),
            over_limit=row.over_limit,
            blocked=row.blocked,
        )
        for row in stats
    ]
    default_allocated = default_quota_for(period.period_type)
    for employee in idle:
        key = normalize_login(employee.login)
        allocated = explicit.get(key, default_allocated)
        rows.append(
            PortalDepartmentEmployeeOut(
                login=employee.login,
                full_name=employee.full_name,
                status="active",
                allocated=allocated,
                used=0,
                used_from_linked=0,
                used_total=0,
                percent=_percent(0, allocated),
                over_limit=0 > allocated,
                blocked=key in blocked,
            )
        )
    rows.sort(key=lambda r: (-r.used_total, (r.full_name or r.login).lower()))
    return PortalDepartmentEmployeesOut(
        period=_period_out(period), department=department, employees=rows
    )


# ---------------------------------------------------------------------------
# Printer ruxsati
# ---------------------------------------------------------------------------


async def _allowed_printers(
    session: AsyncSession, device_ids: set[int], public_ids: set[int]
) -> list[PortalPrinterOut]:
    if not device_ids:
        return []
    rows = (
        await session.execute(
            select(
                PrinterDevice.id,
                func.coalesce(PrinterDevice.name, PrinterDevice.last_driver_name).label("name"),
                PrinterDevice.last_ip,
            ).where(PrinterDevice.id.in_(sorted(device_ids)))
        )
    ).all()
    printers = [
        PortalPrinterOut(
            name=row.name or f"Printer #{row.id}",
            ip=row.last_ip if printer_registry.is_ip(row.last_ip) else None,
            common=row.id in public_ids,
        )
        for row in rows
    ]
    # Avval umumiy printerlar, keyin guruhga berilganlar.
    return sorted(printers, key=lambda p: (not p.common, p.name.lower()))


async def _access(
    session: AsyncSession, key: str, blocked: bool
) -> tuple[PortalAccessOut, set[int] | None]:
    """Xodimga hozir qaysi printerlar ruxsat etilgan.

    Qoida agentga yuboriladigan ro'yxat bilan bir xil (`quota_sync._allowed_for`):
    bloklangan xodim hech qayerdan chop eta olmaydi, `all` guruhi va o'chiq
    cheklov hammasini ochadi, `allowed` guruhi umumiy printerlarga o'z
    printerlarini qo'shadi. Ikkinchi qiymat: ruxsat etilgan qurilmalar,
    `None` esa "barcha printerlar" degani.
    """
    default = await printer_groups.default_access(session)
    public_ids = set(default.device_ids)
    group = (
        await session.execute(
            select(PrinterGroup.id, PrinterGroup.name, PrinterGroup.policy)
            .join(PrinterGroupMember, PrinterGroupMember.group_id == PrinterGroup.id)
            .where(PrinterGroupMember.login == key)
        )
    ).first()
    group_name = group.name if group else None

    if blocked:
        return (
            PortalAccessOut(can_print=False, mode="blocked", group_name=group_name, printers=[]),
            set(),
        )
    if group is not None and group.policy == printer_groups.ALL:
        return PortalAccessOut(can_print=True, mode="all", group_name=group_name, printers=[]), None

    if group is not None and group.policy == printer_groups.ALLOWED:
        group_ids = set(
            (
                await session.execute(
                    select(PrinterGroupPrinter.device_id).where(
                        PrinterGroupPrinter.group_id == group.id
                    )
                )
            )
            .scalars()
            .all()
        )
        allowed = public_ids | group_ids
        mode = "common_and_group"
    elif default.allowed_printers() == [printer_groups.ANY_PRINTER]:
        # Cheklov o'chiq (yoki umumiy printerlarning nishoni yo'q): hamma printer ochiq.
        return PortalAccessOut(can_print=True, mode="all", group_name=None, printers=[]), None
    else:
        allowed = public_ids
        mode = "common"

    return (
        PortalAccessOut(
            can_print=True,
            mode=mode,
            group_name=group_name,
            printers=await _allowed_printers(session, allowed, public_ids),
        ),
        allowed,
    )


# ---------------------------------------------------------------------------
# Sarf
# ---------------------------------------------------------------------------


async def _daily(session: AsyncSession, key: str, period: Period) -> list[PortalDayOut]:
    """Kunlik sarf. Kun chegarasi `/api/stats/timeseries` bilan bir xil, UTC bo'yicha."""
    bucket = func.date_trunc("day", PrintJob.printed_at, "UTC").label("bucket")
    stmt = (
        select(
            bucket,
            func.coalesce(func.sum(PrintJob.pages), 0).label("pages"),
            func.count().label("jobs"),
        )
        .where(
            PrintJob.printed_at >= period.start,
            PrintJob.printed_at < period.end,
            counted_job(),
            login_key(PrintJob.user_name) == key,
        )
        .group_by(bucket)
        .order_by(bucket)
    )
    return [
        PortalDayOut(date=row.bucket.date().isoformat(), pages=row.pages, jobs=row.jobs)
        for row in (await session.execute(stmt)).all()
    ]


async def printing(session: AsyncSession, login: str, period: Period) -> PortalPrintingOut:
    """Kabinet uchun to'liq javob: norma, ruxsat, ishlatilgan printerlar, kunlik sarf."""
    key, employee = await _resolve(session, login)
    override = (
        (await session.execute(select(PrintUserOverride).where(PrintUserOverride.login == key)))
        .scalars()
        .first()
    )
    blocked = bool(override and override.blocked)

    access, allowed_ids = await _access(session, key, blocked)
    used_printers = await reports.printer_stats(session, period, user=key)

    return PortalPrintingOut(
        employee=_employee_out(key, employee),
        period=_period_out(period),
        quota=await _quota(session, key, period, override),
        access=access,
        printers=[
            PortalPrinterUsageOut(
                name=p.name,
                ip=p.last_ip if printer_registry.is_ip(p.last_ip) else None,
                pages=p.pages,
                jobs=p.jobs,
                failed_jobs=p.failed_jobs,
                last_printed_at=p.last_printed_at,
                allowed=allowed_ids is None or (p.device_id is not None and p.device_id in allowed_ids),
            )
            for p in used_printers
        ],
        daily=await _daily(session, key, period),
        generated_at=datetime.now(timezone.utc),
    )


async def jobs(
    session: AsyncSession,
    login: str,
    *,
    since: datetime | None,
    until: datetime | None,
    limit: int,
    offset: int,
) -> tuple[list[PortalJobOut], int]:
    """Xodimning o'z chop etishlari, eng yangisidan boshlab. Ikkinchi qiymat: jami soni."""
    key, _ = await _resolve(session, login)
    filters = [login_key(PrintJob.user_name) == key]
    if since:
        filters.append(PrintJob.printed_at >= since)
    if until:
        filters.append(PrintJob.printed_at < until)

    total = (await session.execute(select(func.count()).where(*filters))).scalar() or 0

    stmt = (
        printer_registry.join_device(
            select(
                PrintJob,
                reports.job_printer_name_expr().label("printer_name"),
                PrinterDevice.last_ip.label("device_ip"),
                counted_job().label("counted"),
            ).select_from(PrintJob)
        )
        .outerjoin(PrinterDevice, PrinterDevice.id == printer_registry.device_id_expr())
        .where(*filters)
        .order_by(PrintJob.printed_at.desc(), PrintJob.id.desc())
        .limit(limit)
        .offset(offset)
    )
    results = []
    for job, printer_name, device_ip, counted in (await session.execute(stmt)).all():
        ip = job.printer_ip if printer_registry.is_ip(job.printer_ip) else device_ip
        results.append(
            PortalJobOut(
                printed_at=job.printed_at,
                document=job.document,
                printer=printer_name or job.printer,
                printer_ip=ip if printer_registry.is_ip(ip) else None,
                computer=job.computer,
                pages=job.pages,
                success=job.success,
                reason=job.reason or None,
                counted=bool(counted),
            )
        )
    return results, total
