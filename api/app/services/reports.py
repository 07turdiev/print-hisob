"""Hisobot raqamlari: xodim sarfi, bo'limlar va printerlar kesimi.

Dashboard (`/api/stats/*`), CSV eksport va portal API raqamlarni shu yerdan
oladi. Shuning uchun portalda xodim ko'rgan son dashboarddagi son bilan bir xil
chiqadi. Qaysi yozuv hisobga kirishi `app.rules` da belgilangan.
"""

from collections.abc import Sequence

from sqlalchemy import DateTime, Integer, String, and_, case, column, exists, func, select, union, values
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.logins import login_key, normalize_login
from app.models import Employee, EmployeeQuota, PrinterDevice, PrintJob, PrintUserOverride
from app.periods import Period, default_quota_for
from app.rules import counted_job
from app.schemas import DepartmentRollupOut, EmployeeStatOut, PrinterStatOut
from app.services import printers as printer_registry

# ---------------------------------------------------------------------------
# Printer identifikatsiyasi (MAC bo'yicha) — statistikada bir nechta joyda
# ishlatiladi, shuning uchun bitta manbadan olinadi.
# ---------------------------------------------------------------------------


def printer_usage_subquery(*filters):
    """Printer kesimida yig'indi: sahifalar, ishlar, muvaffaqiyat/xato sonlari.

    Guruhlash **qurilma** bo'yicha (`app.services.printers`): yozuv avval MAC,
    keyin IP, oxirida drayver nomi bo'yicha reyestrdagi qurilmaga bog'lanadi.
    Shu tufayli bitta jismoniy printer turli kompyuterlarda turlicha atalgan
    bo'lsa ham bitta qatorga birlashadi.
    """
    identity = printer_registry.identity_expr().label("identity")
    return (
        printer_registry.join_device(
            select(
                identity,
                func.max(printer_registry.device_id_expr()).label("device_id"),
                func.max(PrintJob.printer_mac).label("mac"),
                func.max(PrintJob.printer).label("raw_name"),
                func.max(PrintJob.printer_ip).label("printer_ip"),
                func.max(PrintJob.printed_at).label("last_printed_at"),
                func.coalesce(func.sum(PrintJob.pages), 0).label("pages"),
                func.count().label("jobs"),
                func.coalesce(
                    func.sum(case((PrintJob.success.is_(True), 1), else_=0)), 0
                ).label("success_jobs"),
                func.coalesce(
                    func.sum(case((PrintJob.success.is_(False), 1), else_=0)), 0
                ).label("failed_jobs"),
            ).select_from(PrintJob)
        )
        .where(*filters)
        .group_by(identity)
        .subquery()
    )


def job_printer_name_expr():
    """Bitta chop etish hodisasi uchun ko'rsatiladigan printer nomi.

    Tartib: admin reyestrda belgilagan nom -> reyestrdagi so'nggi drayver nomi ->
    hodisadagi xom nom. Shu tufayli bitta jismoniy printer barcha kompyuterlarda
    **bir xil** nom bilan ko'rinadi, garchi har bir kompyuterda drayver uni
    boshqacha atagan bo'lsa ham.
    """
    return func.coalesce(PrinterDevice.name, PrinterDevice.last_driver_name, PrintJob.printer)


def printer_display_name_expr(usage_subquery):
    """Ko'rsatish uchun tayyor nom: admin nomi -> so'nggi drayver nomi -> xom nom."""
    return func.coalesce(
        PrinterDevice.name, PrinterDevice.last_driver_name, usage_subquery.c.raw_name
    )


async def printer_stats(
    session: AsyncSession, period: Period, *, user: str | None = None
) -> list[PrinterStatOut]:
    """Davrda ishlatilgan printerlar, sahifalar bo'yicha kamayish tartibida.

    `user` berilsa, faqat shu xodimning o'z chop etishlari olinadi (har qanday
    yozilishda: `MADANIYAT\\ali`, `Ali`). Unga biriktirilganlarniki qo'shilmaydi.
    """
    filters = [
        PrintJob.printed_at >= period.start,
        PrintJob.printed_at < period.end,
        counted_job(),
    ]
    if user:
        filters.append(login_key(PrintJob.user_name) == normalize_login(user))
    usage = printer_usage_subquery(*filters)
    stmt = (
        select(
            usage.c.device_id,
            usage.c.mac,
            printer_display_name_expr(usage).label("name"),
            usage.c.pages,
            usage.c.jobs,
            usage.c.success_jobs,
            usage.c.failed_jobs,
            func.coalesce(PrinterDevice.last_ip, usage.c.printer_ip).label("last_ip"),
            usage.c.last_printed_at,
        )
        .select_from(usage)
        .outerjoin(PrinterDevice, PrinterDevice.id == usage.c.device_id)
        .order_by(usage.c.pages.desc())
    )
    rows = (await session.execute(stmt)).all()

    results: list[PrinterStatOut] = []
    for row in rows:
        jobs = row.jobs or 0
        success_jobs = row.success_jobs or 0
        success_rate = (success_jobs / jobs) if jobs else 0.0
        results.append(
            PrinterStatOut(
                device_id=row.device_id,
                mac=row.mac,
                name=row.name,
                pages=row.pages,
                jobs=jobs,
                success_rate=round(success_rate, 4),
                failed_jobs=row.failed_jobs or 0,
                last_ip=row.last_ip,
                last_printed_at=row.last_printed_at,
            )
        )
    return results


# ---------------------------------------------------------------------------
# Xodimlar sarfi va normasi
# ---------------------------------------------------------------------------


def _periods_table(periods: Sequence[Period], name: str):
    """Davrlar ro'yxati SQL jadvali sifatida: bitta so'rov bir nechta davrni hisoblaydi.

    So'rovda jadvalga bir necha joydan murojaat qilinadi, har biriga alohida nom kerak.
    """
    return values(
        column("idx", Integer),
        column("period_type", String),
        column("year", Integer),
        column("period_no", Integer),
        column("starts_at", DateTime(timezone=True)),
        column("ends_at", DateTime(timezone=True)),
        name=name,
    ).data([(i, p.period_type, p.year, p.period_no, p.start, p.end) for i, p in enumerate(periods)])


def _in_period(table):
    return and_(PrintJob.printed_at >= table.c.starts_at, PrintJob.printed_at < table.c.ends_at)


async def employee_stats(
    session: AsyncSession,
    period: Period,
    department: str | None = None,
    *,
    login: str | None = None,
) -> list[EmployeeStatOut]:
    """Bitta davr uchun `employee_stats_by_period`.

    `/api/stats/employees`, CSV eksport va portal shu funksiyani chaqiradi.
    """
    return (await employee_stats_by_period(session, [period], department, login=login))[0]


async def employee_stats_by_period(
    session: AsyncSession,
    periods: Sequence[Period],
    department: str | None = None,
    *,
    login: str | None = None,
) -> list[list[EmployeeStatOut]]:
    """Har bir xodimning sarfi va normasi, har bir davr uchun alohida ro'yxat.

    Natija `periods` tartibida. Hamma davr bitta SQL so'rovda hisoblanadi, shuning
    uchun portaldagi tarix (`/history`) davrlar soniga qarab so'rov ko'paytirmaydi
    va raqamlari bitta davr so'ralgandagi bilan aynan bir xil chiqadi. Davrlar
    bir turda (hammasi oy yoki hammasi chorak) bo'lishi kerak.

    **Biriktirish qanday hisoblanadi.** Varaqlar hech qayerga ko'chirilmaydi:
    har bir xodim o'z sarfini (`used`) saqlaydi, egasining qatorida esa unga
    biriktirilganlardan kelgan yig'indi alohida ustun bo'lib qo'shiladi
    (`used_from_linked`). Norma `used_total = used + used_from_linked` ga
    nisbatan tekshiriladi — shunda xodim o'zi qancha chiqarganini ham,
    unga qancha qo'shilganini ham ko'radi. Biriktirish tarixiy emas: hozirgi
    biriktirish barcha davrlarga qo'llanadi.

    Loginlar normallashtirilgan holda (kichik harf, `DOMAIN\\` prefiksisiz)
    guruhlanadi — bitta odam ikki xil yozilish bilan ikki qatorga bo'linib
    ketmasligi uchun (`app.logins.normalize_login` bilan bir xil qoida).

    Xodim davrda chop etmagan va unga biriktirilganlardan ham varaq kelmagan
    bo'lsa, u o'sha davr ro'yxatida bo'lmaydi.
    """
    if not periods:
        return []
    if len({p.period_type for p in periods}) != 1:
        raise ValueError("Davrlar bir turda bo'lishi kerak")

    # Bu davr uchun aniq norma qatori bo'lmagan xodimlarga standart norma
    # qo'llanadi (0 emas) — pastda `func.coalesce` shuni ta'minlaydi (faqat
    # qator umuman yo'qligida ishga tushadi, saqlangan 0 qiymatga tegmaydi).
    default_allocated = default_quota_for(periods[0].period_type)
    norm_login = login_key(PrintJob.user_name)
    key = normalize_login(login) if login else None

    # 1) Har bir davrda har bir xodimning **o'z** sarfi.
    usage_periods = _periods_table(periods, "usage_periods")
    usage_stmt = (
        select(
            usage_periods.c.idx.label("idx"),
            norm_login.label("login"),
            # Ko'rsatish uchun xom yozilishlardan bittasi (odatda hammasi bir xil).
            func.max(PrintJob.user_name).label("raw_login"),
            func.coalesce(func.sum(PrintJob.pages), 0).label("used"),
        )
        .select_from(PrintJob)
        .join(usage_periods, _in_period(usage_periods))
        .where(counted_job())
        .group_by(usage_periods.c.idx, norm_login)
    )
    if key:
        usage_stmt = usage_stmt.where(norm_login == key)
    usage = usage_stmt.subquery()

    # 2) Har bir "egaga" unga biriktirilgan loginlardan kelgan yig'indi.
    linked_periods = _periods_table(periods, "linked_periods")
    linked_stmt = (
        select(
            linked_periods.c.idx.label("idx"),
            PrintUserOverride.charge_to_login.label("owner"),
            func.coalesce(func.sum(PrintJob.pages), 0).label("used"),
        )
        .select_from(PrintJob)
        .join(linked_periods, _in_period(linked_periods))
        .join(PrintUserOverride, PrintUserOverride.login == norm_login)
        .where(counted_job(), PrintUserOverride.charge_to_login.isnot(None))
        .group_by(linked_periods.c.idx, PrintUserOverride.charge_to_login)
    )
    if key:
        linked_stmt = linked_stmt.where(PrintUserOverride.charge_to_login == key)
    linked = linked_stmt.subquery()

    # 3) Qatorlar to'plami: chop etganlar **va** biriktirilganlari bor egalar.
    #    Ikkinchisi kerak, chunki o'zi umuman chop etmagan xodim ham unga
    #    biriktirilgan varaqlar tufayli hisobotda ko'rinishi kerak.
    identities = union(
        select(usage.c.idx, usage.c.login.label("login")),
        select(linked.c.idx, linked.c.owner.label("login")),
    ).subquery()

    quota_periods = _periods_table(periods, "quota_periods")
    own_override = aliased(PrintUserOverride)
    used_expr = func.coalesce(usage.c.used, 0)
    linked_expr = func.coalesce(linked.c.used, 0)

    stmt = (
        select(
            identities.c.idx,
            identities.c.login,
            func.coalesce(usage.c.raw_login, identities.c.login).label("raw_login"),
            Employee.full_name,
            Employee.department,
            Employee.position,
            Employee.is_active,
            used_expr.label("used"),
            linked_expr.label("used_from_linked"),
            func.coalesce(EmployeeQuota.allocated_pages, default_allocated).label("allocated"),
            own_override.blocked,
            own_override.charge_to_login,
        )
        .select_from(identities)
        .join(quota_periods, quota_periods.c.idx == identities.c.idx)
        .outerjoin(usage, (usage.c.idx == identities.c.idx) & (usage.c.login == identities.c.login))
        .outerjoin(
            linked, (linked.c.idx == identities.c.idx) & (linked.c.owner == identities.c.login)
        )
        .outerjoin(Employee, login_key(Employee.login) == identities.c.login)
        .outerjoin(
            EmployeeQuota,
            (EmployeeQuota.login == identities.c.login)
            & (EmployeeQuota.period_type == quota_periods.c.period_type)
            & (EmployeeQuota.year == quota_periods.c.year)
            & (EmployeeQuota.period_no == quota_periods.c.period_no),
        )
        .outerjoin(own_override, own_override.login == identities.c.login)
    )
    if department:
        stmt = stmt.where(Employee.department == department)
    stmt = stmt.order_by(identities.c.idx, (used_expr + linked_expr).desc(), identities.c.login)

    rows = (await session.execute(stmt)).all()

    results: list[list[EmployeeStatOut]] = [[] for _ in periods]
    for row in rows:
        if row.is_active is None:
            match_status = "unmatched"
        elif row.is_active:
            match_status = "active"
        else:
            match_status = "inactive"

        used = row.used or 0
        used_from_linked = row.used_from_linked or 0
        used_total = used + used_from_linked
        allocated = row.allocated or 0
        results[row.idx].append(
            EmployeeStatOut(
                login=row.raw_login or row.login,
                full_name=row.full_name,
                department=row.department,
                position=row.position,
                used=used,
                used_from_linked=used_from_linked,
                used_total=used_total,
                allocated=allocated,
                remaining=allocated - used_total,
                over_limit=used_total > allocated,
                match_status=match_status,
                charged_to=row.charge_to_login,
                blocked=bool(row.blocked),
            )
        )
    return results


async def usage_by_login(
    session: AsyncSession, period: Period, logins: Sequence[str]
) -> dict[str, tuple[int, int]]:
    """Davrda har bir loginning hisobga kiradigan varaqlari va ishlari.

    Natija: `{normallashtirilgan login: (varaqlar, ishlar)}`. Chop etmagan login
    natijada bo'lmaydi. Biriktirilgan loginlar ro'yxati uchun: ularning
    varaqlari yig'indisi egasining `used_from_linked` iga teng.
    """
    keys = sorted({key for key in (normalize_login(login) for login in logins) if key})
    if not keys:
        return {}
    norm_login = login_key(PrintJob.user_name)
    stmt = (
        select(
            norm_login.label("login"),
            func.coalesce(func.sum(PrintJob.pages), 0).label("pages"),
            func.count().label("jobs"),
        )
        .where(
            PrintJob.printed_at >= period.start,
            PrintJob.printed_at < period.end,
            counted_job(),
            norm_login.in_(keys),
        )
        .group_by(norm_login)
    )
    return {row.login: (row.pages, row.jobs) for row in (await session.execute(stmt)).all()}


# ---------------------------------------------------------------------------
# Bo'limlar kesimi
# ---------------------------------------------------------------------------


async def department_rollup(session: AsyncSession, period: Period) -> list[DepartmentRollupOut]:
    """`Employee.department` bo'yicha davr uchun to'liq agregatsiya.

    - Sarf (`pages`, `jobs`) har bir ishni chop etgan xodimning bo'limiga yozadi.
      Biriktirish qo'shilmaydi, shuning uchun bu haqiqiy qog'oz sarfi. Ketgan
      xodimning shu davrdagi ishlari ham o'z (oxirgi) bo'limida sanaladi.
    - Xodimlar soni va normalar yig'indisi faqat faol xodimlar bo'yicha.

    Bo'lim joriy AD tuzilishi bo'yicha olinadi (tarixiy emas). Bo'limi yo'q
    loginlarning sarfi `unassigned_usage` da.
    """
    department = Employee.department
    names = select(department.label("name")).where(department.isnot(None)).distinct().subquery()

    employee_counts = (
        select(department.label("name"), func.count().label("employee_count"))
        .where(department.isnot(None), Employee.is_active.is_(True))
        .group_by(department)
        .subquery()
    )

    # Har bir faol xodim uchun shu davrga aniq norma qatori bo'lmasa, standart
    # norma qo'llanadi (0 emas) — shuning uchun `Employee`dan boshlab
    # `EmployeeQuota`ga outer join qilinadi (aksincha bo'lsa, norma qatori
    # yo'q xodimlar yig'indiga umuman kirmay qolar edi).
    default_allocated = default_quota_for(period.period_type)
    per_employee_quota = (
        select(
            department.label("name"),
            func.coalesce(EmployeeQuota.allocated_pages, default_allocated).label("allocated"),
        )
        .select_from(Employee)
        .outerjoin(
            EmployeeQuota,
            (EmployeeQuota.login == login_key(Employee.login))
            & (EmployeeQuota.period_type == period.period_type)
            & (EmployeeQuota.year == period.year)
            & (EmployeeQuota.period_no == period.period_no),
        )
        .where(department.isnot(None), Employee.is_active.is_(True))
        .subquery()
    )

    quota_totals = (
        select(
            per_employee_quota.c.name,
            func.sum(per_employee_quota.c.allocated).label("total_allocated"),
        )
        .group_by(per_employee_quota.c.name)
        .subquery()
    )

    pages_totals = (
        select(
            department.label("name"),
            func.coalesce(func.sum(PrintJob.pages), 0).label("pages"),
            func.count().label("jobs"),
        )
        .select_from(PrintJob)
        .join(Employee, login_key(Employee.login) == login_key(PrintJob.user_name))
        .where(
            department.isnot(None),
            PrintJob.printed_at >= period.start,
            PrintJob.printed_at < period.end,
            counted_job(),
        )
        .group_by(department)
        .subquery()
    )

    stmt = (
        select(
            names.c.name,
            func.coalesce(pages_totals.c.pages, 0).label("pages"),
            func.coalesce(pages_totals.c.jobs, 0).label("jobs"),
            func.coalesce(employee_counts.c.employee_count, 0).label("employee_count"),
            func.coalesce(quota_totals.c.total_allocated, 0).label("total_allocated"),
        )
        .select_from(names)
        .outerjoin(pages_totals, pages_totals.c.name == names.c.name)
        .outerjoin(employee_counts, employee_counts.c.name == names.c.name)
        .outerjoin(quota_totals, quota_totals.c.name == names.c.name)
        .order_by(func.coalesce(pages_totals.c.pages, 0).desc())
    )
    rows = (await session.execute(stmt)).all()

    results: list[DepartmentRollupOut] = []
    for row in rows:
        used = row.pages or 0
        allocated = row.total_allocated or 0
        results.append(
            DepartmentRollupOut(
                name=row.name,
                pages=used,
                jobs=row.jobs or 0,
                employee_count=row.employee_count or 0,
                total_allocated=allocated,
                remaining=allocated - used,
                over_limit=used > allocated,
            )
        )
    return results


async def unassigned_usage(session: AsyncSession, period: Period) -> tuple[int, int]:
    """Hech qaysi bo'limga yozilmaydigan sarf: `(varaqlar, ishlar)`.

    AD'da yo'q loginlar va bo'limi bo'sh xodimlarning ishlari. `department_rollup`
    yig'indisiga shu son qo'shilsa, davrning umumiy sarfi chiqadi.
    """
    has_department = exists(
        select(1)
        .where(
            login_key(Employee.login) == login_key(PrintJob.user_name),
            Employee.department.isnot(None),
        )
        .correlate_except(Employee)
    )
    stmt = select(
        func.coalesce(func.sum(PrintJob.pages), 0).label("pages"),
        func.count().label("jobs"),
    ).where(
        PrintJob.printed_at >= period.start,
        PrintJob.printed_at < period.end,
        counted_job(),
        ~has_department,
    )
    row = (await session.execute(stmt)).one()
    return row.pages or 0, row.jobs or 0
