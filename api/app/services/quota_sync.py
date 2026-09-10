r"""Agent bilan kvota almashinuvi (`POST /api/print-quotas`).

Vazifa taqsimoti (agent hujjatidan): **raqamni server biladi** — odam bir necha
kompyuterdan chop etadi va umumiy summani faqat markaz ko'ra oladi; **qarorni
agent qabul qiladi** — ish navbatga tushgan va printer qog'ozni tortgan payt
orasidagi millisekundlarda hal qilish kerak. Shuning uchun bitta POST ikkala
ishni bajaradi: agent sarfni bildiradi, server javobida limitlarni qaytaradi.

Javobdagi uch qiymatning ma'nosi bir xil emas (hujjatdagi "Uch nozik qoida"):

* `limit` umuman yuborilmasa (yoki `null`) — "menda fikr yo'q", agent
  `defaultLimit`ga, undan keyin o'zining mahalliy sozlamasiga tushadi;
* `-1` — aniq cheklovsiz, mahalliy chegara ham qo'llanmaydi;
* `0` — so'zma-so'z: bu odam umuman chop eta olmaydi.

`periodKey` — "yopishqoq" qaror: server bir marta yuborsa, jadval butunlay
serverga o'tadi va uning o'zgarishi agentdagi hisoblagichlarni nolga tushiradi.
Shuning uchun u `app.periods.period_key` orqali barqaror shaklda hosil qilinadi.
"""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.logins import SQL_DOMAIN_PREFIX_PATTERN, normalize_login
from app.models import AgentQuotaState, EmployeeQuota, PrintJob
from app.periods import Period, PeriodType, current_period, default_quota_for, period_key
from app.schemas import QuotaLimitOut, QuotaSyncIn, QuotaSyncOut

# Bitta INSERT'dagi qatorlar soni (Postgres parametr chegarasi uchun).
CHUNK_SIZE = 500


def _normalized_login_expr():
    r"""SQL tomonda `MADANIYAT\E.Turdiyev` -> `e.turdiyev`.

    `app.logins.normalize_login` bilan bir xil qoida: oxirgi `\` gacha bo'lgan
    qism olib tashlanadi va natija kichik harfga o'tkaziladi.
    """
    return func.lower(func.regexp_replace(PrintJob.user_name, SQL_DOMAIN_PREFIX_PATTERN, ""))


def agent_period_type() -> PeriodType:
    """Agentga qaysi davr yuborilishi (`AGENT_QUOTA_PERIOD_TYPE` sozlamasidan).

    Agent bir vaqtda faqat bitta davr bo'yicha hisoblay oladi, dashboardda esa
    ikkitasi (oylik va choraklik) bor — shuning uchun tanlov sozlamada.
    """
    return "month" if settings.agent_quota_period_type == "month" else "quarter"


async def _usage_by_login(session: AsyncSession, period: Period) -> dict[str, int]:
    """Davr ichida har bir (normallashtirilgan) login sarflagan varaqlar soni.

    Sarf har doim `SUM(pages)` — `pages` allaqachon jismoniy varaq soni
    (agent duplex hisobini o'zi qilib yuboradi), shuning uchun serverda
    qo'shimcha bo'lish/yaxlitlash qilinmaydi.
    """
    login = _normalized_login_expr().label("login")
    stmt = (
        select(login, func.coalesce(func.sum(PrintJob.pages), 0).label("used"))
        .where(PrintJob.printed_at >= period.start, PrintJob.printed_at < period.end)
        .group_by(login)
    )
    rows = (await session.execute(stmt)).all()
    return {row.login: int(row.used or 0) for row in rows}


async def _explicit_limits(session: AsyncSession, period: Period) -> dict[str, int]:
    """Shu davr uchun dashboardda **aniq belgilangan** kvotalar.

    Bu yerda faqat haqiqiy qatorlar bo'ladi — kvotasi belgilanmagan xodimlar
    javobda `limit=null` bilan ketadi va agent `defaultLimit`ni qo'llaydi.
    Saqlangan `0` esa so'zma-so'z 0 bo'lib qoladi (standart bilan almashtirilmaydi).
    """
    stmt = select(EmployeeQuota.login, EmployeeQuota.allocated_pages).where(
        EmployeeQuota.period_type == period.period_type,
        EmployeeQuota.year == period.year,
        EmployeeQuota.period_no == period.period_no,
    )
    rows = (await session.execute(stmt)).all()
    return {normalize_login(row.login): int(row.allocated_pages) for row in rows}


async def _save_state(
    session: AsyncSession,
    payload: QuotaSyncIn,
    key: str,
    served: dict[str, QuotaLimitOut],
    reported_at: datetime,
) -> None:
    """Agentning so'nggi holatini `(kompyuter, login, davr)` bo'yicha upsert qiladi.

    Tarix yig'ilmaydi (agent har 5 daqiqada signal yuboradi) — `AgentStatus`
    bilan bir xil yondashuv. Bizning javobimiz ham yoziladi, shunda keyingi
    so'rovda agent uni qo'llaganini (yoki qo'llamaganini) ko'rish mumkin.
    """
    rows = []
    for item in payload.users:
        login = normalize_login(item.user)
        if not login:
            continue
        answer = served.get(login)
        rows.append(
            {
                "computer": payload.computer,
                "login": login,
                "raw_user": item.user,
                "period_key": key,
                "pages_used_here": item.pages_used_here,
                "pages_used_reported": item.pages_used,
                "applied_limit": item.limit,
                "served_limit": answer.limit if answer else None,
                "served_used": answer.used if answer else None,
                "reported_at": reported_at,
            }
        )

    if not rows:
        return

    # `session.begin()` bu yerda ISHLATILMAYDI: limitlarni hisoblash uchun avval
    # SELECT bajarilgan va sessiyada tranzaksiya allaqachon ochilgan bo'ladi
    # ("A transaction is already begun on this Session"). O'qish va yozish bitta
    # implicit tranzaksiyada boradi, oxirida `commit()` bilan yopiladi.
    for start in range(0, len(rows), CHUNK_SIZE):
        chunk = rows[start : start + CHUNK_SIZE]
        stmt = pg_insert(AgentQuotaState).values(chunk)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_agent_quota_state_computer_login_period",
            set_={
                "raw_user": stmt.excluded.raw_user,
                "pages_used_here": stmt.excluded.pages_used_here,
                "pages_used_reported": stmt.excluded.pages_used_reported,
                "applied_limit": stmt.excluded.applied_limit,
                "served_limit": stmt.excluded.served_limit,
                "served_used": stmt.excluded.served_used,
                "reported_at": stmt.excluded.reported_at,
                "updated_at": func.now(),
            },
        )
        await session.execute(stmt)
    await session.commit()


async def sync_quotas(session: AsyncSession, payload: QuotaSyncIn) -> QuotaSyncOut:
    """Agent hisobotini qabul qilib, joriy davr limitlarini qaytaradi.

    Javobga ikki guruh foydalanuvchi kiradi:

    1. agent so'ragan foydalanuvchilar — ular uchun `used` (haqiqiy, flot
       bo'yicha) va aniq kvota bo'lsa `limit`;
    2. shu davrga dashboardda **aniq kvota belgilangan** barcha xodimlar — agent
       ularni oldindan keshlab qo'ysin, shunda o'sha odam birinchi marta shu
       mashinada chop etganda ham to'g'ri limit qo'llanadi.
    """
    period = current_period(agent_period_type())
    key = period_key(period.period_type, period.year, period.period_no)

    usage = await _usage_by_login(session, period)
    limits = await _explicit_limits(session, period)

    # Agent so'raganlar + kvotasi aniq belgilanganlar.
    requested = {normalize_login(item.user): item.user for item in payload.users}
    requested.pop("", None)
    logins = dict(requested)
    for login in limits:
        logins.setdefault(login, login)

    users: list[QuotaLimitOut] = []
    served: dict[str, QuotaLimitOut] = {}
    for login, display_name in sorted(logins.items()):
        answer = QuotaLimitOut(
            # Agent nomlarni registrga sezgir bo'lmagan holda solishtiradi, shuning
            # uchun u yuborgan shaklni o'zgartirmasdan qaytaramiz.
            user=display_name,
            limit=limits.get(login),
            used=usage.get(login, 0) if settings.agent_quota_report_used else None,
        )
        users.append(answer)
        served[login] = answer

    await _save_state(session, payload, key, served, payload.normalized_timestamp())

    return QuotaSyncOut(
        period_key=key,
        default_limit=default_quota_for(period.period_type),
        users=users,
    )
