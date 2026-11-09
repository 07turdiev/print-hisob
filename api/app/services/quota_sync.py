r"""Agent bilan kvota almashinuvi (`POST /api/print-quotas`).

Vazifa taqsimoti (agent hujjatidan): **raqamni server biladi** — odam bir necha
kompyuterdan chop etadi va umumiy summani faqat markaz ko'ra oladi; **qarorni
agent qabul qiladi** — ish navbatga tushgan va printer qog'ozni tortgan payt
orasidagi millisekundlarda hal qilish kerak. Shuning uchun bitta POST ikkala
ishni bajaradi: agent sarfni bildiradi, server javobida limitlarni qaytaradi.

**Kvota endi hech kimni to'smaydi.** U faqat hisobot normasi (dashboardda
"limitdan oshgan" deb ko'rsatiladi). Chop etishni to'sish faqat adminning aniq
qarori bilan bo'ladi: `print_user_overrides.blocked` belgilangan loginga
`limit: 0` yuboriladi, qolgan hammaga `-1` (cheklovsiz). Avval kvotadan oshish
avtomatik to'sardi va odamlar sababini bilmay qolardi.

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
from app.logins import login_key, normalize_login
from app.models import AgentQuotaState, PrintJob
from app.periods import Period, PeriodType, current_period, period_key
from app.rules import counted_job
from app.services import printer_groups, user_overrides
from app.schemas import QuotaLimitOut, QuotaSyncIn, QuotaSyncOut

# Bitta INSERT'dagi qatorlar soni (Postgres parametr chegarasi uchun).
CHUNK_SIZE = 500

# Agent hujjatidagi maxsus qiymatlar.
UNLIMITED = -1  # aniq cheklovsiz (mahalliy chegara ham qo'llanmaydi)
BLOCKED = 0  # umuman chop eta olmaydi


def _normalized_login_expr():
    r"""SQL tomonda `MADANIYAT\E.Turdiyev` -> `e.turdiyev`.

    `app.logins.normalize_login` bilan bir xil qoida: oxirgi `\` gacha bo'lgan
    qism olib tashlanadi va natija kichik harfga o'tkaziladi.
    """
    return login_key(PrintJob.user_name)


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
    qo'shimcha bo'lish/yaxlitlash qilinmaydi. Virtual printerlar hisoblanmaydi,
    aks holda agentdagi raqam dashboarddagi sarfdan farq qilardi.
    """
    login = _normalized_login_expr().label("login")
    stmt = (
        select(login, func.coalesce(func.sum(PrintJob.pages), 0).label("used"))
        .where(
            PrintJob.printed_at >= period.start,
            PrintJob.printed_at < period.end,
            counted_job(),
        )
        .group_by(login)
    )
    rows = (await session.execute(stmt)).all()
    return {row.login: int(row.used or 0) for row in rows}


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
    # Kalit normallashtirilgan login: bitta odam so'rovda ikki xil yozilishi mumkin
    # (`MADANIYAT\x` va `x`), bitta INSERT'da takrorlansa `ON CONFLICT` yiqiladi.
    rows_by_login: dict[str, dict] = {}
    for item in payload.users:
        login = normalize_login(item.user)
        if not login:
            continue
        answer = served.get(login)
        rows_by_login[login] = {
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

    rows = list(rows_by_login.values())
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


def _allowed_for(
    login: str,
    policies: dict[str, printer_groups.LoginPolicy],
    *,
    blocked: bool,
    default: list[str],
) -> list[str]:
    """Shu login uchun ruxsat etilgan printerlar ro'yxati.

    Guruhsiz xodim `default` ni oladi (standart qoida), guruh esa istisno.
    Har doim ochiq-oydin qiymat qaytariladi, hatto cheklov bo'lmaganda ham
    (`["*"]`). Sababi `limit` bilan bir xil: agent javobni keshlaydi, shuning
    uchun "cheklov olindi" xabari ro'yxatdan yo'qolish orqali emas, aniq qiymat
    orqali yetkazilishi kerak. Aks holda guruhdan chiqarilgan xodim eski
    cheklov bilan qolib ketardi.
    """
    if blocked:
        return []

    policy = policies.get(login)
    if policy is None:
        return list(default)
    if policy.policy == printer_groups.ALL:
        return [printer_groups.ANY_PRINTER]
    if policy.policy == printer_groups.ALLOWED:
        return list(policy.tokens)
    return []


async def sync_quotas(session: AsyncSession, payload: QuotaSyncIn) -> QuotaSyncOut:
    """Agent hisobotini qabul qilib, joriy holatni qaytaradi.

    Javobga ikki guruh foydalanuvchi kiradi:

    1. agent so'ragan foydalanuvchilar — ularga `limit: -1` (cheklovsiz) va
       ma'lumot uchun haqiqiy sarf (`used`);
    2. **admin tegib o'tgan barcha loginlar** — bloklanganlarga `0`,
       blokdan chiqarilganlarga ochiq-oydin `-1`.

    Ikkinchi guruhga bloklanmaganlar ham kirishi muhim: agent javobni keshlaydi,
    shuning uchun "cheklov olindi" degan xabar ro'yxatdan yo'qolish orqali emas,
    aniq `-1` qiymati orqali yetkaziladi.

    Kvota bu yerda umuman qatnashmaydi: u faqat hisobot normasi. Chop etishni
    to'sish xodim ustidagi "Bloklash" tugmasi bilan bo'ladi (`limit: 0`).

    `allowedPrinters` esa yangi: u faqat `allowedPrinters` ni biladigan agentda
    kuchga kiradi. Eski agentlar notanish maydonni e'tiborsiz qoldiradi.
    Standart ro'yxat javobning yuqori qismida bir marta boradi. Bu agent
    so'ramagan login uchun u takrorlanmaydi, aks holda har bir javob admin
    tegib o'tgan loginlar soniga ko'paygan bo'lardi.
    """
    period = current_period(agent_period_type())
    key = period_key(period.period_type, period.year, period.period_no)

    report_used = settings.agent_quota_report_used
    usage = await _usage_by_login(session, period) if report_used else {}
    known = await user_overrides.known_login_states(session)
    access = await printer_groups.default_access(session)
    default_allowed = access.allowed_printers()
    policies = await printer_groups.policy_by_login(session, public_tokens=access.tokens)

    # Agent so'raganlar + admin tegib o'tgan barcha loginlar. Ikkinchisi faqat
    # bloklanganlar emas: blokdan chiqarilganga ham ochiq-oydin `-1` yuborilishi
    # kerak, aks holda agent eski keshlangan `0` ni saqlab qolishi mumkin.
    requested = {normalize_login(item.user): item.user for item in payload.users}
    requested.pop("", None)
    logins = dict(requested)
    for login in known:
        logins.setdefault(login, login)
    # Guruh a'zolari ham qo'shiladi: agent ularni so'ramagan bo'lsa ham
    # cheklov yetib borishi kerak.
    for login in policies:
        logins.setdefault(login, login)

    users: list[QuotaLimitOut] = []
    served: dict[str, QuotaLimitOut] = {}
    for login, display_name in sorted(logins.items()):
        blocked = bool(known.get(login))
        allowed = _allowed_for(login, policies, blocked=blocked, default=default_allowed)
        answer = QuotaLimitOut(
            # Agent nomlarni registrga sezgir bo'lmagan holda solishtiradi, shuning
            # uchun u yuborgan shaklni o'zgartirmasdan qaytaramiz.
            user=display_name,
            limit=BLOCKED if blocked else UNLIMITED,
            used=usage.get(login, 0) if report_used else None,
            allowed_printers=None
            if login not in requested and allowed == default_allowed
            else allowed,
        )
        users.append(answer)
        served[login] = answer

    await _save_state(session, payload, key, served, payload.normalized_timestamp())

    return QuotaSyncOut(
        period_key=key,
        # Ro'yxatda yo'q har kim cheklovsiz — kvotadan oshish hech kimni to'smaydi.
        default_limit=UNLIMITED,
        allowed_printers=default_allowed,
        users=users,
    )
