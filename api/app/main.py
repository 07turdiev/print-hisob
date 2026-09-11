import csv
import io
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from fastapi import Depends, FastAPI, HTTPException, Query, Response, Security, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import Integer, case, cast, exists, func, literal, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    API_KEY_UNAUTHORIZED_RESPONSE,
    USER_UNAUTHORIZED_RESPONSE,
    create_access_token,
    require_api_key,
    require_user,
    verify_credentials,
)
from app.config import settings
from app.db import Base, engine, get_session
from app.models import AgentStatus, Employee, EmployeeQuota, PrintJob, Printer
from app.periods import Period, PeriodType, default_quota_for, period_bounds, period_label
from app.routers import print_quotas
from app.schemas import (
    AdSyncStatusOut,
    AgentOut,
    AgentsSummaryOut,
    AgentStatusIn,
    AgentStatusResult,
    DepartmentRollupOut,
    EmployeeOut,
    EmployeeQuotaIn,
    EmployeeQuotaOut,
    EmployeeStatOut,
    EmployeeSyncBatch,
    EmployeeSyncResult,
    FailureReasonOut,
    IngestResult,
    LoginIn,
    LoginOut,
    PrintJobBatch,
    PrintJobOut,
    PrinterNameIn,
    PrinterOut,
    PrinterStatOut,
    StatsSummaryOut,
    TimeseriesPointOut,
    TopItemOut,
    TopStatsOut,
)

logger = logging.getLogger(__name__)

# Postgres bitta so'rovda 65535 parametrni qabul qiladi; 11 ustun -> xavfsiz bo'lak.
CHUNK_SIZE = 500


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    if settings.auto_create_tables:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


DESCRIPTION = """
Ish stantsiyalaridagi agentlardan chop etish hodisalarini qabul qilib PostgreSQL'ga yozadi.

### Ma'lumotlarni qayta ishlash qoidalari

* **Bo'sh satr → `NULL`.** `printerIp: ""` va `reason: ""` bazaga `NULL` bo'lib tushadi.
* **Vaqt.** `.NET` uslubidagi 7 xonali kasr soniya (`...10.1234567+00:00`) qabul qilinadi
  va `timestamptz` aniqligiga (6 xona) kesiladi. Mintaqasiz vaqt UTC deb olinadi.
* **Dublikatlar.** Har hodisa `computer + user + document + printer + timestamp` bo'yicha
  yagona. Agent o'sha paketni qayta yuborsa takroriy qator qo'shilmaydi — javobda
  `inserted: 0`, `duplicates: N` ko'rinadi.
* **Qog'oz sarfi (varaq).** `pages` — jismoniy qog'oz (varaq) soni; agent duplex
  hisobini o'zi qilib, tayyor holda yuboradi (masalan 3 sahifali duplex hujjat
  uchun `pages=2`). Statistikada sarf har doim `SUM(pages)` bilan hisoblanadi —
  serverda qo'shimcha yaxlitlash/bo'lish qilinmaydi. `documentPages` — fayldagi
  sahifalar soni (varaq emas), faqat ma'lumot uchun saqlanadi. `duplex` — ikki
  tomonlama chop etilganmi, shuningdek faqat ma'lumot uchun (allaqachon
  `pages`da hisobga olingan).
"""

TAGS_METADATA = [
    {"name": "auth", "description": "Dashboard foydalanuvchisi autentifikatsiyasi (JWT)."},
    {"name": "print-jobs", "description": "Chop etish hodisalarini yozish va o'qish."},
    {"name": "printers", "description": "Printerlar reyestri (MAC bo'yicha identifikatsiya va qulay nom)."},
    {"name": "employees", "description": "AD (Active Directory) xodimlar sinxronizatsiyasi."},
    {
        "name": "quotas",
        "description": (
            "Xodimlar uchun oylik/choraklik qog'oz kvotalari va ish stantsiyasidagi "
            "agent bilan limit almashinuvi (`/api/print-quotas`)."
        ),
    },
    {"name": "stats", "description": "Chorak/oy bo'yicha dashboard statistikasi."},
    {"name": "agents", "description": "Agent (.exe) sog'lik holati (heartbeat) monitoringi."},
    {"name": "service", "description": "Xizmat va baza holatini tekshirish."},
]

app = FastAPI(
    title="Printer Hisob API",
    description=DESCRIPTION,
    version="1.0.0",
    openapi_tags=TAGS_METADATA,
    lifespan=lifespan,
)

# CORS — dashboard brauzerda boshqa origin'dan (masalan Vite dev serveri) so'rov
# yuborgani uchun kerak. Mahalliy dev portlari regex bilan, prod manzillari esa
# CORS_ORIGINS orqali ruxsat etiladi. Bearer token ishlatilgani uchun cookie/credentials shart emas.
_cors_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)

# Autentifikatsiya (`require_api_key`, `require_user`) va javob namunalari
# `app.auth` da — dekoratorlardagi eski nom saqlanadi.
UNAUTHORIZED_RESPONSE = API_KEY_UNAUTHORIZED_RESPONSE

# Alohida modullarga ko'chirilgan endpointlar.
app.include_router(print_quotas.router)


async def period_params(
    period_type: PeriodType = Query(..., description="Davr turi: 'month' yoki 'quarter'"),
    year: int = Query(..., ge=2000, le=2100, description="Yil, masalan 2026"),
    period_no: int = Query(
        ..., description="Oy uchun 1..12, chorak uchun 1..4 (Q1=1..Q4=4)"
    ),
) -> Period:
    """`period_type/year/period_no` query-parametrlaridan `[start, end)` chegarasini hisoblaydi."""
    try:
        start, end = period_bounds(period_type, year, period_no)
    except ValueError as exc:
        # `status.HTTP_422_UNPROCESSABLE_ENTITY` starlette'da eskirgan; sonni to'g'ridan-to'g'ri ishlatamiz.
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return Period(period_type=period_type, year=year, period_no=period_no, start=start, end=end)


def _employee_scope_clause(department: str | None):
    """`PrintJob.user_name`ni `Employee` jadvali orqali bo'lim bo'yicha
    filtrlash uchun `EXISTS` sharti quradi. Berilmasa `None` qaytadi
    (filtr qo'llanmaydi, eski xatti-harakat saqlanadi).

    **Muhim**: bu filtr faol bo'lganda AD'da topilmagan (`unmatched`) login'lar
    natijadan chiqib qoladi — ularning bo'limi yo'q, shuning uchun hech qaysi
    bo'lim bo'yicha filtrga mos kelmaydi.
    """
    if not department:
        return None
    conditions = [Employee.login == PrintJob.user_name, Employee.department == department]
    # `correlate_except(Employee)`: `departments_stmt`da `Employee` allaqachon
    # tashqi so'rovga qo'shilgan (outerjoin) bo'lishi mumkin — shunda avtomatik
    # korrelyatsiya uni ham ichki FROM'dan olib tashlab, bo'sh subquery hosil
    # qilib qo'yardi. `Employee`ni har doim ichki FROM'da qoldiramiz.
    inner = select(1).where(*conditions).correlate_except(Employee)
    return exists(inner)


# ---------------------------------------------------------------------------
# Printer identifikatsiyasi (MAC bo'yicha) — statistikada bir nechta joyda
# ishlatiladi, shuning uchun bitta manbadan olinadi.
# ---------------------------------------------------------------------------


def _printer_identity_expr():
    """Guruhlash uchun identifikator: mac mavjud bo'lsa mac, aks holda xom
    printer nomi (USB/ulashilgan/mac yubormaydigan agentlar uchun zaxira)."""
    return func.coalesce(PrintJob.printer_mac, PrintJob.printer)


def _printer_usage_subquery(*filters):
    """Davr (va boshqa) filtrlar bo'yicha printer identifikatori kesimida
    yig'indi: sahifalar, ishlar, muvaffaqiyat/xato sonlari, hamda reyestr
    bilan bog'lash uchun `mac` va zaxira ko'rsatish uchun `raw_name`/`printer_ip`.
    """
    identity = _printer_identity_expr().label("identity")
    return (
        select(
            identity,
            func.max(PrintJob.printer_mac).label("mac"),
            func.max(PrintJob.printer).label("raw_name"),
            func.max(PrintJob.printer_ip).label("printer_ip"),
            func.coalesce(func.sum(PrintJob.pages), 0).label("pages"),
            func.count().label("jobs"),
            func.coalesce(
                func.sum(case((PrintJob.success.is_(True), 1), else_=0)), 0
            ).label("success_jobs"),
            func.coalesce(
                func.sum(case((PrintJob.success.is_(False), 1), else_=0)), 0
            ).label("failed_jobs"),
        )
        .where(*filters)
        .group_by(identity)
        .subquery()
    )


def _print_job_printer_name_expr():
    """Bitta chop etish hodisasi uchun ko'rsatiladigan printer nomi.

    Tartib: admin reyestrda belgilagan nom -> reyestrdagi so'nggi drayver nomi ->
    hodisadagi xom nom. Shu tufayli bitta jismoniy printer (bir xil MAC) barcha
    kompyuterlarda **bir xil** nom bilan ko'rinadi, garchi har bir kompyuterda
    drayver uni boshqacha atagan bo'lsa ham.

    MAC'i yo'q hodisalarda (USB, ulashilgan navbat, boshqa L2 segment) reyestrda
    qator bo'lmaydi va xom nom ishlatiladi.
    """
    return func.coalesce(Printer.name, Printer.last_driver_name, PrintJob.printer)


def _printer_display_name_expr(usage_subquery):
    """Ko'rsatish uchun tayyor nom: reyestr qulay nomi -> reyestr so'nggi drayver
    nomi -> hodisadagi xom printer nomi -> mac (identifikator o'zi)."""
    return func.coalesce(
        Printer.name, Printer.last_driver_name, usage_subquery.c.raw_name, usage_subquery.c.mac
    )


@app.get(
    "/health",
    tags=["service"],
    summary="Xizmat holati",
    description="Bazaga oddiy so'rov yuborib ulanish tirikligini tekshiradi.",
)
async def health(session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    await session.execute(select(1))
    return {"status": "ok", "database": "ok"}


# ---------------------------------------------------------------------------
# Dashboard foydalanuvchisi autentifikatsiyasi (JWT)
# ---------------------------------------------------------------------------


@app.post(
    "/api/auth/login",
    response_model=LoginOut,
    tags=["auth"],
    summary="Dashboard uchun login (JWT token olish)",
    response_description="Bearer token va uning amal qilish muddati",
    responses={status.HTTP_401_UNAUTHORIZED: {"description": "Login yoki parol noto'g'ri"}},
)
async def login(payload: LoginIn) -> LoginOut:
    """Login/parolni `.env`dagi (`AUTH_USERNAME`/`AUTH_PASSWORD`) qiymatlar bilan
    solishtiradi va muvaffaqiyatli bo'lsa JWT bearer token qaytaradi.

    Bu token keyingi so'rovlarda `Authorization: Bearer <token>` sarlavhasi orqali
    yuboriladi (`require_user`). Bu — agentlar ishlatadigan `X-API-Key`dan butunlay
    alohida mexanizm.
    """
    if not settings.jwt_secret or not settings.auth_password:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server konfiguratsiyasi to'liq emas: JWT_SECRET yoki AUTH_PASSWORD o'rnatilmagan",
        )
    if not verify_credentials(payload.username, payload.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Login yoki parol noto'g'ri"
        )
    token, expires_in = create_access_token(payload.username)
    return LoginOut(access_token=token, token_type="bearer", expires_in=expires_in)


@app.post(
    "/api/print-jobs",
    response_model=IngestResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Security(require_api_key)],
    tags=["print-jobs"],
    summary="Chop etish hodisalari paketini saqlash",
    response_description="Qabul qilingan, yozilgan va o'tkazib yuborilgan hodisalar soni",
    responses=UNAUTHORIZED_RESPONSE,
)
async def ingest_print_jobs(
    batch: PrintJobBatch,
    session: AsyncSession = Depends(get_session),
) -> IngestResult:
    """Bir kompyuterdan kelgan chop etish hodisalarini saqlaydi.

    Har bir hodisa `dedup_key` bo'yicha yagona. Agent tarmoq uzilishidan keyin
    o'sha paketni qayta yuborsa, takroriy yozuvlar qo'shilmaydi.
    """
    received = len(batch.jobs)
    if received == 0:
        return IngestResult(computer=batch.computer, received=0, inserted=0, duplicates=0)

    now = datetime.now(timezone.utc)

    # Paket ichidagi takrorlarni oldindan olib tashlaymiz.
    rows_by_key: dict[str, dict] = {}
    for job in batch.jobs:
        key = job.dedup_key(batch.computer)
        rows_by_key[key] = {
            "computer": batch.computer,
            "user_name": job.user_name,
            "document": job.document,
            "printer": job.printer,
            "printer_ip": job.printer_ip,
            "pages": job.pages,
            "document_pages": job.document_pages,
            "duplex": job.duplex,
            "printed_at": job.normalized_timestamp(),
            "success": job.success,
            "reason": job.reason,
            "printer_mac": job.printer_mac,
            "job_id": job.job_id,
            "dedup_key": key,
        }

    rows = list(rows_by_key.values())
    inserted = 0

    # Har bir mac uchun batch ichidagi eng so'nggi (printed_at bo'yicha) hodisani
    # tanlaymiz — printerlar reyestrini shu bilan yangilaymiz (`name`ga tegmasdan).
    printer_updates: dict[str, dict] = {}
    for row in rows:
        mac = row["printer_mac"]
        if not mac:
            continue
        existing = printer_updates.get(mac)
        if existing is None or row["printed_at"] >= existing["printed_at"]:
            printer_updates[mac] = row

    async with session.begin():
        # Printerlar reyestri chop etish yozuvlaridan OLDIN yangilanadi — shuning
        # uchun bir xil paketda mac kelsa ham, oxirgi bajarilgan so'rov har doim
        # print_jobs INSERT'i bo'lib qoladi (dedup_key asosidagi rowcount hisobi
        # va testlar shunga tayanadi).
        if printer_updates:
            printer_rows = [
                {
                    "mac": mac,
                    "last_ip": row["printer_ip"],
                    "last_driver_name": row["printer"],
                    "last_seen": now,
                }
                for mac, row in printer_updates.items()
            ]
            for start in range(0, len(printer_rows), CHUNK_SIZE):
                chunk = printer_rows[start : start + CHUNK_SIZE]
                printer_stmt = pg_insert(Printer).values(chunk)
                printer_stmt = printer_stmt.on_conflict_do_update(
                    index_elements=["mac"],
                    set_={
                        "last_ip": printer_stmt.excluded.last_ip,
                        "last_driver_name": printer_stmt.excluded.last_driver_name,
                        "last_seen": printer_stmt.excluded.last_seen,
                        # `name` ataylab yangilanmaydi — admin qo'lda belgilagan qiymat saqlanadi.
                    },
                )
                await session.execute(printer_stmt)

        for start in range(0, len(rows), CHUNK_SIZE):
            chunk = rows[start : start + CHUNK_SIZE]
            stmt = (
                pg_insert(PrintJob)
                .values(chunk)
                .on_conflict_do_nothing(index_elements=["dedup_key"])
            )
            result = await session.execute(stmt)
            inserted += result.rowcount or 0

    logger.info(
        "computer=%s received=%d inserted=%d", batch.computer, received, inserted
    )
    return IngestResult(
        computer=batch.computer,
        received=received,
        inserted=inserted,
        duplicates=received - inserted,
    )


@app.get(
    "/api/print-jobs",
    response_model=list[PrintJobOut],
    dependencies=[Security(require_user)],
    tags=["print-jobs"],
    summary="Yozuvlarni filtrlab olish",
    response_description=(
        "Eng yangisidan boshlab tartiblangan hodisalar. `X-Total-Count` javob "
        "sarlavhasida (bir xil filtrlar bilan) sahifalash uchun umumiy son beriladi."
    ),
    responses=USER_UNAUTHORIZED_RESPONSE,
)
async def list_print_jobs(
    response: Response,
    session: AsyncSession = Depends(get_session),
    computer: str | None = Query(default=None, description="Ish stantsiyasi nomi"),
    user: str | None = Query(default=None, description="Foydalanuvchi login'i"),
    printer: str | None = Query(
        default=None,
        description=(
            "Printer nomi bo'yicha qidiruv (qisman moslik). Reyestrdagi qulay nom ham, "
            "hodisadagi xom drayver nomi ham tekshiriladi."
        ),
    ),
    printer_mac: str | None = Query(
        default=None, description="Aniq qurilma (MAC manzili) bo'yicha filtr"
    ),
    success: bool | None = Query(default=None, description="Faqat muvaffaqiyatli/xato"),
    since: datetime | None = Query(default=None, description="Shu vaqtdan boshlab (ISO-8601)"),
    until: datetime | None = Query(default=None, description="Shu vaqtgacha, chegara kirmaydi"),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> list[PrintJobOut]:
    """Jurnal uchun chop etish hodisalari.

    Printer nomi **reyestrdan** (MAC bo'yicha) olinadi: bitta jismoniy printer turli
    kompyuterlarda turlicha drayver nomi bilan ko'ringan bo'lsa ham, jurnalda hamma
    joyda admin belgilagan yagona nom chiqadi (`printerName`). Xom nom `printer`
    maydonida saqlanib qoladi — diagnostika uchun.
    """
    filters = []
    if computer:
        filters.append(PrintJob.computer == computer)
    if user:
        filters.append(PrintJob.user_name == user)
    if printer:
        # Qidiruv reyestrdagi qulay nomga ham tushishi kerak — foydalanuvchi jadvalda
        # ko'rgan nomni yozadi, xom drayver nomini emas.
        like = f"%{printer}%"
        filters.append(
            or_(
                PrintJob.printer.ilike(like),
                Printer.name.ilike(like),
                Printer.last_driver_name.ilike(like),
            )
        )
    if printer_mac:
        filters.append(PrintJob.printer_mac == printer_mac)
    if success is not None:
        filters.append(PrintJob.success.is_(success))
    if since:
        filters.append(PrintJob.printed_at >= since)
    if until:
        filters.append(PrintJob.printed_at < until)

    # Reyestrga bog'lash — MAC'i bo'lmagan hodisalar ham qolishi uchun outer join.
    def _with_registry(stmt):
        return stmt.select_from(PrintJob).outerjoin(Printer, Printer.mac == PrintJob.printer_mac)

    # Sahifalash uchun umumiy son — bir xil filtrlar bilan, `limit`/`offset`siz.
    count_stmt = _with_registry(select(func.count()))
    if filters:
        count_stmt = count_stmt.where(*filters)
    total = (await session.execute(count_stmt)).scalar() or 0
    response.headers["X-Total-Count"] = str(total)

    stmt = _with_registry(select(PrintJob, _print_job_printer_name_expr()))
    if filters:
        stmt = stmt.where(*filters)
    stmt = stmt.order_by(PrintJob.printed_at.desc()).limit(limit).offset(offset)

    results: list[PrintJobOut] = []
    for job, printer_name in (await session.execute(stmt)).all():
        out = PrintJobOut.model_validate(job)
        out.printer_name = printer_name or job.printer
        results.append(out)
    return results


# ---------------------------------------------------------------------------
# Printerlar reyestri (MAC bo'yicha identifikatsiya + admin nomi)
# ---------------------------------------------------------------------------


def _printer_out(row: Printer) -> PrinterOut:
    return PrinterOut(
        mac=row.mac,
        name=row.name,
        display_name=row.name or row.last_driver_name or row.mac,
        last_ip=row.last_ip,
        last_driver_name=row.last_driver_name,
        last_seen=row.last_seen,
        first_seen=row.first_seen,
    )


@app.get(
    "/api/printers",
    response_model=list[PrinterOut],
    dependencies=[Security(require_user)],
    tags=["printers"],
    summary="Printerlar reyestrini olish (MAC bo'yicha)",
    response_description="Eng so'nggi ko'rilganidan boshlab tartiblangan printerlar",
    responses=USER_UNAUTHORIZED_RESPONSE,
)
async def list_printers(
    session: AsyncSession = Depends(get_session),
    q: str | None = Query(default=None, description="MAC, nom yoki drayver nomi bo'yicha qidiruv"),
) -> list[PrinterOut]:
    """Ingest paytida `printer_mac` bilan kelgan har bir printer shu yerda
    avtomatik paydo bo'ladi (`POST /api/print-jobs` upsert qiladi). Admin
    `PUT /api/printers/{mac}` orqali qulay nom belgilaydi.
    """
    stmt = select(Printer).order_by(Printer.last_seen.desc().nullslast())
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                Printer.mac.ilike(like),
                Printer.name.ilike(like),
                Printer.last_driver_name.ilike(like),
            )
        )
    rows = list((await session.scalars(stmt)).all())
    return [_printer_out(row) for row in rows]


@app.put(
    "/api/printers/{mac}",
    response_model=PrinterOut,
    dependencies=[Security(require_user)],
    tags=["printers"],
    summary="Printerga qulay nom belgilash",
    response_description="Yangilangan (yoki hali mavjud bo'lmasa yangi yaratilgan) reyestr qatori",
    responses=USER_UNAUTHORIZED_RESPONSE,
)
async def set_printer_name(
    mac: str,
    payload: PrinterNameIn,
    session: AsyncSession = Depends(get_session),
) -> PrinterOut:
    """Berilgan MAC uchun qulay nom belgilaydi. Reyestrda bu mac hali bo'lmasa
    (masalan hech qanday chop etish hodisasi kelmagan bo'lsa ham admin oldindan
    nom belgilamoqchi bo'lishi mumkin) — yangi qator yaratiladi. Bo'sh nom
    (`""`) `NULL`ga aylanadi (nomni tozalaydi).
    """
    async with session.begin():
        stmt = pg_insert(Printer).values(mac=mac, name=payload.name)
        stmt = stmt.on_conflict_do_update(
            index_elements=["mac"],
            set_={"name": stmt.excluded.name},
        ).returning(Printer)
        result = await session.execute(stmt)
        saved = result.scalars().all()

    if saved:
        return _printer_out(saved[0])

    # Bazasiz (Fake) testlarda `RETURNING` qator qaytarmaydi — haqiqiy bazada
    # bu yo'lga hech qachon tushilmaydi. Kiritilgan qiymatlardan mos javob quramiz.
    return PrinterOut(
        mac=mac,
        name=payload.name,
        display_name=payload.name or mac,
        last_ip=None,
        last_driver_name=None,
        last_seen=None,
        first_seen=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# AD (Active Directory) sinxronizatsiyasi
# ---------------------------------------------------------------------------


@app.post(
    "/api/ad-sync",
    response_model=EmployeeSyncResult,
    dependencies=[Security(require_api_key)],
    tags=["employees"],
    summary="AD'dan xodimlar ro'yxatini sinxronlash",
    response_description="Qabul qilingan, yozilgan va nofaol qilingan xodimlar soni",
    responses=UNAUTHORIZED_RESPONSE,
)
async def sync_employees(
    batch: EmployeeSyncBatch,
    session: AsyncSession = Depends(get_session),
) -> EmployeeSyncResult:
    """Soatlik AD sinxronizatsiya skripti yuboradigan xodimlar paketini saqlaydi.

    `login` bo'yicha upsert qilinadi, shuning uchun bir xil paketni qayta yuborish
    xavfsiz (idempotent). `mode="full"` bo'lsa, paketda kelmagan (demak AD'dan
    o'chirilgan/ishdan bo'shagan) xodimlar `is_active=false` qilinadi.
    """
    received = len(batch.employees)
    now = datetime.now(timezone.utc)

    # Paket ichida bir login ikki marta kelsa, oxirgisini olamiz.
    rows_by_login: dict[str, dict] = {}
    for emp in batch.employees:
        rows_by_login[emp.login] = {
            "login": emp.login,
            "full_name": emp.full_name,
            "department": emp.department,
            "position": emp.position,
            "is_active": emp.is_active,
            "synced_at": now,
        }
    rows = list(rows_by_login.values())
    upserted = 0
    deactivated = 0

    async with session.begin():
        for start in range(0, len(rows), CHUNK_SIZE):
            chunk = rows[start : start + CHUNK_SIZE]
            stmt = pg_insert(Employee).values(chunk)
            stmt = stmt.on_conflict_do_update(
                index_elements=["login"],
                set_={
                    "full_name": stmt.excluded.full_name,
                    "department": stmt.excluded.department,
                    "position": stmt.excluded.position,
                    "is_active": stmt.excluded.is_active,
                    "synced_at": stmt.excluded.synced_at,
                },
            )
            result = await session.execute(stmt)
            upserted += result.rowcount or 0

        if batch.mode == "full":
            logins = list(rows_by_login.keys())
            deactivate_stmt = update(Employee).where(Employee.is_active.is_(True))
            if logins:
                deactivate_stmt = deactivate_stmt.where(Employee.login.notin_(logins))
            deactivate_result = await session.execute(
                deactivate_stmt.values(is_active=False, synced_at=now)
            )
            deactivated = deactivate_result.rowcount or 0

    logger.info(
        "ad-sync mode=%s received=%d upserted=%d deactivated=%d",
        batch.mode,
        received,
        upserted,
        deactivated,
    )
    return EmployeeSyncResult(
        mode=batch.mode, received=received, upserted=upserted, deactivated=deactivated
    )


@app.get(
    "/api/employees",
    response_model=list[EmployeeOut],
    dependencies=[Security(require_user)],
    tags=["employees"],
    summary="AD'dagi barcha xodimlarni ro'yxatini olish",
    response_description="Xodimlar (faqat chop etganlar emas — kvota belgilash uchun ham kerak)",
    responses=USER_UNAUTHORIZED_RESPONSE,
)
async def list_employees(
    session: AsyncSession = Depends(get_session),
    department: str | None = Query(default=None, description="Bo'lim nomi bo'yicha filtr"),
    is_active: bool | None = Query(default=None, description="Faqat faol/nofaol xodimlar"),
    q: str | None = Query(default=None, description="Login yoki F.I.Sh. bo'yicha qidiruv"),
    limit: int = Query(default=200, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
) -> list[Employee]:
    """Dashboard'ning "Xodimlar" bo'limi uchun — AD'dagi **barcha** xodimlar, chop
    etgan-etmaganidan qat'i nazar. Shu ro'yxatdan hali chop etmagan xodimga ham
    oldindan kvota belgilash mumkin bo'ladi.
    """
    stmt = select(Employee).order_by(Employee.login)

    if department:
        stmt = stmt.where(Employee.department == department)
    if is_active is not None:
        stmt = stmt.where(Employee.is_active.is_(is_active))
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Employee.login.ilike(like), Employee.full_name.ilike(like)))

    stmt = stmt.limit(limit).offset(offset)
    return list((await session.scalars(stmt)).all())


@app.get(
    "/api/ad-sync/status",
    response_model=AdSyncStatusOut,
    dependencies=[Security(require_user)],
    tags=["employees"],
    summary="AD sinxronizatsiyasining so'nggi holati",
    response_description="AD'dan ma'lumot oxirgi marta qachon kelgani va 'eskirgan' (stale) belgisi",
    responses=USER_UNAUTHORIZED_RESPONSE,
)
async def ad_sync_status(session: AsyncSession = Depends(get_session)) -> AdSyncStatusOut:
    """`MAX(employees.synced_at)` — soatlik AD sinxronizatsiya skripti oxirgi marta
    qachon ma'lumot yuborgani (har bir `POST /api/ad-sync` xodimning `synced_at`
    maydonini yangilaydi). Bu vaqt juda eski bo'lsa (yoki umuman xodim bo'lmasa),
    sinxronizatsiya to'xtagan bo'lishi mumkin — dashboard shuni ogohlantiradi.
    """
    last_synced_expr = func.max(Employee.synced_at)
    stale_cutoff = func.now() - literal(timedelta(minutes=settings.ad_sync_stale_minutes))

    stmt = select(
        last_synced_expr.label("last_synced_at"),
        func.count().label("employee_count"),
        func.coalesce(
            func.sum(case((Employee.is_active.is_(True), 1), else_=0)), 0
        ).label("active_count"),
        cast(
            func.floor(func.extract("epoch", func.now() - last_synced_expr) / 60), Integer
        ).label("minutes_since_sync"),
        or_(func.count() == 0, last_synced_expr < stale_cutoff).label("is_stale"),
    )
    row = (await session.execute(stmt)).one()

    # Bazasiz (Fake) testlarda `.one()` har bir ustunga 0 qaytaradi — haqiqiy
    # sana bo'lmasa `None` deb hisoblaymiz (haqiqiy bazada `MAX()` xodim
    # bo'lmaganda allaqachon `NULL` qaytaradi).
    last_synced_at = row.last_synced_at if isinstance(row.last_synced_at, datetime) else None
    minutes_since_sync = (
        int(row.minutes_since_sync)
        if last_synced_at is not None and row.minutes_since_sync is not None
        else None
    )

    return AdSyncStatusOut(
        last_synced_at=last_synced_at,
        employee_count=row.employee_count or 0,
        active_count=row.active_count or 0,
        minutes_since_sync=minutes_since_sync,
        is_stale=bool(row.is_stale),
    )


# ---------------------------------------------------------------------------
# Agent (.exe) sog'lik holati (heartbeat)
# ---------------------------------------------------------------------------


def _agent_stale_cutoff_expr():
    """`now() - AGENT_STALE_MINUTES` ifodasini quradi (SQL tomonda hisoblanadi)."""
    return func.now() - literal(timedelta(minutes=settings.agent_stale_minutes))


@app.post(
    "/api/agent-status",
    response_model=AgentStatusResult,
    dependencies=[Security(require_api_key)],
    tags=["agents"],
    summary="Agentning sog'lik holati haqida signal (heartbeat)",
    response_description="Qabul qilingan kompyuter nomi va holat",
    responses=UNAUTHORIZED_RESPONSE,
)
async def ingest_agent_status(
    payload: AgentStatusIn,
    session: AsyncSession = Depends(get_session),
) -> AgentStatusResult:
    """Har bir ish stantsiyasidan davriy kelib turadigan sog'lik signali.

    `computer` bo'yicha upsert qilinadi — tarix saqlanmaydi, faqat eng so'nggi
    hisobot qoladi. Bir xil signal qayta yuborilsa ham xavfsiz (idempotent).
    """
    row = {
        "computer": payload.computer,
        "username": payload.username,
        "version": payload.version,
        "working": payload.working,
        "detail": payload.detail,
        "boot_time_utc": payload.normalized_boot_time(),
        "uptime_seconds": payload.uptime_seconds,
        "agent_uptime_seconds": payload.agent_uptime_seconds,
        "reported_at": payload.normalized_timestamp(),
    }

    async with session.begin():
        stmt = pg_insert(AgentStatus).values(**row)
        stmt = stmt.on_conflict_do_update(
            index_elements=["computer"],
            set_={
                "username": stmt.excluded.username,
                "version": stmt.excluded.version,
                "working": stmt.excluded.working,
                "detail": stmt.excluded.detail,
                "boot_time_utc": stmt.excluded.boot_time_utc,
                "uptime_seconds": stmt.excluded.uptime_seconds,
                "agent_uptime_seconds": stmt.excluded.agent_uptime_seconds,
                "reported_at": stmt.excluded.reported_at,
                "updated_at": func.now(),
            },
        )
        await session.execute(stmt)

    logger.info(
        "agent-status computer=%s working=%s", payload.computer, payload.working
    )
    return AgentStatusResult(computer=payload.computer, status="ok")


@app.get(
    "/api/agents",
    response_model=list[AgentOut],
    dependencies=[Security(require_user)],
    tags=["agents"],
    summary="Barcha agentlarning so'nggi holati",
    response_description="Har bir kompyuter uchun so'nggi hisobot va 'aloqasi yo'q' (stale) belgisi",
    responses=USER_UNAUTHORIZED_RESPONSE,
)
async def list_agents(
    session: AsyncSession = Depends(get_session),
    working: bool | None = Query(default=None, description="Faqat ishlayotgan/ishlamayotgan agentlar"),
    stale: bool | None = Query(
        default=None, description="Faqat aloqasi yo'q (stale) yoki aloqasi bor agentlar"
    ),
    q: str | None = Query(default=None, description="Kompyuter yoki foydalanuvchi nomi bo'yicha qidiruv"),
) -> list[AgentOut]:
    """Dashboard uchun agentlar ro'yxati. `isStale` va `minutesSinceReport`
    SQL tomonda `AGENT_STALE_MINUTES` sozlamasiga nisbatan hisoblanadi.
    """
    stale_cutoff = _agent_stale_cutoff_expr()
    is_stale_expr = (AgentStatus.reported_at < stale_cutoff).label("is_stale")
    minutes_since_expr = cast(
        func.extract("epoch", func.now() - AgentStatus.reported_at) / 60, Integer
    ).label("minutes_since_report")
    recently_restarted_expr = (
        AgentStatus.agent_uptime_seconds.is_not(None)
        & (AgentStatus.agent_uptime_seconds < settings.agent_recent_restart_seconds)
    ).label("recently_restarted")

    stmt = select(
        AgentStatus.computer,
        AgentStatus.username,
        AgentStatus.version,
        AgentStatus.working,
        AgentStatus.detail,
        AgentStatus.boot_time_utc,
        AgentStatus.uptime_seconds,
        AgentStatus.agent_uptime_seconds,
        AgentStatus.reported_at,
        is_stale_expr,
        minutes_since_expr,
        recently_restarted_expr,
    )

    if working is not None:
        stmt = stmt.where(AgentStatus.working.is_(working))
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(AgentStatus.computer.ilike(like), AgentStatus.username.ilike(like)))
    if stale is True:
        stmt = stmt.where(AgentStatus.reported_at < stale_cutoff)
    elif stale is False:
        stmt = stmt.where(AgentStatus.reported_at >= stale_cutoff)

    # Muammoli (ishlamayotgan) agentlar birinchi, so'ng eng uzoq vaqt aloqasi
    # yo'qlar tepada bo'ladi.
    stmt = stmt.order_by(AgentStatus.working.asc(), AgentStatus.reported_at.asc())

    rows = (await session.execute(stmt)).all()
    return [
        AgentOut(
            computer=row.computer,
            username=row.username,
            version=row.version,
            working=row.working,
            detail=row.detail,
            boot_time_utc=row.boot_time_utc,
            uptime_seconds=row.uptime_seconds,
            agent_uptime_seconds=row.agent_uptime_seconds,
            reported_at=row.reported_at,
            is_stale=bool(row.is_stale),
            minutes_since_report=int(row.minutes_since_report or 0),
            recently_restarted=bool(row.recently_restarted),
        )
        for row in rows
    ]


@app.get(
    "/api/agents/summary",
    response_model=AgentsSummaryOut,
    dependencies=[Security(require_user)],
    tags=["agents"],
    summary="Agentlar bo'yicha umumiy ko'rsatkichlar (KPI kartochkalari uchun)",
    responses=USER_UNAUTHORIZED_RESPONSE,
)
async def agents_summary(session: AsyncSession = Depends(get_session)) -> AgentsSummaryOut:
    stale_cutoff = _agent_stale_cutoff_expr()
    recently_restarted_condition = AgentStatus.agent_uptime_seconds.is_not(None) & (
        AgentStatus.agent_uptime_seconds < settings.agent_recent_restart_seconds
    )
    stmt = select(
        func.count().label("total"),
        func.coalesce(
            func.sum(case((AgentStatus.working.is_(True), 1), else_=0)), 0
        ).label("working"),
        func.coalesce(
            func.sum(case((AgentStatus.working.is_(False), 1), else_=0)), 0
        ).label("not_working"),
        func.coalesce(
            func.sum(case((AgentStatus.reported_at < stale_cutoff, 1), else_=0)), 0
        ).label("stale"),
        func.coalesce(
            func.sum(case((recently_restarted_condition, 1), else_=0)), 0
        ).label("recently_restarted"),
    )
    row = (await session.execute(stmt)).one()
    return AgentsSummaryOut(
        total=row.total or 0,
        working=row.working or 0,
        not_working=row.not_working or 0,
        stale=row.stale or 0,
        recently_restarted=row.recently_restarted or 0,
    )


# ---------------------------------------------------------------------------
# Kvotalar
# ---------------------------------------------------------------------------


@app.get(
    "/api/quotas",
    response_model=list[EmployeeQuotaOut],
    dependencies=[Security(require_user)],
    tags=["quotas"],
    summary="Kvotalarni filtrlab olish",
    responses=USER_UNAUTHORIZED_RESPONSE,
)
async def list_quotas(
    session: AsyncSession = Depends(get_session),
    period_type: PeriodType | None = Query(default=None, description="'month' yoki 'quarter'"),
    year: int | None = Query(default=None, description="Yil"),
    period_no: int | None = Query(default=None, description="Oy yoki chorak raqami"),
    login: str | None = Query(default=None, description="Xodim login'i"),
    department: str | None = Query(default=None, description="Bo'lim nomi bo'yicha filtr"),
) -> list[EmployeeQuota]:
    stmt = select(EmployeeQuota)

    if department:
        stmt = stmt.join(Employee, Employee.login == EmployeeQuota.login).where(
            Employee.department == department
        )
    if period_type:
        stmt = stmt.where(EmployeeQuota.period_type == period_type)
    if year:
        stmt = stmt.where(EmployeeQuota.year == year)
    if period_no:
        stmt = stmt.where(EmployeeQuota.period_no == period_no)
    if login:
        stmt = stmt.where(EmployeeQuota.login == login)

    stmt = stmt.order_by(
        EmployeeQuota.year.desc(), EmployeeQuota.period_no, EmployeeQuota.login
    )
    return list((await session.scalars(stmt)).all())


@app.put(
    "/api/quotas",
    response_model=list[EmployeeQuotaOut],
    dependencies=[Security(require_user)],
    tags=["quotas"],
    summary="Bitta yoki bir nechta kvotani belgilash/yangilash",
    response_description="Yozilgan/yangilangan kvota qatorlari",
    responses=USER_UNAUTHORIZED_RESPONSE,
)
async def upsert_quotas(
    payload: EmployeeQuotaIn | list[EmployeeQuotaIn],
    session: AsyncSession = Depends(get_session),
) -> list[EmployeeQuota]:
    """`(login, period_type, year, period_no)` bo'yicha upsert qiladi.

    Bir xil kvotani qayta yuborish xavfsiz — `allocated_pages` shunchaki yangilanadi.
    """
    items = payload if isinstance(payload, list) else [payload]
    if not items:
        return []

    rows = [
        {
            "login": it.login,
            "period_type": it.period_type,
            "year": it.year,
            "period_no": it.period_no,
            "allocated_pages": it.allocated_pages,
        }
        for it in items
    ]

    saved: list[EmployeeQuota] = []
    async with session.begin():
        for start in range(0, len(rows), CHUNK_SIZE):
            chunk = rows[start : start + CHUNK_SIZE]
            stmt = pg_insert(EmployeeQuota).values(chunk)
            stmt = (
                stmt.on_conflict_do_update(
                    constraint="uq_employee_quotas_period",
                    set_={"allocated_pages": stmt.excluded.allocated_pages},
                )
                .returning(EmployeeQuota)
            )
            result = await session.execute(stmt)
            saved.extend(result.scalars().all())

    return saved


# ---------------------------------------------------------------------------
# Statistika
# ---------------------------------------------------------------------------


@app.get(
    "/api/stats/summary",
    response_model=StatsSummaryOut,
    dependencies=[Security(require_user)],
    tags=["stats"],
    summary="Davr uchun umumiy ko'rsatkichlar",
    responses=USER_UNAUTHORIZED_RESPONSE,
)
async def stats_summary(
    session: AsyncSession = Depends(get_session),
    period: Period = Depends(period_params),
    department: str | None = Query(default=None, description="Bo'lim bo'yicha filtr (Employee jadvali orqali)"),
) -> StatsSummaryOut:
    stmt = select(
        func.coalesce(func.sum(PrintJob.pages), 0).label("total_pages"),
        func.count().label("total_jobs"),
        func.coalesce(
            func.sum(case((PrintJob.success.is_(True), 1), else_=0)), 0
        ).label("success_jobs"),
        func.count(func.distinct(PrintJob.printer)).label("active_printers"),
    ).where(PrintJob.printed_at >= period.start, PrintJob.printed_at < period.end)

    scope = _employee_scope_clause(department)
    if scope is not None:
        stmt = stmt.where(scope)

    row = (await session.execute(stmt)).one()
    total_jobs = row.total_jobs or 0
    success_rate = (row.success_jobs / total_jobs) if total_jobs else 0.0

    return StatsSummaryOut(
        period_type=period.period_type,
        year=period.year,
        period_no=period.period_no,
        total_pages=row.total_pages,
        total_jobs=total_jobs,
        success_rate=round(success_rate, 4),
        active_printers=row.active_printers,
        default_quota=default_quota_for(period.period_type),
    )


@app.get(
    "/api/stats/employees",
    response_model=list[EmployeeStatOut],
    dependencies=[Security(require_user)],
    tags=["stats"],
    summary="Har bir xodimning davrdagi sarfi va kvotasi",
    response_description="Chop etgan har bir login uchun sarf/kvota/qoldiq",
    responses=USER_UNAUTHORIZED_RESPONSE,
)
async def stats_employees(
    session: AsyncSession = Depends(get_session),
    period: Period = Depends(period_params),
    department: str | None = Query(default=None, description="Bo'lim bo'yicha filtr"),
) -> list[EmployeeStatOut]:
    """Dashboard'ning asosiy jadvali: davrda chop etgan har bir foydalanuvchi uchun
    sarflangan sahifalar, unga tegishli kvota va AD holati (faol/nofaol/nomaʼlum).

    AD'da topilmagan (ammo chop etgan) login'lar ham qaytariladi —
    `matchStatus="unmatched"` bilan belgilanadi, tushirib qoldirilmaydi. **Istisno**:
    `department` filtri faol bo'lsa, unmatched login'lar (bo'limi
    yo'qligi sababli) natijadan chiqarib tashlanadi.
    """
    return await _employee_stats_rows(session, period, department)


async def _employee_stats_rows(
    session: AsyncSession, period: Period, department: str | None
) -> list[EmployeeStatOut]:
    """`/api/stats/employees` va CSV eksport uchun umumiy agregatsiya.

    Har bir SQL agregatsiyasi shu yerda bir marta yoziladi — CSV eksport bu
    natijalarni faqat bo'lim bo'yicha guruhlab, boshqacha formatda chiqaradi,
    lekin raqamlar (used/allocated) har doim bir xil manbadan keladi.
    """
    # Bu davr uchun aniq kvota qatori bo'lmagan xodimlarga standart kvota
    # qo'llanadi (0 emas) — pastda `func.coalesce` shuni ta'minlaydi (faqat
    # qator umuman yo'qligida ishga tushadi, saqlangan 0 qiymatga tegmaydi).
    default_allocated = default_quota_for(period.period_type)

    usage = (
        select(
            PrintJob.user_name.label("login"),
            func.coalesce(func.sum(PrintJob.pages), 0).label("used"),
        )
        .where(PrintJob.printed_at >= period.start, PrintJob.printed_at < period.end)
        .group_by(PrintJob.user_name)
        .subquery()
    )

    stmt = (
        select(
            usage.c.login,
            Employee.full_name,
            Employee.department,
            Employee.position,
            Employee.is_active,
            usage.c.used,
            func.coalesce(EmployeeQuota.allocated_pages, default_allocated).label("allocated"),
        )
        .select_from(usage)
        .outerjoin(Employee, Employee.login == usage.c.login)
        .outerjoin(
            EmployeeQuota,
            (EmployeeQuota.login == usage.c.login)
            & (EmployeeQuota.period_type == period.period_type)
            & (EmployeeQuota.year == period.year)
            & (EmployeeQuota.period_no == period.period_no),
        )
    )
    if department:
        stmt = stmt.where(Employee.department == department)
    stmt = stmt.order_by(usage.c.used.desc())

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
        allocated = row.allocated or 0
        results.append(
            EmployeeStatOut(
                login=row.login,
                full_name=row.full_name,
                department=row.department,
                position=row.position,
                used=used,
                allocated=allocated,
                remaining=allocated - used,
                over_limit=used > allocated,
                match_status=match_status,
            )
        )
    return results


UNMATCHED_SECTION_LABEL = "Noma'lum foydalanuvchilar"


@app.get(
    "/api/stats/employees.csv",
    dependencies=[Security(require_user)],
    tags=["stats"],
    summary="Xodimlar sarfi/kvotasini CSV (KPI hisoboti) shaklida eksport qilish",
    response_description="Bo'lim bo'yicha guruhlangan CSV fayl (Excel'da ochiladi)",
    responses=USER_UNAUTHORIZED_RESPONSE,
)
async def stats_employees_csv(
    session: AsyncSession = Depends(get_session),
    period: Period = Depends(period_params),
    department: str | None = Query(default=None, description="Bo'lim bo'yicha filtr"),
) -> Response:
    """Mijoz talab qilgan KPI hisoboti formatida CSV: bo'lim sarlavhasi, so'ng
    har bir xodim uchun T/r, F.I.SH., lavozim, davr kvotasi va sarfi.

    Raqamlar `/api/stats/employees` bilan bir xil SQL agregatsiyasidan olinadi
    (`_employee_stats_rows`) — faqat chiqish formati boshqacha (bo'lim bo'yicha
    guruhlangan jadval, JSON emas). AD'da topilmagan (unmatched) yoki ishdan
    bo'shagan (inactive) login'larning sarfi ham ko'rsatiladi, yashirilmaydi.
    """
    rows = await _employee_stats_rows(session, period, department)

    label = period_label(period.period_type, period.period_no)

    # Bo'lim bo'yicha guruhlash: `department is None` — AD'da umuman topilmagan
    # (unmatched) login'lar, alohida "Noma'lum foydalanuvchilar" bo'limiga tushadi.
    # Ishdan bo'shagan (inactive) xodimlar ham o'z (joriy AD) bo'limida qoladi.
    by_department: dict[str, list[EmployeeStatOut]] = {}
    unmatched: list[EmployeeStatOut] = []
    for row in rows:
        if row.department:
            by_department.setdefault(row.department, []).append(row)
        else:
            unmatched.append(row)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["T/r", "F.I.SH.", "Lavozimi", label, f"Qog'oz sarfi {label}"])

    def _sort_key(row: EmployeeStatOut) -> str:
        return (row.full_name or row.login).lower()

    for dept_name in sorted(by_department):
        writer.writerow([dept_name, "", "", "", ""])
        for idx, row in enumerate(sorted(by_department[dept_name], key=_sort_key), start=1):
            writer.writerow(
                [idx, row.full_name or row.login, row.position or "", row.allocated, row.used]
            )

    if unmatched:
        writer.writerow([UNMATCHED_SECTION_LABEL, "", "", "", ""])
        for idx, row in enumerate(sorted(unmatched, key=_sort_key), start=1):
            writer.writerow(
                [idx, row.full_name or row.login, row.position or "", row.allocated, row.used]
            )

    # Excel'da o'zbekcha (lotin, apostrof bilan) harflar to'g'ri ochilishi uchun
    # UTF-8 BOM qo'shiladi.
    content = "﻿" + buffer.getvalue()

    filename = f"KPI qog'oz sarfi {period.year} {label}.csv"
    ascii_filename = filename.encode("ascii", "ignore").decode("ascii") or "kpi.csv"
    disposition = (
        f'attachment; filename="{ascii_filename}"; '
        f"filename*=UTF-8''{quote(filename)}"
    )

    return Response(
        content=content.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": disposition},
    )


@app.get(
    "/api/stats/timeseries",
    response_model=list[TimeseriesPointOut],
    dependencies=[Security(require_user)],
    tags=["stats"],
    summary="Davr ichida kunlik sahifalar dinamikasi",
    responses=USER_UNAUTHORIZED_RESPONSE,
)
async def stats_timeseries(
    session: AsyncSession = Depends(get_session),
    period: Period = Depends(period_params),
    department: str | None = Query(default=None, description="Bo'lim bo'yicha filtr (Employee jadvali orqali)"),
) -> list[TimeseriesPointOut]:
    # Muhim: `date_trunc` sessiya `TimeZone`siga (masalan Asia/Tashkent) bog'liq bo'lmasligi
    # uchun kun chegarasi aniq UTC bo'yicha hisoblanadi (printed_at UTC sifatida saqlanadi).
    bucket = func.date_trunc("day", PrintJob.printed_at, "UTC").label("bucket")
    stmt = (
        select(
            bucket,
            func.coalesce(func.sum(PrintJob.pages), 0).label("pages"),
            func.count().label("jobs"),
        )
        .where(PrintJob.printed_at >= period.start, PrintJob.printed_at < period.end)
        .group_by(bucket)
        .order_by(bucket)
    )
    scope = _employee_scope_clause(department)
    if scope is not None:
        stmt = stmt.where(scope)

    rows = (await session.execute(stmt)).all()
    return [
        TimeseriesPointOut(date=row.bucket.date().isoformat(), pages=row.pages, jobs=row.jobs)
        for row in rows
    ]


@app.get(
    "/api/stats/top",
    response_model=TopStatsOut,
    dependencies=[Security(require_user)],
    tags=["stats"],
    summary="Eng ko'p sahifa chop etgan printerlar/kompyuterlar/bo'limlar",
    responses=USER_UNAUTHORIZED_RESPONSE,
)
async def stats_top(
    session: AsyncSession = Depends(get_session),
    period: Period = Depends(period_params),
    limit: int = Query(default=10, ge=1, le=100),
    department: str | None = Query(default=None, description="Bo'lim bo'yicha filtr (Employee jadvali orqali)"),
) -> TopStatsOut:
    period_filter = (PrintJob.printed_at >= period.start, PrintJob.printed_at < period.end)
    scope = _employee_scope_clause(department)

    # Printer bo'yicha MAC identifikatoriga qarab guruhlanadi (raw drayver nomi
    # emas) — `_printer_usage_subquery`/`_printer_display_name_expr` orqali
    # `/api/stats/printers` bilan bir xil qoida ishlatiladi.
    printer_filters = list(period_filter)
    if scope is not None:
        printer_filters.append(scope)
    printer_usage = _printer_usage_subquery(*printer_filters)
    printers_stmt = (
        select(
            _printer_display_name_expr(printer_usage).label("name"),
            printer_usage.c.pages,
            printer_usage.c.jobs,
        )
        .select_from(printer_usage)
        .outerjoin(Printer, Printer.mac == printer_usage.c.mac)
        .order_by(printer_usage.c.pages.desc())
        .limit(limit)
    )
    computers_stmt = (
        select(
            PrintJob.computer.label("name"),
            func.coalesce(func.sum(PrintJob.pages), 0).label("pages"),
            func.count().label("jobs"),
        )
        .where(*period_filter)
        .group_by(PrintJob.computer)
        .order_by(func.sum(PrintJob.pages).desc())
        .limit(limit)
    )
    department_label = func.coalesce(Employee.department, "Noma'lum bo'lim").label("name")
    departments_stmt = (
        select(
            department_label,
            func.coalesce(func.sum(PrintJob.pages), 0).label("pages"),
            func.count().label("jobs"),
        )
        .select_from(PrintJob)
        .outerjoin(Employee, Employee.login == PrintJob.user_name)
        .where(*period_filter)
        .group_by(department_label)
        .order_by(func.sum(PrintJob.pages).desc())
        .limit(limit)
    )

    # `printers_stmt` uchun `scope` allaqachon `printer_usage` ichida qo'llangan.
    if scope is not None:
        computers_stmt = computers_stmt.where(scope)
        departments_stmt = departments_stmt.where(scope)

    printers = (await session.execute(printers_stmt)).all()
    computers = (await session.execute(computers_stmt)).all()
    departments = (await session.execute(departments_stmt)).all()

    return TopStatsOut(
        printers=[TopItemOut(name=r.name, pages=r.pages, jobs=r.jobs) for r in printers],
        computers=[TopItemOut(name=r.name, pages=r.pages, jobs=r.jobs) for r in computers],
        departments=[TopItemOut(name=r.name, pages=r.pages, jobs=r.jobs) for r in departments],
    )


@app.get(
    "/api/stats/printers",
    response_model=list[PrinterStatOut],
    dependencies=[Security(require_user)],
    tags=["stats"],
    summary="Har bir printer bo'yicha davr statistikasi",
    response_description="Barcha printerlar (faqat top-N emas), sahifalar bo'yicha kamayish tartibida",
    responses=USER_UNAUTHORIZED_RESPONSE,
)
async def stats_printers(
    session: AsyncSession = Depends(get_session),
    period: Period = Depends(period_params),
) -> list[PrinterStatOut]:
    """`/api/stats/top`dagi "eng ko'p N ta printer"dan farqli o'laroq, davrda
    ishlatilgan **barcha** printerlarni (muvaffaqiyat foizi va xatolar soni bilan
    birga) qaytaradi — printerlar sahifasi uchun.

    Guruhlash `printer_mac` bo'yicha (mac bo'lmasa xom printer nomi bo'yicha)
    amalga oshiriladi — bir xil jismoniy printer turli kompyuterlarda turlicha
    drayver nomi bilan ko'ringan bo'lsa ham bitta qatorga birlashadi. Nom —
    reyestrdagi qulay nom (agar admin belgilagan bo'lsa), aks holda so'nggi
    ko'rilgan drayver nomi, aks holda hodisadagi xom nom, aks holda mac.
    """
    usage = _printer_usage_subquery(
        PrintJob.printed_at >= period.start, PrintJob.printed_at < period.end
    )
    stmt = (
        select(
            usage.c.mac,
            _printer_display_name_expr(usage).label("name"),
            usage.c.pages,
            usage.c.jobs,
            usage.c.success_jobs,
            usage.c.failed_jobs,
            func.coalesce(Printer.last_ip, usage.c.printer_ip).label("last_ip"),
        )
        .select_from(usage)
        .outerjoin(Printer, Printer.mac == usage.c.mac)
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
                mac=row.mac,
                name=row.name,
                pages=row.pages,
                jobs=jobs,
                success_rate=round(success_rate, 4),
                failed_jobs=row.failed_jobs or 0,
                last_ip=row.last_ip,
            )
        )
    return results


@app.get(
    "/api/stats/failures",
    response_model=list[FailureReasonOut],
    dependencies=[Security(require_user)],
    tags=["stats"],
    summary="Muvaffaqiyatsiz chop etishlar sabab bo'yicha",
    responses=USER_UNAUTHORIZED_RESPONSE,
)
async def stats_failures(
    session: AsyncSession = Depends(get_session),
    period: Period = Depends(period_params),
    department: str | None = Query(default=None, description="Bo'lim bo'yicha filtr (Employee jadvali orqali)"),
) -> list[FailureReasonOut]:
    reason_label = func.coalesce(PrintJob.reason, "Sabab ko'rsatilmagan").label("reason")
    stmt = (
        select(reason_label, func.count().label("count"))
        .where(
            PrintJob.printed_at >= period.start,
            PrintJob.printed_at < period.end,
            PrintJob.success.is_(False),
        )
        .group_by(reason_label)
        .order_by(func.count().desc())
    )
    scope = _employee_scope_clause(department)
    if scope is not None:
        stmt = stmt.where(scope)

    rows = (await session.execute(stmt)).all()
    return [FailureReasonOut(reason=row.reason, count=row.count) for row in rows]


@app.get(
    "/api/stats/departments",
    response_model=list[DepartmentRollupOut],
    dependencies=[Security(require_user)],
    tags=["stats"],
    summary="Bo'lim kesimida davr yig'indisi",
    response_description="Har bir bo'lim uchun: sahifalar, ishlar, xodimlar soni, kvota yig'indisi",
    responses=USER_UNAUTHORIZED_RESPONSE,
)
async def stats_departments(
    session: AsyncSession = Depends(get_session),
    period: Period = Depends(period_params),
) -> list[DepartmentRollupOut]:
    """Ko'chirish (transfer) hisobotlari uchun: har bir bo'lim bo'yicha
    davrdagi sarf **joriy** AD tuzilishi bo'yicha hisoblanadi (so'rov vaqtida
    `Employee.department`ga qo'shiladi — tarixiy emas).

    Faqat chop etganlar emas — **barcha faol xodimlar** hisobga olinadi
    (`employeeCount`, `totalAllocated` shu tarzda to'g'ri chiqadi).
    """
    return await _department_rollup(session, period)


async def _department_rollup(session: AsyncSession, period: Period) -> list[DepartmentRollupOut]:
    """`Employee.department` bo'yicha davr uchun to'liq agregatsiya: sahifalar/ishlar
    (chop etilgan), faol xodimlar soni va kvotalar yig'indisi. Barcha agregatsiya
    SQL tomonda amalga oshiriladi.
    """
    column = Employee.department
    names = select(column.label("name")).where(column.isnot(None)).distinct().subquery()

    employee_counts = (
        select(column.label("name"), func.count().label("employee_count"))
        .where(column.isnot(None), Employee.is_active.is_(True))
        .group_by(column)
        .subquery()
    )

    # Har bir faol xodim uchun shu davrga aniq kvota qatori bo'lmasa, standart
    # kvota qo'llanadi (0 emas) — shuning uchun `Employee`dan boshlab
    # `EmployeeQuota`ga outer join qilinadi (aksincha bo'lsa, kvota qatori
    # yo'q xodimlar yig'indiga umuman kirmay qolar edi).
    default_allocated = default_quota_for(period.period_type)
    per_employee_quota = (
        select(
            column.label("name"),
            func.coalesce(EmployeeQuota.allocated_pages, default_allocated).label("allocated"),
        )
        .select_from(Employee)
        .outerjoin(
            EmployeeQuota,
            (EmployeeQuota.login == Employee.login)
            & (EmployeeQuota.period_type == period.period_type)
            & (EmployeeQuota.year == period.year)
            & (EmployeeQuota.period_no == period.period_no),
        )
        .where(column.isnot(None), Employee.is_active.is_(True))
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
            column.label("name"),
            func.coalesce(func.sum(PrintJob.pages), 0).label("pages"),
            func.count().label("jobs"),
        )
        .select_from(PrintJob)
        .join(Employee, Employee.login == PrintJob.user_name)
        .where(
            column.isnot(None),
            PrintJob.printed_at >= period.start,
            PrintJob.printed_at < period.end,
        )
        .group_by(column)
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
