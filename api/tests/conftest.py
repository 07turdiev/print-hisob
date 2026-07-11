"""Yangi endpoint testlari uchun umumiy, bazasiz (DB-free) yordamchilar.

`test_ingest.py` o'ziga xos oddiyroq stub bilan ishlaydi (faqat `execute()` va
dedup_key asosidagi rowcount). Bu yerdagi `FakeSession` esa `ad-sync`, `quotas`
va `stats` endpointlari uchun kerak bo'lgan `session.scalars()`, `.one()` va
`.all()` metodlarini ham qo'llab-quvvatlaydi — baribir haqiqiy bazaga ulanmaydi,
faqat SQL'ni kompilyatsiya qilib parametrlarni yozib oladi.
"""

import os
import re
from datetime import datetime, timedelta, timezone

os.environ.setdefault("AUTO_CREATE_TABLES", "false")
os.environ.setdefault("API_KEY", "")
# Dashboard autentifikatsiyasi (JWT) — testlar shu maxfiy kalit bilan token yasaydi.
os.environ.setdefault("AUTH_USERNAME", "admin")
os.environ.setdefault("AUTH_PASSWORD", "test-parol")
os.environ.setdefault("JWT_SECRET", "test-uchun-uzun-maxfiy-kalit-32-bayt-yoki-kop")

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql

from app.config import settings
from app.db import get_session
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

    async def execute(self, stmt) -> _FakeResult:
        params = stmt.compile(dialect=postgresql.dialect()).params
        CAPTURED.append(params)
        return _FakeResult(stmt, params)

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
    with TestClient(app) as c:
        c.headers.update({"Authorization": f"Bearer {_TEST_TOKEN}"})
        yield c
    app.dependency_overrides.clear()
