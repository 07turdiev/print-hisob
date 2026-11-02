"""Bir nechta endpoint uchun umumiy FastAPI bog'liqliklari.

`period_params` avval `main.py` da turardi, lekin uni routerlar ham ishlatishi
kerak bo'ldi — `main.py` routerlarni import qilgani uchun teskari import
halqasi chiqardi. Shuning uchun u alohida modulga ko'chirildi.
"""

from fastapi import HTTPException, Query

from app.periods import Period, PeriodType, period_bounds


async def period_params(
    period_type: PeriodType = Query(..., description="Davr turi: 'month' yoki 'quarter'"),
    year: int = Query(..., ge=2000, le=2100, description="Yil, masalan 2026"),
    period_no: int = Query(..., description="Oy uchun 1..12, chorak uchun 1..4 (Q1=1..Q4=4)"),
) -> Period:
    """`period_type/year/period_no` query-parametrlaridan `[start, end)` chegarasini hisoblaydi."""
    try:
        start, end = period_bounds(period_type, year, period_no)
    except ValueError as exc:
        # `status.HTTP_422_UNPROCESSABLE_ENTITY` starlette'da eskirgan; sonni
        # to'g'ridan-to'g'ri ishlatamiz.
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return Period(period_type=period_type, year=year, period_no=period_no, start=start, end=end)
