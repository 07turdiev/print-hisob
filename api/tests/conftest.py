"""Yangi endpoint testlari uchun umumiy, bazasiz (DB-free) yordamchilar.

`test_ingest.py` o'ziga xos oddiyroq stub bilan ishlaydi (faqat `execute()` va
dedup_key asosidagi rowcount). Bu yerdagi `FakeSession` esa `ad-sync`, `quotas`
va `stats` endpointlari uchun kerak bo'lgan `session.scalars()`, `.one()` va
`.all()` metodlarini ham qo'llab-quvvatlaydi — baribir haqiqiy bazaga ulanmaydi,
faqat SQL'ni kompilyatsiya qilib parametrlarni yozib oladi.
"""

import asyncio
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

os.environ.setdefault("AUTO_CREATE_TABLES", "false")
os.environ.setdefault("API_KEY", "")
# Dashboard autentifikatsiyasi (JWT) — testlar shu maxfiy kalit bilan token yasaydi.
os.environ.setdefault("AUTH_USERNAME", "admin")
os.environ.setdefault("AUTH_PASSWORD", "test-parol")
os.environ.setdefault("JWT_SECRET", "test-uchun-uzun-maxfiy-kalit-32-bayt-yoki-kop")

import jwt
import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from fastapi.testclient import TestClient
from sqlalchemy import make_url, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.db import Base, get_session
from app.main import app

# Bearer autentifikatsiya talab qiladigan endpointlar uchun tayyor, yaroqli token.
_TEST_TOKEN = jwt.encode(
    {
        "sub": settings.auth_username,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes),
    },
    settings.jwt_secret,
    algorithm="HS256",
)

# Har bir `execute()`/`scalars()` chaqiruvida qabul qilingan bind-parametrlar shu yerga yoziladi.
CAPTURED: list[dict] = []
# Kompilyatsiya qilingan SQL matnlari — masalan ON CONFLICT DO UPDATE qaysi
# ustunlarga tegayotganini tekshirish uchun.
CAPTURED_SQL: list[str] = []

_MULTIROW_RE = re.compile(r"_m(\d+)$")


def _rowcount_from_params(params: dict) -> int:
    """Ko'p qatorli INSERT'da (`col_m0`, `col_m1`, ...) qatorlar sonini taxmin qiladi."""
    indices = {int(m.group(1)) for key in params if (m := _MULTIROW_RE.search(key))}
    return len(indices)


class _FakeTx:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class _FakeRow:
    """SELECT natijasi uchun soxta qator: talab qilingan ustunlar 0 qiymat bilan qaytadi."""

    def __init__(self, values: dict):
        self._values = values

    def __getattr__(self, name):
        return self._values.get(name)


class _FakeResult:
    """Haqiqiy bazasiz `Result`ga o'xshab `.one()`, `.all()`, `.scalars()`, `.rowcount`."""

    def __init__(self, stmt, params: dict):
        self._stmt = stmt
        self._rowcount = _rowcount_from_params(params)

    def _column_keys(self) -> list[str]:
        try:
            return list(self._stmt.selected_columns.keys())
        except Exception:
            return []

    @property
    def rowcount(self) -> int:
        return self._rowcount

    def scalars(self) -> "_FakeResult":
        return self

    def one(self) -> _FakeRow:
        return _FakeRow({key: 0 for key in self._column_keys()})

    def all(self) -> list:
        # Bazasiz muhitda qatorlar mavjud emas — bo'sh ro'yxat "xatosiz ishlash"
        # (endpoint qurilishi, filtrlash, javob shakli) uchun yetarli.
        return []

    def scalar(self) -> int:
        # Masalan `SELECT count(*)` kabi bitta qiymatli so'rovlar uchun (X-Total-Count).
        return 0


class FakeSession:
    def begin(self) -> _FakeTx:
        return _FakeTx()

    async def commit(self) -> None:
        """Haqiqiy sessiyada tranzaksiyani yopadi; bazasiz muhitda hech nima qilmaydi.

        Faqat `session.begin()` blokidan tashqarida yozadigan xizmatlar uchun kerak
        (masalan `app.services.quota_sync` — u avval SELECT bajarib, so'ng yozadi).
        """

    async def rollback(self) -> None:
        """Xato yuz berganda chaqiriladi; bazasiz muhitda hech nima qilmaydi."""

    async def execute(self, stmt) -> _FakeResult:
        compiled = stmt.compile(dialect=postgresql.dialect())
        CAPTURED.append(compiled.params)
        CAPTURED_SQL.append(str(compiled))
        return _FakeResult(stmt, compiled.params)

    async def scalar(self, stmt):
        """`session.scalar(...)` — bazasiz muhitda qator topilmagani kabi `None`."""
        await self.execute(stmt)
        return None

    async def get(self, entity, ident):
        """`session.get(...)` — bazasiz muhitda hech qanday qator topilmaydi."""
        return None

    async def scalars(self, stmt) -> _FakeResult:
        return await self.execute(stmt)


async def _fake_session():
    yield FakeSession()


@pytest.fixture
def client():
    """`X-API-Key` talab qilinmaydi (bo'sh), Bearer token esa har bir so'rovga
    avtomatik qo'shiladi — shuning uchun `require_user` bilan himoyalangan
    endpointlar uchun testlarda alohida sarlavha ko'rsatish shart emas.
    """
    app.dependency_overrides[get_session] = _fake_session
    CAPTURED.clear()
    CAPTURED_SQL.clear()
    with TestClient(app) as c:
        c.headers.update({"Authorization": f"Bearer {_TEST_TOKEN}"})
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Haqiqiy Postgres: `TEST_DATABASE_URL` berilganda ishlaydi, aks holda o'tkazib
# yuboriladi. `FakeSession` SQL'ni bajarmagani uchun join, cheklov va tranzaksiya
# xatolarini faqat shu testlar ushlaydi. Sxema migratsiyalardan quriladi.
# ---------------------------------------------------------------------------

_API_DIR = Path(__file__).resolve().parents[1]


def alembic_config(url: str) -> AlembicConfig:
    config = AlembicConfig(str(_API_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(_API_DIR / "migrations"))
    config.attributes["database_url"] = url
    return config


@pytest.fixture(scope="session")
def pg_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL", "")
    if not url:
        pytest.skip("TEST_DATABASE_URL o'rnatilmagan")
    # Har bir test jadvallarni tozalaydi, shuning uchun boshqa bazaga tegmasligi shart.
    if "test" not in (make_url(url).database or ""):
        pytest.exit("TEST_DATABASE_URL nomida 'test' so'zi bo'lgan baza bo'lishi kerak", returncode=2)
    command.upgrade(alembic_config(url), "head")
    return url


@dataclass
class PgContext:
    client: TestClient
    engine: AsyncEngine

    def sql(self, query: str, **params) -> list:
        """Bazaga to'g'ridan-to'g'ri so'rov: natijani tekshirish yoki holat tayyorlash uchun."""

        async def run() -> list:
            async with self.engine.begin() as conn:
                result = await conn.execute(text(query), params)
                return list(result.all()) if result.returns_rows else []

        return asyncio.run(run())


@pytest.fixture
def pg(pg_url: str):
    engine = create_async_engine(pg_url, poolclass=NullPool)
    maker = async_sessionmaker(engine, expire_on_commit=False)

    async def _session():
        async with maker() as session:
            yield session

    async def _truncate() -> None:
        tables = ", ".join(table.name for table in Base.metadata.sorted_tables)
        async with engine.begin() as conn:
            await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY"))

    asyncio.run(_truncate())
    app.dependency_overrides[get_session] = _session
    with TestClient(app) as c:
        c.headers.update({"Authorization": f"Bearer {_TEST_TOKEN}"})
        yield PgContext(client=c, engine=engine)
    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())
