r"""Foydalanuvchi sozlamalari: chop etishni bloklash va xodimni xodimga biriktirish.

**Bloklash** — admin tugmasi bilan, ataylab. Bloklangan loginga agent javobida
`limit: 0` yuboriladi, bu agent hujjatiga ko'ra "umuman chop eta olmaydi" degani.
Kvotadan oshish esa hech kimni to'smaydi — u faqat hisobot normasi.

**Biriktirish** — bir xodimning varaqlarini boshqasining hisobida ham ko'rsatish.
Varaqlar **ko'chirilmaydi**: har ikkala xodim ham o'z sarfini saqlaydi, egasining
qatorida esa "biriktirilganlardan" ustuni alohida chiqadi. Shunday qilib xodim
o'zi qancha chiqarganini ham, unga kimdan qancha qo'shilganini ham ko'radi.

Zanjirlar taqiqlangan (A→B→C). Sababi oddiy: zanjir bo'lsa "kimning hisobida"
degan savolga yagona javob bo'lmay qoladi va A→B→A halqasi hisobni cheksiz
aylantirib yuborishi mumkin. Shuning uchun bog'lanish har doim bir daraja.
"""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.logins import normalize_login
from app.models import Employee, PrintUserOverride
from app.schemas import UserOverrideIn, UserOverrideOut


async def list_overrides(session: AsyncSession) -> list[PrintUserOverride]:
    """Barcha qo'lda belgilangan sozlamalar (bloklangan yoki biriktirilganlar)."""
    stmt = select(PrintUserOverride).order_by(PrintUserOverride.login)
    return list((await session.scalars(stmt)).all())


async def known_login_states(session: AsyncSession) -> dict[str, bool]:
    """`{normallashtirilgan login: bloklanganmi}` — admin tegib o'tgan barcha loginlar.

    **Nega bloklanmaganlari ham kerak?** Agent javobni keshlaydi. Agar blokdan
    chiqarilgan odam javob ro'yxatidan shunchaki yo'qolsa, agent eski keshlangan
    `limit: 0` ni saqlab qolishi mumkin — hujjatda keshning qatorma-qator
    birlashtirilishi yoki butunlay almashtirilishi aniq yozilmagan. Shuning
    uchun "cheklov olindi" degan xabar **aniq** bo'lishi kerak: bunday loginga
    har safar ochiq-oydin `limit: -1` yuboriladi.

    Jadvalda faqat admin qo'lda tegib o'tgan qatorlar bo'lgani uchun bu ro'yxat
    kichik bo'lib qoladi.
    """
    stmt = select(PrintUserOverride.login, PrintUserOverride.blocked)
    return {login: bool(blocked) for login, blocked in (await session.execute(stmt)).all()}


async def links_by_owner(session: AsyncSession) -> dict[str, list[str]]:
    """`{egasining logini: [unga biriktirilgan loginlar]}`."""
    stmt = select(PrintUserOverride.login, PrintUserOverride.charge_to_login).where(
        PrintUserOverride.charge_to_login.isnot(None)
    )
    result: dict[str, list[str]] = {}
    for login, owner in (await session.execute(stmt)).all():
        result.setdefault(owner, []).append(login)
    return result


async def _employee_exists(session: AsyncSession, login: str) -> bool:
    """AD ro'yxatida shunday login bormi (registrga sezgir bo'lmagan holda)."""
    stmt = select(func.count()).select_from(Employee).where(func.lower(Employee.login) == login)
    return bool((await session.execute(stmt)).scalar() or 0)


async def _validate_link(session: AsyncSession, login: str, owner: str) -> None:
    """Biriktirish qoidalarini tekshiradi; buzilsa 400 qaytaradi."""
    if owner == login:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Xodimni o'ziga biriktirib bo'lmaydi",
        )

    if not await _employee_exists(session, owner):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{owner}' xodimlar ro'yxatida topilmadi",
        )

    # Zanjirning birinchi turi: egasining o'zi allaqachon kimgadir biriktirilgan.
    owner_row = await session.scalar(
        select(PrintUserOverride).where(PrintUserOverride.login == owner)
    )
    if owner_row is not None and owner_row.charge_to_login:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"'{owner}' allaqachon '{owner_row.charge_to_login}' ga biriktirilgan — "
                "zanjir hosil qilib bo'lmaydi. Avval uning biriktirilishini bekor qiling."
            ),
        )

    # Zanjirning ikkinchi turi: bu loginning o'ziga kimdir biriktirilgan,
    # ya'ni u egasi bo'lib turibdi.
    followers = (
        await session.execute(
            select(func.count())
            .select_from(PrintUserOverride)
            .where(PrintUserOverride.charge_to_login == login)
        )
    ).scalar() or 0
    if followers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"'{login}' ga boshqa xodim(lar) biriktirilgan, shuning uchun uni "
                "o'zini boshqasiga biriktirib bo'lmaydi."
            ),
        )


async def apply_override(
    session: AsyncSession, raw_login: str, payload: UserOverrideIn, actor: str
) -> UserOverrideOut:
    """Bloklash/biriktirishni qisman yangilaydi.

    Faqat so'rovda **yuborilgan** maydonlar o'zgaradi: masalan faqat `blocked`
    kelsa, biriktirish tegilmaydi va aksincha.
    """
    login = normalize_login(raw_login)
    if not login:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Login bo'sh bo'lishi mumkin emas"
        )

    sent = payload.fields_sent()
    values: dict[str, object] = {"login": login}

    if "blocked" in sent:
        blocked = bool(payload.blocked)
        values["blocked"] = blocked
        values["blocked_at"] = datetime.now(timezone.utc) if blocked else None
        values["blocked_by"] = actor if blocked else None
        # Sababni faqat bloklaganda saqlaymiz; blokdan chiqarilganda tozalanadi.
        values["blocked_reason"] = payload.blocked_reason if blocked else None
    elif "blocked_reason" in sent:
        values["blocked_reason"] = payload.blocked_reason

    if "charge_to_login" in sent:
        owner = normalize_login(payload.charge_to_login) if payload.charge_to_login else None
        if owner:
            await _validate_link(session, login, owner)
        values["charge_to_login"] = owner

    if len(values) == 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hech qanday o'zgarish yuborilmadi",
        )

    stmt = pg_insert(PrintUserOverride).values(**values)
    stmt = stmt.on_conflict_do_update(
        index_elements=["login"],
        set_={key: stmt.excluded[key] for key in values if key != "login"}
        | {"updated_at": func.now()},
    ).returning(PrintUserOverride)
    result = await session.execute(stmt)
    saved = result.scalars().all()
    await session.commit()

    if saved:
        return UserOverrideOut.model_validate(saved[0])

    # Bazasiz (Fake) testlarda `RETURNING` qator qaytarmaydi — haqiqiy bazada bu
    # yo'lga tushilmaydi. Yuborilgan qiymatlardan mos javob quramiz.
    return UserOverrideOut(
        login=login,
        blocked=bool(values.get("blocked", False)),
        blocked_at=values.get("blocked_at"),  # type: ignore[arg-type]
        blocked_by=values.get("blocked_by"),  # type: ignore[arg-type]
        blocked_reason=values.get("blocked_reason"),  # type: ignore[arg-type]
        charge_to_login=values.get("charge_to_login"),  # type: ignore[arg-type]
    )
