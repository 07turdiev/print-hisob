"""Oy/chorak davrlarini hisoblash uchun yordamchi funksiyalar.

Dashboard hisobotlari **kalendar chorak** (Q1-Q4) yoki **oy** bo'yicha chiqadi.
Bu modul (year, period_no) juftligini `[start, end)` vaqt oralig'iga aylantiradi;
filtrlash SQL tomonda `printed_at >= start AND printed_at < end` ko'rinishida bo'ladi.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

PeriodType = Literal["month", "quarter"]


def validate_period_no(period_type: PeriodType, period_no: int) -> None:
    """`period_no` berilgan `period_type` uchun to'g'ri oraliqda ekanini tekshiradi."""
    if period_type == "month":
        if not 1 <= period_no <= 12:
            raise ValueError("Oy uchun period_no 1..12 oralig'ida bo'lishi kerak")
    elif period_type == "quarter":
        if not 1 <= period_no <= 4:
            raise ValueError("Chorak uchun period_no 1..4 oralig'ida bo'lishi kerak")
    else:
        raise ValueError(f"Noma'lum period_type: {period_type!r}")


def _add_months(dt: datetime, months: int) -> datetime:
    total = dt.month - 1 + months
    year = dt.year + total // 12
    month = total % 12 + 1
    return dt.replace(year=year, month=month)


def period_bounds(period_type: PeriodType, year: int, period_no: int) -> tuple[datetime, datetime]:
    """(year, period_no) uchun `[start, end)` chegaralarini UTC datetime sifatida qaytaradi.

    - `period_type="month"`: `period_no` 1 (yanvar) dan 12 (dekabr) gacha.
    - `period_type="quarter"`: `period_no` 1 (Q1: yanvar-mart) dan 4 (Q4: oktabr-dekabr) gacha.
    """
    validate_period_no(period_type, period_no)

    if period_type == "month":
        start = datetime(year, period_no, 1, tzinfo=timezone.utc)
        end = _add_months(start, 1)
    else:
        start_month = (period_no - 1) * 3 + 1
        start = datetime(year, start_month, 1, tzinfo=timezone.utc)
        end = _add_months(start, 3)

    return start, end


@dataclass(frozen=True)
class Period:
    """So'rov query-parametrlaridan hisoblangan davr va uning vaqt chegaralari."""

    period_type: PeriodType
    year: int
    period_no: int
    start: datetime
    end: datetime


# Hisobotlarda (masalan CSV eksport) ko'rsatiladigan oy nomlari (o'zbekcha, lotin).
_UZ_MONTH_NAMES = [
    "Yanvar",
    "Fevral",
    "Mart",
    "Aprel",
    "May",
    "Iyun",
    "Iyul",
    "Avgust",
    "Sentyabr",
    "Oktyabr",
    "Noyabr",
    "Dekabr",
]


def period_label(period_type: PeriodType, period_no: int) -> str:
    """Davrning o'zbekcha nomini qaytaradi: oy uchun oy nomi, chorak uchun "N-chorak"."""
    validate_period_no(period_type, period_no)
    if period_type == "month":
        return _UZ_MONTH_NAMES[period_no - 1]
    return f"{period_no}-chorak"
