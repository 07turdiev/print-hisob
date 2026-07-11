"""Qog'oz sarfi hisobi uchun testlar.

**Muhim**: agent endi duplex hisobini o'zi qilib, `pages` maydonida tayyor
jismoniy varaq (qog'oz) sonini yuboradi. Shuning uchun serverda hech qanday
qo'shimcha yaxlitlash/bo'lish (avvalgi `SHEETS = CASE ... duplex ...`
ifodasi) qilinMAYDI — sarf har doim oddiy `SUM(pages)` bilan hisoblanadi.

Haqiqiy bazasiz `conftest.FakeSession` faqat bind-parametrlarni yozib oladi
(compiled SQL matnini emas), shuning uchun bu yerda `/api/stats/*`
endpointlari `duplex`ga bog'liq CASE ifodasisiz, to'g'ridan-to'g'ri
`PrintJob.pages` ustuni bilan qurilishini alohida stub `session.execute`
bilan ulanib, yuborilgan SQL matnida tekshiramiz.
"""

from sqlalchemy.dialects import postgresql

from app.main import app
from app.db import get_session


class _SQLCapturingSession:
    """Har bir `execute()`ga kelgan so'rovning kompilyatsiya qilingan SQL
    matnini (bind-parametrlar emas) yozib oladi — `CASE`/`duplex` ifodasi
    endi ISHLATILMASLIGINI tekshirish uchun.
    """

    def __init__(self) -> None:
        self.statements: list[str] = []

    def begin(self):
        class _Tx:
            async def __aenter__(self_inner):
                return self_inner

            async def __aexit__(self_inner, *exc):
                return False

        return _Tx()

    async def execute(self, stmt):
        self.statements.append(str(stmt.compile(dialect=postgresql.dialect())))

        class _EmptyResult:
            rowcount = 0

            def scalars(self):
                return self

            def all(self):
                return []

            def one(self):
                class _Row:
                    def __getattr__(self, name):
                        return 0

                return _Row()

            def scalar(self):
                return 0

        return _EmptyResult()

    async def scalars(self, stmt):
        return await self.execute(stmt)


def _capture_sql_for(path: str, params: dict) -> list[str]:
    from fastapi.testclient import TestClient

    session = _SQLCapturingSession()

    async def _fake_session():
        yield session

    app.dependency_overrides[get_session] = _fake_session
    try:
        with TestClient(app) as c:
            # Bu endpointlar `require_user` bilan himoyalangan; lekin biz faqat
            # SQL qurilishini tekshiramiz, shuning uchun autentifikatsiyani
            # yon o'tkazish uchun `require_user`ni ham bekor qilamiz.
            from app.auth import require_user

            app.dependency_overrides[require_user] = lambda: "test"
            r = c.get(path, params=params)
            assert r.status_code == 200, r.text
    finally:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(require_user, None)
    return session.statements


PERIOD = {"period_type": "quarter", "year": 2026, "period_no": 3}


def _assert_plain_sum_pages_no_duplex_case(statements: list[str]) -> None:
    joined = "\n".join(statements)
    assert "sum(print_jobs.pages)" in joined.lower()
    # Avvalgi `CASE WHEN print_jobs.duplex ...` ifodasi butunlay olib tashlangan
    # (boshqa maqsadda, masalan muvaffaqiyat/xato sanog'ida, `CASE` ishlatilishi
    # mumkin — shuning uchun faqat `duplex` ustuni umuman ishlatilmasligini
    # tekshiramiz).
    assert "duplex" not in joined.lower()


def test_stats_summary_sums_plain_pages():
    statements = _capture_sql_for("/api/stats/summary", PERIOD)
    _assert_plain_sum_pages_no_duplex_case(statements)


def test_stats_employees_sums_plain_pages():
    statements = _capture_sql_for("/api/stats/employees", PERIOD)
    _assert_plain_sum_pages_no_duplex_case(statements)


def test_stats_timeseries_sums_plain_pages():
    statements = _capture_sql_for("/api/stats/timeseries", PERIOD)
    _assert_plain_sum_pages_no_duplex_case(statements)


def test_stats_top_sums_plain_pages():
    statements = _capture_sql_for("/api/stats/top", PERIOD)
    _assert_plain_sum_pages_no_duplex_case(statements)


def test_stats_printers_sums_plain_pages():
    statements = _capture_sql_for("/api/stats/printers", PERIOD)
    _assert_plain_sum_pages_no_duplex_case(statements)


def test_stats_departments_sums_plain_pages():
    statements = _capture_sql_for("/api/stats/departments", PERIOD)
    _assert_plain_sum_pages_no_duplex_case(statements)
