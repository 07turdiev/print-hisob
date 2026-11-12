"""Hisobot raqamlari: xodim sarfi va printerlar kesimi.

Dashboard (`/api/stats/*`), CSV eksport va portal API raqamlarni shu yerdan
oladi. Shuning uchun portalda xodim ko'rgan son dashboarddagi son bilan bir xil
chiqadi. Qaysi yozuv hisobga kirishi `app.rules` da belgilangan.
"""

from sqlalchemy import case, func, select, union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.logins import login_key, normalize_login
from app.models import Employee, EmployeeQuota, PrinterDevice, PrintJob, PrintUserOverride
from app.periods import Period, default_quota_for
from app.rules import counted_job
from app.schemas import EmployeeStatOut, PrinterStatOut
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
# Xodimlar sarfi va kvotasi
# ---------------------------------------------------------------------------


async def employee_stats(
    session: AsyncSession,
    period: Period,
    department: str | None = None,
    *,
    login: str | None = None,
) -> list[EmployeeStatOut]:
    """`/api/stats/employees`, CSV eksport va portal uchun umumiy agregatsiya.

    Har bir SQL agregatsiyasi shu yerda bir marta yoziladi — CSV eksport bu
    natijalarni faqat bo'lim bo'yicha guruhlab, boshqacha formatda chiqaradi,
    portal esa `login` bilan bitta qatorni oladi, lekin raqamlar har doim bir
    xil manbadan keladi.

    **Biriktirish qanday hisoblanadi.** Varaqlar hech qayerga ko'chirilmaydi:
    har bir xodim o'z sarfini (`used`) saqlaydi, egasining qatorida esa unga
    biriktirilganlardan kelgan yig'indi alohida ustun bo'lib qo'shiladi
    (`used_from_linked`). Kvota `used_total = used + used_from_linked` ga
    nisbatan tekshiriladi — shunda xodim o'zi qancha chiqarganini ham,
    unga qancha qo'shilganini ham ko'radi.

    Loginlar normallashtirilgan holda (kichik harf, `DOMAIN\\` prefiksisiz)
    guruhlanadi — bitta odam ikki xil yozilish bilan ikki qatorga bo'linib
    ketmasligi uchun (`app.logins.normalize_login` bilan bir xil qoida).

    Xodim davrda chop etmagan va unga biriktirilganlardan ham varaq kelmagan
    bo'lsa, u natijada bo'lmaydi.
    """
    # Bu davr uchun aniq kvota qatori bo'lmagan xodimlarga standart kvota
    # qo'llanadi (0 emas) — pastda `func.coalesce` shuni ta'minlaydi (faqat
    # qator umuman yo'qligida ishga tushadi, saqlangan 0 qiymatga tegmaydi).
    default_allocated = default_quota_for(period.period_type)
    period_filter = (
        PrintJob.printed_at >= period.start,
        PrintJob.printed_at < period.end,
        counted_job(),
    )
    norm_login = login_key(PrintJob.user_name)
    key = normalize_login(login) if login else None

    # 1) Davrda har bir xodimning **o'z** sarfi.
    usage_stmt = (
        select(
            norm_login.label("login"),
            # Ko'rsatish uchun xom yozilishlardan bittasi (odatda hammasi bir xil).
            func.max(PrintJob.user_name).label("raw_login"),
            func.coalesce(func.sum(PrintJob.pages), 0).label("used"),
        )
        .where(*period_filter)
        .group_by(norm_login)
    )
    if key:
        usage_stmt = usage_stmt.where(norm_login == key)
    usage = usage_stmt.subquery()

    # 2) Har bir "egaga" unga biriktirilgan loginlardan kelgan yig'indi.
    linked_stmt = (
        select(
            PrintUserOverride.charge_to_login.label("owner"),
            func.coalesce(func.sum(PrintJob.pages), 0).label("used"),
        )
        .select_from(PrintJob)
        .join(PrintUserOverride, PrintUserOverride.login == norm_login)
        .where(*period_filter, PrintUserOverride.charge_to_login.isnot(None))
        .group_by(PrintUserOverride.charge_to_login)
    )
    if key:
        linked_stmt = linked_stmt.where(PrintUserOverride.charge_to_login == key)
    linked = linked_stmt.subquery()

    # 3) Qatorlar to'plami: chop etganlar **va** biriktirilganlari bor egalar.
    #    Ikkinchisi kerak, chunki o'zi umuman chop etmagan xodim ham unga
    #    biriktirilgan varaqlar tufayli hisobotda ko'rinishi kerak.
    identities = union(
        select(usage.c.login.label("login")),
        select(linked.c.owner.label("login")),
    ).subquery()

    own_override = aliased(PrintUserOverride)
    used_expr = func.coalesce(usage.c.used, 0)
    linked_expr = func.coalesce(linked.c.used, 0)

    stmt = (
        select(
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
        .outerjoin(usage, usage.c.login == identities.c.login)
        .outerjoin(linked, linked.c.owner == identities.c.login)
        .outerjoin(Employee, login_key(Employee.login) == identities.c.login)
        .outerjoin(
            EmployeeQuota,
            (EmployeeQuota.login == identities.c.login)
            & (EmployeeQuota.period_type == period.period_type)
            & (EmployeeQuota.year == period.year)
            & (EmployeeQuota.period_no == period.period_no),
        )
        .outerjoin(own_override, own_override.login == identities.c.login)
    )
    if department:
        stmt = stmt.where(Employee.department == department)
    stmt = stmt.order_by((used_expr + linked_expr).desc())

    rows = (await session.execute(stmt)).all()

    results: list[EmployeeStatOut] = []
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
        results.append(
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
