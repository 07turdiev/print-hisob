r"""Xodimlar guruhlari va printer ruxsatlari.

**Uch daraja.** Guruh bitta siyosatga ega bo'ladi:

* `all` — to'liq ruxsat;
* `allowed` — faqat belgilangan qurilmalar;
* `none` — umuman chop eta olmaydi.

**Nega shunday taqsimlangan.** `none` yangi mexanizm talab qilmaydi: agentga
mavjud `limit: 0` orqali yetadi, ya'ni bu bugun ishlab turgan "Bloklash" bilan
bir xil kanal. `allowed` esa agentdagi `allowedPrinters` qo'llanmasi chiqqandan
keyin kuchga kiradi — shu vaqtgacha u faqat hisobotda ko'rinadi ("ruxsat
etilmagan printerdan chiqardi").

**Bir xodim — bitta guruh.** Cheklov baza darajasida (`uq_printer_group_members_login`).
Aks holda "bu odamga nima ruxsat etilgan" degan savolga javob guruhlarni
qo'shish qoidasiga bog'liq bo'lib qolardi va sabab topish qiyinlashardi.

**Guruhga kirmagan xodim cheklanmaydi.** Cheklov faqat ongli ravishda qo'yiladi,
shuning uchun guruh tuzilmagan paytda hamma ishlashda davom etadi.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.logins import SQL_DOMAIN_PREFIX_PATTERN, normalize_login
from app.models import (
    Employee,
    PrinterAlias,
    PrinterDevice,
    PrinterGroup,
    PrinterGroupMember,
    PrinterGroupPrinter,
    PrintJob,
)
from app.services import printers

# `status.HTTP_422_UNPROCESSABLE_ENTITY` starlette'da eskirgan; `main.py` dagi
# konventsiya bilan bir xil — sonni to'g'ridan-to'g'ri ishlatamiz.
_UNPROCESSABLE = 422

ALL = "all"
ALLOWED = "allowed"
NONE = "none"
POLICIES = (ALL, ALLOWED, NONE)

# Agent shartnomasidagi "barcha printerlar" belgisi.
ANY_PRINTER = "*"


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


async def _tokens_by_group(session: AsyncSession) -> dict[int, tuple[str, ...]]:
    """Har bir guruh uchun agentga yuboriladigan nishonlar ro'yxati.

    Bitta qurilmaning barcha nishonlari kiradi (MAC, IP va drayver nomlari),
    chunki agent ish navbatga tushganda qaysi nishonni ko'rishini oldindan
    bilmaymiz: bir kompyuterda MAC, boshqasida faqat nom ko'rinadi.
    """
    rows = (
        await session.execute(
            select(PrinterGroupPrinter.group_id, PrinterAlias.value)
            .join(PrinterAlias, PrinterAlias.device_id == PrinterGroupPrinter.device_id)
            .order_by(PrinterGroupPrinter.group_id, PrinterAlias.value)
        )
    ).all()

    by_group: dict[int, list[str]] = {}
    for group_id, value in rows:
        by_group.setdefault(group_id, []).append(value)
    return {gid: tuple(dict.fromkeys(values)) for gid, values in by_group.items()}


async def policy_by_login(session: AsyncSession) -> dict[str, LoginPolicy]:
    """Guruhga kirgan har bir login uchun hal qilingan siyosat.

    Guruhga kirmaganlar natijada bo'lmaydi — ular cheklanmaydi.
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
            tokens=tokens.get(gid, ()) if policy == ALLOWED else (),
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

    A'zolar hech qanday guruhsiz qoladi, ya'ni cheklovsiz chop etadi — bu
    ataylab: guruhni o'chirish "cheklovni olib tashlash" degani.
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


def violations_stmt(start: datetime, end: datetime):
    r"""Davr ichida guruh siyosatini buzgan chiqarishlar.

    Qoida ikki holatni qamrab oladi:

    * `policy='none'` \u2014 har qanday chiqarish buzilish;
    * `policy='allowed'` \u2014 qurilma guruhning ruxsat ro'yxatida bo'lmasa.

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

    allowed_here = (
        select(PrinterGroupPrinter.id)
        .where(
            PrinterGroupPrinter.group_id == PrinterGroup.id,
            PrinterGroupPrinter.device_id == device_id,
        )
        .exists()
    )

    stmt = (
        select(
            PrinterGroupMember.login.label("login"),
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
        .join(PrinterGroupMember, PrinterGroupMember.login == login_expr)
        .join(PrinterGroup, PrinterGroup.id == PrinterGroupMember.group_id)
        .outerjoin(Employee, func.lower(Employee.login) == PrinterGroupMember.login)
        .where(
            PrintJob.printed_at >= start,
            PrintJob.printed_at < end,
            PrintJob.success.is_(True),
            device_id.isnot(None),
            or_(
                PrinterGroup.policy == NONE,
                and_(PrinterGroup.policy == ALLOWED, ~allowed_here),
            ),
        )
        .group_by(PrinterGroupMember.login, device_id)
        .order_by(func.sum(PrintJob.pages).desc())
    )
    return stmt


async def violations(session: AsyncSession, start: datetime, end: datetime) -> list[Violation]:
    rows = (await session.execute(violations_stmt(start, end))).all()
    return [
        Violation(
            login=r.login,
            full_name=r.full_name,
            department=r.department,
            group_name=r.group_name,
            policy=r.policy,
            device_id=int(r.device_id) if r.device_id is not None else None,
            printer_name=r.printer_name or "—",
            pages=int(r.pages or 0),
            jobs=int(r.jobs or 0),
            last_at=r.last_at,
        )
        for r in rows
    ]
