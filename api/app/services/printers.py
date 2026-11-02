r"""Printerlarni tanib olish, birlashtirish va nomlash.

**Muammo.** Bitta jismoniy printer har bir kompyuterda boshqacha drayver nomi
bilan ko'rinadi ("Canon Katta", "Canon svetnoy", `\\server\Canon-2`). Eski
reyestr MAC'ni yagona kalit qilgani uchun MAC yubormaydigan printerlar (boshqa
VLAN, USB, ulashilgan navbat) umuman birlashmas va har bir nom alohida
"printer" bo'lib hisoblanardi.

**Yechim.** Qurilma (`PrinterDevice`) va uni tanib oladigan nishonlar
(`PrinterAlias`) ajratilgan. Chop etish yozuvi kelganda nishonlar shu tartibda
tekshiriladi:

1. `mac` — eng barqaror;
2. `ip` — statik manzilda ishonchli;
3. `name` — eng zaifi, chunki ikki xil printer bir xil drayver nomi bilan
   atalgan bo'lishi mumkin.

Shu sababli **nom nishoni faqat MAC ham, IP ham bo'lmaganda** avtomatik
yaratiladi. Qolgan hollarda nomni qurilmaga admin qo'lda biriktiradi
(birlashtirish amali) — server o'zi taxmin qilib ikki printerni qo'shib
yubormaydi.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import String, cast, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models import Printer, PrinterAlias, PrinterDevice, PrintJob

logger = logging.getLogger(__name__)

MAC = "mac"
IP = "ip"
NAME = "name"

# Nishon turlari ishonchlilik tartibida — qidiruv ham, yaratish ham shu tartibda.
KINDS = (MAC, IP, NAME)


def is_ip(value: str | None) -> bool:
    """Qiymat IPv4 manzilimi.

    `printer_ip` da IP bo'lmagan port nomlari ham keladi (`WSD-...`, `USB001`).
    Ular qurilmani tanib olish uchun yaroqsiz: `USB001` har bir kompyuterda
    boshqa printerni bildiradi, shuning uchun ularni nishon qilib olmaymiz.
    """
    if not value:
        return False
    parts = value.strip().split(".")
    if len(parts) != 4:
        return False
    return all(p.isdigit() and len(p) <= 3 and 0 <= int(p) <= 255 for p in parts)


@dataclass(frozen=True)
class JobPrinter:
    """Chop etish yozuvidagi printer ma'lumoti (ingest uchun)."""

    mac: str | None
    ip: str | None
    name: str
    seen_at: datetime

    def identity(self) -> tuple[str, str]:
        """Shu yozuv uchun qurilmani yaratishda ishlatiladigan asosiy nishon."""
        if self.mac:
            return (MAC, self.mac)
        if is_ip(self.ip):
            return (IP, self.ip or "")
        return (NAME, self.name)


# ---------------------------------------------------------------------------
# SQL: chop etish yozuvini qurilmaga bog'lash
# ---------------------------------------------------------------------------

_AliasMac = aliased(PrinterAlias)
_AliasIp = aliased(PrinterAlias)
_AliasName = aliased(PrinterAlias)


def join_device(stmt):
    """`print_jobs` ga uchta nishon jadvalini qo'shadi (mac, ip, nom tartibida)."""
    return (
        stmt.outerjoin(
            _AliasMac, (_AliasMac.kind == MAC) & (_AliasMac.value == PrintJob.printer_mac)
        )
        .outerjoin(_AliasIp, (_AliasIp.kind == IP) & (_AliasIp.value == PrintJob.printer_ip))
        .outerjoin(_AliasName, (_AliasName.kind == NAME) & (_AliasName.value == PrintJob.printer))
    )


def device_id_expr():
    """Yozuv tegishli bo'lgan qurilma identifikatori (topilmasa `NULL`)."""
    return func.coalesce(_AliasMac.device_id, _AliasIp.device_id, _AliasName.device_id)


def identity_expr():
    """Guruhlash kaliti: qurilma topilsa uning id'si, aks holda xom nom.

    Reconcile'dan keyin deyarli barcha yozuvlar qurilmaga bog'lanadi; zaxira
    tarmog'i faqat reconcile ulgurmagan yangi yozuvlar uchun kerak.
    """
    return func.coalesce(cast(device_id_expr(), String), PrintJob.printer)


# ---------------------------------------------------------------------------
# Nishonlarni yozish
# ---------------------------------------------------------------------------


async def _claim_alias(session: AsyncSession, device_id: int, kind: str, value: str) -> bool:
    """Nishonni qurilmaga biriktiradi. Band bo'lsa tegmaydi va `False` qaytaradi.

    Band nishonni boshqa qurilmaga ko'chirib yubormaymiz: bu jim turib
    statistikani boshqa printerga olib o'tib yuborardi. Ko'chirish faqat aniq
    `merge()` amali orqali bo'ladi.
    """
    stmt = (
        pg_insert(PrinterAlias)
        .values(device_id=device_id, kind=kind, value=value)
        .on_conflict_do_nothing(constraint="uq_printer_aliases_kind_value")
    )
    result = await session.execute(stmt)
    return bool(result.rowcount)


async def _has_alias(session: AsyncSession, device_id: int, kind: str) -> bool:
    """Qurilmaga shu turdagi nishon allaqachon biriktirilganmi."""
    found = await session.scalar(
        select(PrinterAlias.id)
        .where(PrinterAlias.device_id == device_id, PrinterAlias.kind == kind)
        .limit(1)
    )
    return found is not None


async def _find_device(session: AsyncSession, job: JobPrinter) -> int | None:
    """Yozuvga mos qurilmani nishonlar bo'yicha qidiradi (mac -> ip -> nom)."""
    candidates: list[tuple[str, str]] = []
    if job.mac:
        candidates.append((MAC, job.mac))
    if is_ip(job.ip):
        candidates.append((IP, job.ip or ""))
    candidates.append((NAME, job.name))

    for kind, value in candidates:
        found = await session.scalar(
            select(PrinterAlias.device_id).where(
                PrinterAlias.kind == kind, PrinterAlias.value == value
            )
        )
        if found is None:
            continue
        device_id = int(found)

        # IP yoki nom bo'yicha topildi, lekin qurilmada MAC turibdi — va u
        # bu yozuvning MAC'i emas (aks holda tsikl birinchi qadamda tugardi).
        # Demak IP boshqa jismoniy printerga o'tgan: DHCP manzilni qayta
        # taqsimlagan yoki printer almashtirilgan. Bu holda eski qurilmaga
        # yozib ketmaymiz — yangisi yaratiladi va admin kerak bo'lsa `merge`
        # qiladi. Jim turib ikki printerning tarixini qo'shib yuborish
        # xavfliroq: qo'shilganini ajratib bo'lmaydi.
        if kind != MAC and job.mac and await _has_alias(session, device_id, MAC):
            return None

        return device_id
    return None


async def ensure_device(session: AsyncSession, job: JobPrinter) -> int:
    """Yozuvga mos qurilmani topadi, bo'lmasa yaratadi va nishonlarini biriktiradi."""
    device_id = await _find_device(session, job)

    if device_id is None:
        inserted = await session.execute(
            pg_insert(PrinterDevice)
            .values(
                last_driver_name=job.name,
                last_ip=job.ip if is_ip(job.ip) else None,
                last_seen=job.seen_at,
            )
            .returning(PrinterDevice.id)
        )
        new_id = inserted.scalar()
        if new_id is None:
            # Bazasiz (Fake) testlarda `RETURNING` qator qaytarmaydi.
            return 0
        device_id = int(new_id)

        kind, value = job.identity()
        await _claim_alias(session, device_id, kind, value)

    # Topilgan qurilmaga MAC'ni ham biriktiramiz, lekin faqat unda MAC hali
    # bo'lmasa. Buning sababi: reyestrdagi qurilmalar IP bo'yicha qurilgan
    # (agent MAC yubormagan davrda), shuning uchun MAC kelib boshlaganda u
    # o'sha qurilmaga yozilishi kerak — aks holda IP almashgan kuni printer
    # yangi qurilma bo'lib ajralib ketadi va MAC yuborishdan foyda bo'lmaydi.
    #
    # Qurilmada boshqa MAC turgan bo'lsa tegmaymiz: bu plata almashganini yoki
    # IP boshqa jismoniy printerga o'tganini bildiradi. Jim turib ikki
    # printerni qo'shib yuborishdan ko'ra, ularni alohida qoldirib adminning
    # `merge` qarorini kutish xavfsizroq — noto'g'ri qo'shilgan tarixni
    # ajratib bo'lmaydi.
    if job.mac and not await _has_alias(session, device_id, MAC):
        await _claim_alias(session, device_id, MAC, job.mac)

    # MAC bilan kelgan qurilmaning IP'sini ham biriktiramiz: shunda o'sha printer
    # MAC'siz (boshqa kompyuterdan) ko'ringanda alohida qurilma yaratilmaydi.
    if job.mac and is_ip(job.ip):
        await _claim_alias(session, device_id, IP, job.ip or "")

    await session.execute(
        update(PrinterDevice)
        .where(PrinterDevice.id == device_id)
        .values(
            last_driver_name=job.name,
            last_ip=job.ip if is_ip(job.ip) else PrinterDevice.last_ip,
            last_seen=func.greatest(func.coalesce(PrinterDevice.last_seen, job.seen_at), job.seen_at),
        )
    )
    return device_id


# ---------------------------------------------------------------------------
# Mavjud ma'lumotni ko'chirish (reconcile)
# ---------------------------------------------------------------------------


async def _new_device(
    session: AsyncSession,
    *,
    name: str | None,
    driver_name: str | None,
    ip: str | None,
    seen_at: datetime | None,
) -> int | None:
    result = await session.execute(
        pg_insert(PrinterDevice)
        .values(
            name=name,
            last_driver_name=driver_name,
            last_ip=ip if is_ip(ip) else None,
            last_seen=seen_at,
        )
        .returning(PrinterDevice.id)
    )
    new_id = result.scalar()
    return int(new_id) if new_id is not None else None


async def _alias_owner(session: AsyncSession, kind: str, value: str) -> int | None:
    owner = await session.scalar(
        select(PrinterAlias.device_id).where(PrinterAlias.kind == kind, PrinterAlias.value == value)
    )
    return int(owner) if owner is not None else None


async def reconcile(session: AsyncSession) -> dict[str, int]:
    """Mavjud chop etish tarixidan qurilmalar reyestrini quradi.

    Idempotent: qayta ishga tushirilsa faqat yangi nishonlarni qo'shadi.
    Tartib muhim — avval MAC, keyin IP, oxirida nom: shunda MAC bilan ko'ringan
    printer MAC'siz yozuvlar tufayli ikkinchi marta yaratilmaydi.
    """
    created = 0

    # 1) Eski `printers` reyestri — admin qo'ygan nomlarni yo'qotmaymiz.
    for row in (await session.execute(select(Printer))).scalars().all():
        device_id = await _alias_owner(session, MAC, row.mac)
        if device_id is None:
            device_id = await _new_device(
                session,
                name=row.name,
                driver_name=row.last_driver_name,
                ip=row.last_ip,
                seen_at=row.last_seen,
            )
            if device_id is None:
                continue
            created += 1
            await _claim_alias(session, device_id, MAC, row.mac)
        elif row.name:
            await session.execute(
                update(PrinterDevice)
                .where(PrinterDevice.id == device_id, PrinterDevice.name.is_(None))
                .values(name=row.name)
            )
        if is_ip(row.last_ip):
            await _claim_alias(session, device_id, IP, row.last_ip or "")

    # 2) Tarixdagi MAC'lar.
    mac_rows = (
        await session.execute(
            select(
                PrintJob.printer_mac,
                func.max(PrintJob.printer).label("driver_name"),
                func.max(PrintJob.printer_ip).label("ip"),
                func.max(PrintJob.printed_at).label("seen_at"),
            )
            .where(PrintJob.printer_mac.isnot(None))
            .group_by(PrintJob.printer_mac)
        )
    ).all()
    for row in mac_rows:
        device_id = await _alias_owner(session, MAC, row.printer_mac)
        if device_id is None:
            device_id = await _new_device(
                session, name=None, driver_name=row.driver_name, ip=row.ip, seen_at=row.seen_at
            )
            if device_id is None:
                continue
            created += 1
            await _claim_alias(session, device_id, MAC, row.printer_mac)
        if is_ip(row.ip):
            await _claim_alias(session, device_id, IP, row.ip or "")

    # 3) MAC bo'yicha topilmagan yozuvlardagi IP'lar.
    ip_stmt = (
        join_device(
            select(
                PrintJob.printer_ip,
                func.max(PrintJob.printer).label("driver_name"),
                func.max(PrintJob.printed_at).label("seen_at"),
            ).select_from(PrintJob)
        )
        .where(_AliasMac.device_id.is_(None), PrintJob.printer_ip.isnot(None))
        .group_by(PrintJob.printer_ip)
    )
    for row in (await session.execute(ip_stmt)).all():
        if not is_ip(row.printer_ip):
            continue
        if await _alias_owner(session, IP, row.printer_ip) is not None:
            continue
        device_id = await _new_device(
            session,
            name=None,
            driver_name=row.driver_name,
            ip=row.printer_ip,
            seen_at=row.seen_at,
        )
        if device_id is None:
            continue
        created += 1
        await _claim_alias(session, device_id, IP, row.printer_ip)

    # 4) Na MAC, na IP bo'yicha topilmaganlar — faqat nom qoladi.
    name_stmt = (
        join_device(
            select(
                PrintJob.printer,
                func.max(PrintJob.printed_at).label("seen_at"),
            ).select_from(PrintJob)
        )
        .where(_AliasMac.device_id.is_(None), _AliasIp.device_id.is_(None))
        .group_by(PrintJob.printer)
    )
    for row in (await session.execute(name_stmt)).all():
        if await _alias_owner(session, NAME, row.printer) is not None:
            continue
        device_id = await _new_device(
            session, name=None, driver_name=row.printer, ip=None, seen_at=row.seen_at
        )
        if device_id is None:
            continue
        created += 1
        await _claim_alias(session, device_id, NAME, row.printer)

    await session.commit()
    total = (await session.execute(select(func.count()).select_from(PrinterDevice))).scalar() or 0
    logger.info("printer reconcile: created=%d total=%d", created, total)
    return {"created": created, "total": int(total)}


# ---------------------------------------------------------------------------
# Boshqaruv amallari
# ---------------------------------------------------------------------------


async def list_devices(session: AsyncSession) -> list[tuple[PrinterDevice, list[PrinterAlias]]]:
    """Barcha qurilmalar va ularning nishonlari."""
    devices = (
        (
            await session.execute(
                select(PrinterDevice).order_by(PrinterDevice.last_seen.desc().nullslast())
            )
        )
        .scalars()
        .all()
    )
    aliases = (await session.execute(select(PrinterAlias))).scalars().all()

    by_device: dict[int, list[PrinterAlias]] = {}
    for alias in aliases:
        by_device.setdefault(alias.device_id, []).append(alias)
    return [(d, by_device.get(d.id, [])) for d in devices]


@dataclass(frozen=True)
class MergeSuggestion:
    """Faqat nom bo'yicha aniqlangan qurilma uchun birlashtirish taklifi."""

    device_id: int
    target_id: int
    shared_name: str


def merge_suggestions_stmt():
    r"""Nom bo'yicha ajralib qolgan qurilmalarga mos MAC'li qurilmani topadi.

    Bitta printer bir kompyuterda MAC bilan, boshqasida MAC'siz ko'rinishi
    mumkin (ulashilgan navbat, boshqa pod-tarmoq). MAC'siz yozuv faqat drayver
    nomi bilan keladi va alohida qurilma bo'lib ajraladi. Agar **aynan shu
    drayver nomi** boshqa kompyuterdan MAC bilan ham kelgan bo'lsa, ikkisi
    bitta printer bo'lishi ehtimoli katta.

    Ehtimol \u2014 dalil emas, shuning uchun bu funksiya hech narsa o'zgartirmaydi:
    faqat taklif qaytaradi, qarorni admin qabul qiladi. Ikki xil printer bir xil
    drayver nomi bilan atalishi mumkin (bir modeldagi ikki qurilma), shuning
    uchun nom bir nechta MAC'li qurilmaga ishora qilsa taklif berilmaydi \u2014
    noto'g'ri birlashtirishni keyin ajratib bo'lmaydi.
    """
    strong = aliased(PrinterAlias)
    has_strong = (
        select(strong.id)
        .where(strong.device_id == PrinterAlias.device_id, strong.kind.in_((MAC, IP)))
        .exists()
    )

    # Faqat nom nishoni bor qurilmalar: MAC yoki IP bo'lsa ular yetarli.
    name_only = (
        select(
            PrinterAlias.device_id.label("device_id"),
            PrinterAlias.value.label("name"),
        )
        .where(PrinterAlias.kind == NAME, ~has_strong)
        .cte("name_only")
    )

    # Shu nom MAC bilan ham kelganmi va o'sha MAC qaysi qurilmaga tegishli.
    mac_alias = aliased(PrinterAlias)
    pairs = (
        select(
            name_only.c.device_id,
            mac_alias.device_id.label("target_id"),
            func.min(name_only.c.name).label("shared_name"),
        )
        .join(PrintJob, PrintJob.printer == name_only.c.name)
        .join(
            mac_alias,
            (mac_alias.kind == MAC) & (mac_alias.value == PrintJob.printer_mac),
        )
        .where(PrintJob.printer_mac.isnot(None))
        .group_by(name_only.c.device_id, mac_alias.device_id)
        .cte("pairs")
    )

    stmt = (
        select(
            pairs.c.device_id,
            func.min(pairs.c.target_id).label("target_id"),
            func.min(pairs.c.shared_name).label("shared_name"),
        )
        .where(pairs.c.device_id != pairs.c.target_id)
        .group_by(pairs.c.device_id)
        # Bir nechta MAC'li qurilmaga ishora qilsa \u2014 noaniq, taklif bermaymiz.
        .having(func.count(func.distinct(pairs.c.target_id)) == 1)
    )

    return stmt


async def merge_suggestions(session: AsyncSession) -> list[MergeSuggestion]:
    """`merge_suggestions_stmt()` ni bajaradi va natijani dataclass'ga o'giradi."""
    rows = (await session.execute(merge_suggestions_stmt())).all()
    return [
        MergeSuggestion(
            device_id=int(r.device_id),
            target_id=int(r.target_id),
            shared_name=str(r.shared_name),
        )
        for r in rows
    ]


async def _require_device(session: AsyncSession, device_id: int) -> PrinterDevice:
    device = await session.get(PrinterDevice, device_id)
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Printer #{device_id} topilmadi"
        )
    return device


async def rename(session: AsyncSession, device_id: int, name: str | None) -> PrinterDevice:
    """Qurilmaga qulay nom qo'yadi. Bo'sh nom nomni tozalaydi (drayver nomi qoladi)."""
    device = await _require_device(session, device_id)
    device.name = (name or "").strip() or None
    await session.commit()
    await session.refresh(device)
    return device


async def merge(session: AsyncSession, target_id: int, source_id: int) -> PrinterDevice:
    """`source` qurilmasini `target` ichiga qo'shadi: barcha nishonlar ko'chadi.

    Aynan shu amal "bitta printer, besh xil nom" holatini hal qiladi — tarix ham,
    statistika ham shu zahoti bitta nom ostida birlashadi, chunki yozuvlar
    nishonlar orqali bog'lanadi.
    """
    if target_id == source_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Printerni o'ziga qo'shib bo'lmaydi"
        )
    target = await _require_device(session, target_id)
    source = await _require_device(session, source_id)

    await session.execute(
        update(PrinterAlias).where(PrinterAlias.device_id == source_id).values(device_id=target_id)
    )
    # Nom qo'yilmagan bo'lsa, qo'shilayotgan qurilmanikini olamiz — aks holda
    # admin qo'ygan nom yo'qolardi.
    if not target.name and source.name:
        target.name = source.name
    if not target.last_driver_name:
        target.last_driver_name = source.last_driver_name
    if not target.last_ip:
        target.last_ip = source.last_ip
    if source.last_seen and (not target.last_seen or source.last_seen > target.last_seen):
        target.last_seen = source.last_seen

    await session.delete(source)
    await session.commit()
    await session.refresh(target)
    return target
