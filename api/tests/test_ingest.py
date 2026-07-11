"""Baza talab qilmaydigan testlar: sessiya stub bilan almashtiriladi."""

import os

os.environ.setdefault("AUTO_CREATE_TABLES", "false")
os.environ.setdefault("API_KEY", "")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql

from app.db import get_session
from app.main import app

CAPTURED: list[dict] = []


class _FakeResult:
    def __init__(self, rowcount: int) -> None:
        self.rowcount = rowcount


class _FakeTx:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class _FakeSession:
    """`execute()` ga kelgan SQL parametrlarini yozib oladi."""

    def begin(self):
        return _FakeTx()

    async def execute(self, stmt):
        params = stmt.compile(dialect=postgresql.dialect()).params
        CAPTURED.append(params)
        return _FakeResult(len([k for k in params if k.startswith("dedup_key")]))


async def _fake_session():
    yield _FakeSession()


@pytest.fixture
def client():
    app.dependency_overrides[get_session] = _fake_session
    CAPTURED.clear()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


PAYLOAD = {
    "computer": "DESKTOP-ABC123",
    "jobs": [
        {
            "user": "jsmith",
            "document": "Quarterly Report.docx",
            "printer": "HP LaserJet M404",
            "printerIp": "192.168.1.50",
            "pages": 3,
            "timestamp": "2026-07-10T14:32:10.1234567+00:00",
            "success": True,
            "reason": "",
        },
        {
            "user": "agoncalves",
            "document": "Invoice_9081.pdf",
            "printer": "Canon MF743Cdw",
            "printerIp": "",
            "pages": 0,
            "timestamp": "2026-07-10T14:35:02.9876543+00:00",
            "success": False,
            "reason": "Print job was canceled or deleted before completing",
        },
    ],
}


def test_ingest_returns_counts(client):
    r = client.post("/api/print-jobs", json=PAYLOAD)
    assert r.status_code == 201
    assert r.json() == {
        "computer": "DESKTOP-ABC123",
        "received": 2,
        "inserted": 2,
        "duplicates": 0,
    }


def test_duplex_defaults_to_false_when_omitted(client):
    """Eski agentlar `duplex` maydonini yubormaydi — server `False` deb oladi."""
    client.post("/api/print-jobs", json=PAYLOAD)
    assert CAPTURED[-1]["duplex_m0"] is False
    assert CAPTURED[-1]["duplex_m1"] is False


def test_duplex_true_is_stored(client):
    job = dict(PAYLOAD["jobs"][0]) | {"duplex": True}
    client.post("/api/print-jobs", json={"computer": "X", "jobs": [job]})
    assert CAPTURED[-1]["duplex_m0"] is True


def test_empty_strings_become_null(client):
    client.post("/api/print-jobs", json=PAYLOAD)
    params = CAPTURED[-1]
    assert params["printer_ip_m1"] is None
    assert params["reason_m0"] is None
    assert params["printer_ip_m0"] == "192.168.1.50"


def test_dotnet_seven_digit_fraction_is_truncated(client):
    client.post("/api/print-jobs", json=PAYLOAD)
    printed_at = CAPTURED[-1]["printed_at_m0"]
    assert printed_at.isoformat() == "2026-07-10T14:32:10.123456+00:00"


def test_naive_timestamp_treated_as_utc(client):
    job = dict(PAYLOAD["jobs"][0]) | {"timestamp": "2026-07-10T14:32:10.1234567"}
    client.post("/api/print-jobs", json={"computer": "X", "jobs": [job]})
    assert CAPTURED[-1]["printed_at_m0"].utcoffset().total_seconds() == 0


def test_plain_z_timestamp_without_fraction_parses_as_utc(client):
    """Yangi agent kasr soniyasiz `...Z` formatda ham vaqt yuborishi mumkin."""
    job = dict(PAYLOAD["jobs"][0]) | {"timestamp": "2026-07-11T12:35:01Z"}
    r = client.post("/api/print-jobs", json={"computer": "X", "jobs": [job]})
    assert r.status_code == 201
    printed_at = CAPTURED[-1]["printed_at_m0"]
    assert printed_at.isoformat() == "2026-07-11T12:35:01+00:00"


def test_document_pages_is_stored(client):
    """`documentPages` -> `document_pages` (fayldagi sahifa soni, `pages`dan alohida)."""
    job = dict(PAYLOAD["jobs"][0]) | {"pages": 2, "documentPages": 3}
    client.post("/api/print-jobs", json={"computer": "X", "jobs": [job]})
    assert CAPTURED[-1]["pages_m0"] == 2
    assert CAPTURED[-1]["document_pages_m0"] == 3


def test_document_pages_defaults_to_zero_when_omitted(client):
    """Eski agentlar `documentPages`ni yubormaydi -> server `0` deb oladi."""
    client.post("/api/print-jobs", json=PAYLOAD)
    assert CAPTURED[-1]["document_pages_m0"] == 0
    assert CAPTURED[-1]["document_pages_m1"] == 0


def test_pages_is_stored_as_sent_without_transformation(client):
    """`pages` endi tayyor qog'oz (varaq) soni — server hech qanday
    duplex-ga bog'liq yaxlitlash/bo'lish qilmaydi, kelgan qiymat aynan saqlanadi.
    """
    job = dict(PAYLOAD["jobs"][0]) | {"pages": 2, "documentPages": 3, "duplex": True}
    client.post("/api/print-jobs", json={"computer": "X", "jobs": [job]})
    assert CAPTURED[-1]["pages_m0"] == 2


def test_duplicates_inside_one_batch_are_collapsed(client):
    body = {"computer": "X", "jobs": [PAYLOAD["jobs"][0], PAYLOAD["jobs"][0]]}
    r = client.post("/api/print-jobs", json=body)
    assert r.json()["received"] == 2
    assert r.json()["inserted"] == 1
    assert r.json()["duplicates"] == 1


def test_empty_job_list_is_accepted(client):
    r = client.post("/api/print-jobs", json={"computer": "X", "jobs": []})
    assert r.status_code == 201
    assert r.json()["inserted"] == 0
    assert CAPTURED == []


@pytest.mark.parametrize(
    "job",
    [
        {"user": "a"},
        dict(PAYLOAD["jobs"][0]) | {"pages": -1},
        dict(PAYLOAD["jobs"][0]) | {"timestamp": "kecha"},
        dict(PAYLOAD["jobs"][0]) | {"success": "ehtimol"},
    ],
)
def test_invalid_jobs_rejected(client, job):
    r = client.post("/api/print-jobs", json={"computer": "X", "jobs": [job]})
    assert r.status_code == 422
