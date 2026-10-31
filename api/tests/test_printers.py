"""Printerlar reyestri uchun baza talab qilmaydigan testlar.

Reyestr endi MAC'ga bog'lanmagan: qurilma (`printer_devices`) va uni tanib
oladigan nishonlar (`printer_aliases`) ajratilgan. Birlashtirish va haqiqiy
guruhlash integratsion sinovda tekshiriladi \u2014 bu yerda endpointlar shakli,
himoya va SQL tuzilishi.
"""

from fastapi.testclient import TestClient

from app.main import app

PERIOD = {"period_type": "quarter", "year": 2026, "period_no": 3}


# ---------------------------------------------------------------------------
# Ro'yxat
# ---------------------------------------------------------------------------


def test_list_printers_builds_without_error(client):
    r = client.get("/api/printers")
    assert r.status_code == 200
    assert r.json() == []


def test_list_printers_without_bearer_rejected():
    with TestClient(app) as c:
        r = c.get("/api/printers")
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Nom qo'yish
# ---------------------------------------------------------------------------


def test_rename_missing_printer_returns_404(client):
    r = client.put("/api/printers/404404", json={"name": "Buxgalteriya printeri"})
    assert r.status_code == 404
    assert "topilmadi" in r.json()["detail"]


def test_rename_requires_numeric_id(client):
    """Eski API MAC bo'yicha ishlardi; endi kalit \u2014 qurilma id'si."""
    r = client.put("/api/printers/52:54:00:12:34:56", json={"name": "X"})
    assert r.status_code == 422


def test_rename_without_bearer_rejected():
    with TestClient(app) as c:
        r = c.put("/api/printers/1", json={"name": "X"})
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Birlashtirish
# ---------------------------------------------------------------------------


def test_merge_into_itself_rejected(client):
    r = client.post("/api/printers/5/merge", json={"sourceId": 5})
    assert r.status_code == 400
    assert "o'ziga" in r.json()["detail"]


def test_merge_missing_printer_returns_404(client):
    r = client.post("/api/printers/5/merge", json={"sourceId": 6})
    assert r.status_code == 404


def test_merge_without_bearer_rejected():
    with TestClient(app) as c:
        r = c.post("/api/printers/1/merge", json={"sourceId": 2})
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Reyestrni qayta qurish
# ---------------------------------------------------------------------------


def test_reconcile_on_empty_history(client):
    r = client.post("/api/printers/reconcile")
    assert r.status_code == 200
    assert r.json() == {"created": 0, "total": 0}


# ---------------------------------------------------------------------------
# Statistika
# ---------------------------------------------------------------------------


def test_stats_printers_builds_without_error(client):
    r = client.get("/api/stats/printers", params=PERIOD)
    assert r.status_code == 200
    assert r.json() == []


def test_stats_printers_groups_by_resolved_device(client):
    """Guruhlash qurilma bo'yicha: yozuv mac -> ip -> nom tartibida bog'lanadi."""
    from sqlalchemy.dialects import postgresql

    from app.main import _printer_usage_subquery
    from app.models import PrintJob

    compiled = str(
        _printer_usage_subquery(PrintJob.printed_at.isnot(None)).compile(
            dialect=postgresql.dialect()
        )
    )
    # Uchta nishon jadvali uchta LEFT JOIN bilan ulanadi.
    assert compiled.count("LEFT OUTER JOIN printer_aliases") == 3
    # Guruhlash kaliti \u2014 topilgan qurilma, zaxirada xom nom.
    assert "coalesce(printer_aliases_1.device_id" in compiled
    assert "print_jobs.printer)" in compiled
    assert "GROUP BY" in compiled


def test_stats_top_printers_uses_printer_identity(client):
    r = client.get("/api/stats/top", params=PERIOD)
    assert r.status_code == 200
    assert r.json() == {"printers": [], "computers": [], "departments": []}
