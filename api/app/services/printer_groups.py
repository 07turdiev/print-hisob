r"""Standart printer qoidasi, istisno guruhlari va printer ruxsatlari.

**Standart qoida.** Admin "umumiy printerlar" ro'yxatini tuzadi va cheklovni
yoqadi. Shundan keyin guruhga kirmagan xodim faqat shu printerlardan chiqaradi.
Cheklov o'chiq turganda hamma avvalgidek ishlaydi.

**Guruh — istisno.** Guruh bitta siyosatga ega bo'ladi:

* `all` — barcha printerlar;
* `allowed` — umumiy printerlar va guruhda belgilangan qurilmalar;
* `none` — umuman chop eta olmaydi.

**Nega shunday taqsimlangan.** `none` yangi mexanizm talab qilmaydi: agentga
mavjud `limit: 0` orqali yetadi, ya'ni bu bugun ishlab turgan "Bloklash" bilan
bir xil kanal. Printer ro'yxati bo'yicha cheklov esa agentdagi `allowedPrinters`
qo'llanmasi chiqqandan keyin kuchga kiradi — shu vaqtgacha u faqat hisobotda
ko'rinadi ("ruxsat etilmagan printerdan chiqardi").

**Bir xodim — bitta guruh.** Cheklov baza darajasida (`uq_printer_group_members_login`).
Aks holda "bu odamga nima ruxsat etilgan" degan savolga javob guruhlarni
qo'shish qoidasiga bog'liq bo'lib qolardi va sabab topish qiyinlashardi.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.logins import SQL_DOMAIN_PREFIX_PATTERN, normalize_login
from app.models import (
    Employee,
    PrinterAccessSetting,
    PrinterAlias,
    PrinterDevice,
    PrinterGroup,
    PrinterGroupMember,
    PrinterGroupPrinter,
    PrintJob,
    PublicPrinter,
)
from app.services import printers

logger = logging.getLogger(__name__)

# `status.HTTP_422_UNPROCESSABLE_ENTITY` starlette'da eskirgan; `main.py` dagi
# konventsiya bilan bir xil — sonni to'g'ridan-to'g'ri ishlatamiz.
_UNPROCESSABLE = 422

ALL = "all"
ALLOWED = "allowed"
NONE = "none"
POLICIES = (ALL, ALLOWED, NONE)

# Hisobotda guruhsiz xodimning siyosati. Guruhga berib bo'lmaydi.
DEFAULT = "default"
NO_GROUP_LABEL = "Guruhsiz"

# Agent shartnomasidagi "barcha printerlar" belgisi.
ANY_PRINTER = "*"

# `printer_access_settings` jadvalidagi yagona qator.
_SETTINGS_ID = 1


@dataclass(frozen=True)
class DefaultAccess:
    """Standart qoida: cheklov holati va umumiy printerlar."""

    restrict: bool
    device_ids: tuple[int, ...]
    tokens: tuple[str, ...]

    def allowed_printers(self) -> list[str]:
        """Guruhsiz xodimga yuboriladigan ro'yxat.

        Cheklov yoqilgan-u nishon topilmasa `["*"]` qaytadi: server tomonidagi
        ma'lumot xatosi butun idorani chop etishdan to'xtatib qo'ymasligi kerak.
        """
        if self.restrict and self.tokens:
            return list(self.tokens)
        return [ANY_PRINTER]


@dataclass(frozen=True)
class GroupRow:
    """Ro'yxat uchun guruh: siyosati, qurilmalari va a'zolari."""

    group: PrinterGroup
    device_ids: list[int]
    logins: list[str]


@dataclass(frozen=True)
class LoginPolicy:
    """Bitta login uchun hal qilingan siyosat.

    `tokens` — agentga yuboriladigan nishonlar (MAC, IP, drayver nomlari).
    `policy='allowed'` bo'lmasa bo'sh bo'ladi.
    """

    group_id: int
    group_name: str
    policy: str
    tokens: tuple[str, ...]


def _validate_policy(policy: str) -> str:
    if policy not in POLICIES:
        raise HTTPException(
            _UNPROCESSABLE,
            detail=f"Siyosat faqat shulardan biri bo'lishi mumkin: {', '.join(POLICIES)}",
        )
    return policy


def _clean_name(name: str) -> str:
    cleaned = (name or "").strip()
    if not cleaned:
        raise HTTPException(_UNPROCESSABLE, detail="Guruh nomi bo'sh")
    return cleaned


async def _require_group(session: AsyncSession, group_id: int) -> PrinterGroup:
    group = await session.get(PrinterGroup, group_id)
    if group is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Guruh topilmadi")
    return group


async def _check_name_free(session: AsyncSession, name: str, *, except_id: int | None) -> None:
    stmt = select(PrinterGroup.id).where(func.lower(PrinterGroup.name) == name.lower())
    if except_id is not None:
        stmt = stmt.where(PrinterGroup.id != except_id)
    if await session.scalar(stmt) is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail=f"«{name}» nomli guruh allaqachon bor"
        )


async def _check_devices_exist(session: AsyncSession, device_ids: list[int]) -> None:
    if not device_ids:
        return
    found = set(
        (await session.execute(select(PrinterDevice.id).where(PrinterDevice.id.in_(device_ids))))
        .scalars()
        .all()
    )
    missing = sorted(set(device_ids) - found)
    if missing:
        raise HTTPException(
            _UNPROCESSABLE,
            detail=f"Reyestrda bunday printer yo'q: {', '.join(map(str, missing))}",
        )


async def _check_logins_free(
    session: AsyncSession, logins: list[str], *, group_id: int
) -> None:
    """Bir xodim ikki guruhda bo'lmasligini oldindan, tushunarli xato bilan tekshiradi.

    Baza `uq_printer_group_members_login` bilan ham to'xtatadi, lekin u xatoni
    adminga tushunarsiz ko'rinishda qaytaradi va qaysi odam sabab bo'lganini
    aytmaydi.
    """
    if not logins:
        return
    rows = (
        await session.execute(
            select(PrinterGroupMember.login, PrinterGroup.name)
            .join(PrinterGroup, PrinterGroup.id == PrinterGroupMember.group_id)
            .where(
                PrinterGroupMember.login.in_(logins),
                PrinterGroupMember.group_id != group_id,
            )
        )
    ).all()
    if rows:
        taken = ", ".join(f"{login} («{group}» guruhida)" for login, group in rows)
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Bu xodimlar boshqa guruhda: {taken}. Avval u guruhdan chiqaring.",
        )


# ---------------------------------------------------------------------------
# O'qish
# ---------------------------------------------------------------------------


async def list_groups(session: AsyncSession) -> list[GroupRow]:
    """Barcha guruhlar, qurilmalari va a'zolari bilan."""
    groups = (
        (await session.execute(select(PrinterGroup).order_by(PrinterGroup.name))).scalars().all()
    )
    printers = (await session.execute(select(PrinterGroupPrinter))).scalars().all()
    members = (await session.execute(select(PrinterGroupMember))).scalars().all()

    devices_by_group: dict[int, list[int]] = {}
    for row in printers:
        devices_by_group.setdefault(row.group_id, []).append(row.device_id)
    logins_by_group: dict[int, list[str]] = {}
    for row in members:
        logins_by_group.setdefault(row.group_id, []).append(row.login)

    return [
        GroupRow(
            group=g,
            device_ids=sorted(devices_by_group.get(g.id, [])),
            logins=sorted(logins_by_group.get(g.id, [])),
        )
        for g in groups
    ]


def device_tokens(aliases: Iterable[tuple[str, str]], last_ip: str | None) -> list[str]:
    """Bitta qurilma uchun agentga yuboriladigan nishonlar.

    `aliases` — `(kind, value)` juftliklari. Hamma nishon yuborilmaydi:

    * MAC'lar yuboriladi. Birlashtirishdan keyin ular orasida eski yoki soxta
      MAC bo'lishi mumkin, lekin ular boshqa printerga tegishli emas.
    * IP faqat joriysi (`last_ip`). Eski IP'ni keyin boshqa printer olgan
      bo'lishi mumkin va u ham ruxsat olib qolardi. Joriy IP noma'lum bo'lsagina
      barcha IP nishonlari ishlatiladi.
    * Nom faqat MAC ham, IP ham bo'lmaganda (USB va virtual printerlar). Nom
      ishonchsiz: bir xil nom turli printerlarda uchraydi.
    """
    pairs = list(aliases)
    macs = [value for kind, value in pairs if kind == printers.MAC]
    ips = [value for kind, value in pairs if kind == printers.IP]
    names = [value for kind, value in pairs if kind == printers.NAME]

    current_ips = [last_ip] if last_ip and printers.is_ip(last_ip) else ips
    return (macs + current_ips) or names


async def _tokens_by_device(
    session: AsyncSession, device_ids: list[int]
) -> dict[int, tuple[str, ...]]:
    """Berilgan qurilmalarning agentga yuboriladigan nishonlari."""
    if not device_ids:
        return {}

    alias_rows = (
        await session.execute(
            select(PrinterAlias.device_id, PrinterAlias.kind, PrinterAlias.value)
            .where(PrinterAlias.device_id.in_(device_ids))
            .order_by(PrinterAlias.device_id, PrinterAlias.kind, PrinterAlias.value)
        )
    ).all()
    ip_rows = (
        await session.execute(
            select(PrinterDevice.id, PrinterDevice.last_ip).where(PrinterDevice.id.in_(device_ids))
        )
    ).all()
    last_ip = {device_id: ip for device_id, ip in ip_rows}

    aliases: dict[int, list[tuple[str, str]]] = {}
    for device_id, kind, value in alias_rows:
        aliases.setdefault(device_id, []).append((kind, value))
    return {
        device_id: tuple(device_tokens(pairs, last_ip.get(device_id)))
        for device_id, pairs in aliases.items()
    }


async def _tokens_by_group(session: AsyncSession) -> dict[int, tuple[str, ...]]:
    """Har bir guruhning o'z qurilmalari uchun nishonlar ro'yxati."""
    pairs = [
        (group_id, device_id)
        for group_id, device_id in (
            await session.execute(
                select(PrinterGroupPrinter.group_id, PrinterGroupPrinter.device_id).order_by(
                    PrinterGroupPrinter.group_id, PrinterGroupPrinter.device_id
                )
            )
        ).all()
    ]
    tokens = await _tokens_by_device(session, sorted({device_id for _, device_id in pairs}))

    by_group: dict[int, list[str]] = {}
    for group_id, device_id in pairs:
        by_group.setdefault(group_id, []).extend(tokens.get(device_id, ()))
    return {gid: tuple(dict.fromkeys(values)) for gid, values in by_group.items()}


async def public_device_ids(session: AsyncSession) -> list[int]:
    """Umumiy printerlar ro'yxati."""
    rows = (
        await session.execute(select(PublicPrinter.device_id).order_by(PublicPrinter.device_id))
    ).scalars()
    return [int(device_id) for device_id in rows.all()]


async def default_access(session: AsyncSession) -> DefaultAccess:
    """Standart qoidani o'qiydi: cheklov holati, umumiy printerlar va nishonlari."""
    setting = await session.get(PrinterAccessSetting, _SETTINGS_ID)
    device_ids = await public_device_ids(session)
    by_device = await _tokens_by_device(session, device_ids)
    tokens = tuple(
        dict.fromkeys(token for device_id in device_ids for token in by_device.get(device_id, ()))
    )
    restrict = bool(setting and setting.restrict_default)
    if restrict and not tokens:
        logger.warning("printer cheklovi yoqilgan, lekin umumiy printer nishonlari topilmadi")
    return DefaultAccess(restrict=restrict, device_ids=tuple(device_ids), tokens=tokens)


async def update_access(
    session: AsyncSession,
    *,
    restrict_default: bool | None = None,
    device_ids: list[int] | None = None,
) -> DefaultAccess:
    """Standart qoidani qisman yangilaydi. `device_ids` ro'yxatni butunlay almashtiradi.

    Umumiy printer belgilanmagan holda cheklovni yoqib bo'lmaydi: bu hammani
    bir zumda to'xtatib qo'ygan bo'lardi.
    """
    setting = await session.get(PrinterAccessSetting, _SETTINGS_ID)
    next_ids = (
        sorted(dict.fromkeys(device_ids))
        if device_ids is not None
        else await public_device_ids(session)
    )
    next_restrict = (
        restrict_default
        if restrict_default is not None
        else bool(setting and setting.restrict_default)
    )

    if next_restrict and not next_ids:
        raise HTTPException(
            _UNPROCESSABLE,
            detail="Avval umumiy printerlarni belgilang, aks holda hech kim chop eta olmaydi",
        )

    if device_ids is not None:
        await _check_devices_exist(session, next_ids)
        await session.execute(delete(PublicPrinter))
        session.add_all([PublicPrinter(device_id=device_id) for device_id in next_ids])

    if setting is None:
        session.add(PrinterAccessSetting(id=_SETTINGS_ID, restrict_default=next_restrict))
    else:
        setting.restrict_default = next_restrict

    await session.commit()
    return await default_access(session)


async def policy_by_login(
    session: AsyncSession, *, public_tokens: tuple[str, ...]
) -> dict[str, LoginPolicy]:
    """Guruhga kirgan har bir login uchun hal qilingan siyosat.

    Guruhga kirmaganlar natijada bo'lmaydi — ularga standart qoida qo'llanadi.
    `allowed` guruh istisno bo'lgani uchun umumiy printerlarni ham oladi.
    """
    rows = (
        await session.execute(
            select(
                PrinterGroupMember.login,
                PrinterGroup.id,
                PrinterGroup.name,
                PrinterGroup.policy,
            ).join(PrinterGroup, PrinterGroup.id == PrinterGroupMember.group_id)
        )
    ).all()
    if not rows:
        return {}

    tokens = await _tokens_by_group(session)
    return {
        login: LoginPolicy(
            group_id=gid,
            group_name=name,
            policy=policy,
            tokens=tuple(dict.fromkeys((*public_tokens, *tokens.get(gid, ()))))
            if policy == ALLOWED
            else (),
        )
        for login, gid, name, policy in rows
    }


async def blocked_logins(session: AsyncSession) -> set[str]:
    """`policy='none'` guruhidagi loginlar — ularga `limit: 0` yuboriladi."""
    rows = (
        await session.execute(
            select(PrinterGroupMember.login)
            .join(PrinterGroup, PrinterGroup.id == PrinterGroupMember.group_id)
            .where(PrinterGroup.policy == NONE)
        )
    ).scalars().all()
    return set(rows)


# ---------------------------------------------------------------------------
# Yozish
# ---------------------------------------------------------------------------


async def create_group(session: AsyncSession, *, name: str, policy: str) -> PrinterGroup:
    clean = _clean_name(name)
    _validate_policy(policy)
    await _check_name_free(session, clean, except_id=None)

    group = PrinterGroup(name=clean, policy=policy)
    session.add(group)
    await session.commit()
    await session.refresh(group)
    return group


async def update_group(
    session: AsyncSession,
    group_id: int,
    *,
    name: str | None = None,
    policy: str | None = None,
    device_ids: list[int] | None = None,
    logins: list[str] | None = None,
) -> PrinterGroup:
    """Qisman yangilash: faqat berilgan maydonlar o'zgaradi.

    `device_ids` va `logins` berilsa ro'yxat **butunlay almashtiriladi** —
    dashboarddagi tanlov oynasi har doim to'liq ro'yxat yuboradi, shuning uchun
    qo'shish/o'chirishni alohida amallarga ajratish ortiqcha murakkablik.
    """
    group = await _require_group(session, group_id)

    if name is not None:
        clean = _clean_name(name)
        await _check_name_free(session, clean, except_id=group_id)
        group.name = clean

    if policy is not None:
        group.policy = _validate_policy(policy)

    if device_ids is not None:
        unique = sorted(dict.fromkeys(device_ids))
        await _check_devices_exist(session, unique)
        await session.execute(
            delete(PrinterGroupPrinter).where(PrinterGroupPrinter.group_id == group_id)
        )
        session.add_all(
            [PrinterGroupPrinter(group_id=group_id, device_id=d) for d in unique]
        )

    if logins is not None:
        normalized = [n for n in (normalize_login(x) for x in logins) if n]
        unique_logins = sorted(dict.fromkeys(normalized))
        await _check_logins_free(session, unique_logins, group_id=group_id)
        await session.execute(
            delete(PrinterGroupMember).where(PrinterGroupMember.group_id == group_id)
        )
        session.add_all(
            [PrinterGroupMember(group_id=group_id, login=login) for login in unique_logins]
        )

    await session.commit()
    await session.refresh(group)
    return group


async def delete_group(session: AsyncSession, group_id: int) -> None:
    """Guruhni va uning a'zolik/printer yozuvlarini o'chiradi.

    A'zolar guruhsiz qoladi, ya'ni ularga standart qoida qo'llanadi: istisno
    bekor bo'ladi.
    """
    await _require_group(session, group_id)
    await session.execute(
        delete(PrinterGroupPrinter).where(PrinterGroupPrinter.group_id == group_id)
    )
    await session.execute(
        delete(PrinterGroupMember).where(PrinterGroupMember.group_id == group_id)
    )
    await session.execute(delete(PrinterGroup).where(PrinterGroup.id == group_id))
    await session.commit()


# ---------------------------------------------------------------------------
# Hisobot: ruxsat etilmagan printerdan chiqarish
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Violation:
    """Xodim o'ziga ruxsat etilmagan printerdan chiqargan \u2014 bitta qator."""

    login: str
    full_name: str | None
    department: str | None
    group_name: str
    policy: str
    device_id: int | None
    printer_name: str
    pages: int
    jobs: int
    last_at: datetime


def violations_stmt(start: datetime, end: datetime, *, include_default: bool):
    r"""Davr ichida ruxsat etilmagan printerdan chiqarishlar.

    Qoida uch holatni qamrab oladi:

    * `policy='none'` \u2014 har qanday chiqarish buzilish;
    * `policy='allowed'` \u2014 qurilma na umumiy, na guruhning ro'yxatida bo'lsa;
    * guruhsiz xodim \u2014 qurilma umumiy bo'lmasa (`include_default`).

    `include_default` cheklov tugmasiga emas, umumiy ro'yxat borligiga bog'liq.
    Shu sababli hisobot cheklov yoqilishidan oldin "kim to'silgan bo'lardi"
    degan savolga javob beradi.

    Faqat **muvaffaqiyatli** ishlar olinadi: hisobot "qog'oz sarflandi" degan
    faktni ko'rsatadi, urinishni emas. Bekor qilingan ishlar jurnalda sababi
    bilan ko'rinadi.

    Qurilmasi aniqlanmagan yozuvlar (reyestrda nishoni yo'q) chiqarilmaydi \u2014
    ular haqida hukm chiqarib bo'lmaydi.
    """
    device_id = printers.device_id_expr()
    login_expr = func.lower(
        func.regexp_replace(PrintJob.user_name, SQL_DOMAIN_PREFIX_PATTERN, "")
    )
    # Yorliq `login` emas: so'rovda `employees.login` ustuni ham bor.
    login = login_expr.label("norm_login")

    is_public = select(PublicPrinter.id).where(PublicPrinter.device_id == device_id).exists()

    allowed_here = (
        select(PrinterGroupPrinter.id)
        .where(
            PrinterGroupPrinter.group_id == PrinterGroup.id,
            PrinterGroupPrinter.device_id == device_id,
        )
        .exists()
    )

    breaches = [
        PrinterGroup.policy == NONE,
        and_(PrinterGroup.policy == ALLOWED, ~allowed_here, ~is_public),
    ]
    if include_default:
        breaches.append(and_(PrinterGroupMember.id.is_(None), ~is_public))

    stmt = (
        select(
            login,
            func.max(Employee.full_name).label("full_name"),
            func.max(Employee.department).label("department"),
            func.max(PrinterGroup.name).label("group_name"),
            func.max(PrinterGroup.policy).label("policy"),
            device_id.label("device_id"),
            func.max(
                func.coalesce(
                    PrinterDevice.name, PrinterDevice.last_driver_name, PrintJob.printer
                )
            ).label("printer_name"),
            func.coalesce(func.sum(PrintJob.pages), 0).label("pages"),
            func.count().label("jobs"),
            func.max(PrintJob.printed_at).label("last_at"),
        )
        .select_from(PrintJob)
    )
    stmt = printers.join_device(stmt)
    stmt = (
        stmt.outerjoin(PrinterDevice, PrinterDevice.id == device_id)
        .outerjoin(PrinterGroupMember, PrinterGroupMember.login == login_expr)
        .outerjoin(PrinterGroup, PrinterGroup.id == PrinterGroupMember.group_id)
        .outerjoin(Employee, func.lower(Employee.login) == login_expr)
        .where(
            PrintJob.printed_at >= start,
            PrintJob.printed_at < end,
            PrintJob.success.is_(True),
            device_id.isnot(None),
            or_(*breaches),
        )
        .group_by(login, device_id)
        .order_by(func.sum(PrintJob.pages).desc())
    )
    return stmt


async def violations(session: AsyncSession, start: datetime, end: datetime) -> list[Violation]:
    # Umumiy ro'yxat bo'sh bo'lsa guruhsiz hamma "buzgan" bo'lib chiqardi.
    has_public = await session.scalar(select(PublicPrinter.id).limit(1)) is not None
    rows = (
        await session.execute(violations_stmt(start, end, include_default=has_public))
    ).all()
    return [
        Violation(
            login=r.norm_login,
            full_name=r.full_name,
            department=r.department,
            group_name=r.group_name or NO_GROUP_LABEL,
            policy=r.policy or DEFAULT,
            device_id=int(r.device_id) if r.device_id is not None else None,
            printer_name=r.printer_name or "—",
            pages=int(r.pages or 0),
            jobs=int(r.jobs or 0),
            last_at=r.last_at,
        )
        for r in rows
    ]
