"""`GET/PUT /api/printers` va `/api/stats/printers` uchun baza talab qilmaydigan testlar."""

from fastapi.testclient import TestClient

from app.main import app

PERIOD = {"period_type": "quarter", "year": 2026, "period_no": 3}


def test_list_printers_builds_without_error(client):
    r = client.get("/api/printers")
    assert r.status_code == 200
    assert r.json() == []


def test_list_printers_accepts_search_query(client):
    r = client.get("/api/printers", params={"q": "Canon"})
    assert r.status_code == 200


def test_list_printers_without_bearer_rejected():
    with TestClient(app) as c:
        r = c.get("/api/printers")
    assert r.status_code == 401


def test_put_printer_name_sets_name(client):
    from conftest import CAPTURED

    r = client.put("/api/printers/52:54:00:12:34:56", json={"name": "Buxgalteriya printeri"})
    assert r.status_code == 200
    body = r.json()
    assert body["mac"] == "52:54:00:12:34:56"
    assert body["name"] == "Buxgalteriya printeri"
    assert body["displayName"] == "Buxgalteriya printeri"

    params = CAPTURED[0]
    assert params["mac"] == "52:54:00:12:34:56"
    assert params["name"] == "Buxgalteriya printeri"


def test_put_printer_name_empty_string_clears_name(client):
    """Bo'sh nom -> NULL (reyestr nomini tozalaydi)."""
    from conftest import CAPTURED

    r = client.put("/api/printers/52:54:00:12:34:56", json={"name": ""})
    assert r.status_code == 200
    assert CAPTURED[0]["name"] is None


def test_put_printer_name_without_bearer_rejected():
    with TestClient(app) as c:
        r = c.put("/api/printers/52:54:00:12:34:56", json={"name": "X"})
    assert r.status_code == 401


def test_stats_printers_builds_without_error(client):
    r = client.get("/api/stats/printers", params=PERIOD)
    assert r.status_code == 200
    assert r.json() == []


def test_stats_printers_sql_groups_by_mac_coalesced_identity(client):
    """Kompilyatsiya qilingan SQL `COALESCE(printer_mac, printer)` bo'yicha
    guruhlaydi va `printers` jadvaliga LEFT JOIN qiladi."""
    from sqlalchemy.dialects import postgresql

    from app.main import _printer_display_name_expr, _printer_usage_subquery
    from app.models import Printer, PrintJob

    usage = _printer_usage_subquery(PrintJob.printed_at.isnot(None))
    compiled = str(usage.compile(dialect=postgresql.dialect()))
    assert "coalesce(print_jobs.printer_mac, print_jobs.printer)" in compiled
    assert "GROUP BY" in compiled

    from sqlalchemy import select

    stmt = select(usage.c.mac, _printer_display_name_expr(usage)).outerjoin(
        Printer, Printer.mac == usage.c.mac
    )
    compiled_stmt = str(stmt.compile(dialect=postgresql.dialect()))
    assert "LEFT OUTER JOIN printers" in compiled_stmt


def test_stats_top_printers_uses_printer_identity(client):
    r = client.get("/api/stats/top", params=PERIOD)
    assert r.status_code == 200
    assert r.json() == {"printers": [], "computers": [], "departments": []}
