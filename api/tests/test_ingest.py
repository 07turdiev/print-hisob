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


def test_printer_mac_and_job_id_are_stored(client):
    """Yangi `printerMac`/`jobId` maydonlari `printer_mac`/`job_id` ustunlariga yoziladi."""
    job = dict(PAYLOAD["jobs"][0]) | {"printerMac": "52:54:00:12:34:56", "jobId": "7"}
    client.post("/api/print-jobs", json={"computer": "X", "jobs": [job]})
    assert CAPTURED[-1]["printer_mac_m0"] == "52:54:00:12:34:56"
    assert CAPTURED[-1]["job_id_m0"] == "7"


def test_empty_printer_mac_and_job_id_become_null(client):
    job = dict(PAYLOAD["jobs"][0]) | {"printerMac": "", "jobId": ""}
    client.post("/api/print-jobs", json={"computer": "X", "jobs": [job]})
    assert CAPTURED[-1]["printer_mac_m0"] is None
    assert CAPTURED[-1]["job_id_m0"] is None


def test_missing_printer_mac_and_job_id_default_to_null(client):
    """Eski agentlar bu maydonlarni yubormaydi -> server `None` deb oladi."""
    client.post("/api/print-jobs", json=PAYLOAD)
    assert CAPTURED[-1]["printer_mac_m0"] is None
    assert CAPTURED[-1]["job_id_m0"] is None
    assert CAPTURED[-1]["printer_mac_m1"] is None
    assert CAPTURED[-1]["job_id_m1"] is None


def test_printer_registry_is_upserted_when_mac_present(client):
    """`printerMac` bo'lgan hodisalar `printers` reyestrini upsert qiladi —
    `name` yangilanuvchilar to'plamida bo'lmasligi kerak (admin nomiga tegilmaydi).
    """
    job = dict(PAYLOAD["jobs"][0]) | {"printerMac": "52:54:00:12:34:56"}
    client.post("/api/print-jobs", json={"computer": "X", "jobs": [job]})

    # Reyestr upserti print_jobs INSERT'idan OLDIN bajariladi (CAPTURED[0]).
    printer_params = CAPTURED[0]
    assert printer_params["mac_m0"] == "52:54:00:12:34:56"
    assert printer_params["last_driver_name_m0"] == "HP LaserJet M404"
    assert printer_params["last_ip_m0"] == "192.168.1.50"
    assert "name_m0" not in printer_params

    # Oxirgi bajarilgan so'rov hamon print_jobs INSERT'i (mavjud testlar shunga tayanadi).
    assert "dedup_key_m0" in CAPTURED[-1]


def test_printer_registry_not_touched_when_mac_absent(client):
    """`printerMac` yubormagan (eski) agentlar reyestrga tegmaydi."""
    client.post("/api/print-jobs", json=PAYLOAD)
    assert len(CAPTURED) == 1
    assert "dedup_key_m0" in CAPTURED[0]


def test_dedup_key_unchanged_when_printer_mac_and_job_id_present(client):
    """`dedup_key` faqat computer+user+document+printer+timestamp'ga bog'liq —
    `printerMac`/`jobId` qo'shilishi bir xil asosiy maydonlar uchun bir xil
    dedup_key hosil qilishi kerak (idempotentlik buzilmasligi uchun)."""
    base_job = PAYLOAD["jobs"][0]
    client.post("/api/print-jobs", json={"computer": "X", "jobs": [base_job]})
    key_without = CAPTURED[-1]["dedup_key_m0"]

    CAPTURED.clear()
    job_with_new_fields = dict(base_job) | {"printerMac": "52:54:00:12:34:56", "jobId": "7"}
    client.post("/api/print-jobs", json={"computer": "X", "jobs": [job_with_new_fields]})
    key_with = CAPTURED[-1]["dedup_key_m0"]

    assert key_without == key_with


# ---------------------------------------------------------------------------
# Paket hajmi chegarasi
#
# Agent uzoq uzilishdan keyin butun buferini (`MaxBufferedJobs`, standart 50 000)
# bitta to'plamda yuboradi. Server chegarasi undan kichik bo'lsa: 422 -> agent
# `2xx` olmaydi -> buferni tozalamaydi -> o'sha to'plamni abadiy qayta yuboradi
# -> bufer to'lib, eng eski hodisalar butunlay yo'qoladi.
# ---------------------------------------------------------------------------

AGENT_MAX_BUFFERED_JOBS = 50_000


def _job(i: int) -> dict:
    return {
        "user": "jsmith",
        "document": f"Hisobot-{i}.docx",
        "printer": "HP LaserJet M404",
        "printerIp": "192.168.1.50",
        "pages": 1,
        "timestamp": "2026-07-10T14:32:10Z",
        "success": True,
        "reason": "",
    }


def test_batch_limit_exceeds_agent_buffer():
    """Server chegarasi agent buferidan katta bo'lishi shart."""
    from app.schemas import MAX_JOBS_PER_BATCH

    assert MAX_JOBS_PER_BATCH > AGENT_MAX_BUFFERED_JOBS


def test_accepts_batch_larger_than_5000(client):
    """Avvalgi 5000 chegarasidan katta to'plam ham qabul qilinishi kerak."""
    jobs = [_job(i) for i in range(6000)]
    r = client.post("/api/print-jobs", json={"computer": "DESKTOP-ABC123", "jobs": jobs})
    assert r.status_code == 201
    assert r.json()["received"] == 6000


def test_rejects_batch_above_hard_limit(client):
    """Chegaradan oshgan to'plam rad etiladi — bu himoya saqlanib qolgan."""
    from app.schemas import MAX_JOBS_PER_BATCH

    jobs = [_job(i) for i in range(MAX_JOBS_PER_BATCH + 1)]
    r = client.post("/api/print-jobs", json={"computer": "DESKTOP-ABC123", "jobs": jobs})
    assert r.status_code == 422
