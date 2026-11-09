"""Xodimlar guruhlari: siyosat qoidalari va endpoint shakli (bazasiz).

Siyosatning agentga qanday yetishi — `_allowed_for` — sof funksiya, shuning
uchun u shu yerda to'liq tekshiriladi. Jadvallar bilan ishlash integratsion
sinovda (haqiqiy baza) tekshirilgan.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import printer_groups as pg
from app.services.quota_sync import BLOCKED, UNLIMITED, _allowed_for


def _policy(policy: str, tokens: tuple[str, ...] = ()) -> pg.LoginPolicy:
    return pg.LoginPolicy(group_id=1, group_name="Sinov", policy=policy, tokens=tokens)


# ---------------------------------------------------------------------------
# Siyosat -> agentga nima ketadi
# ---------------------------------------------------------------------------


PUBLIC = ["40:F8:DF:64:C6:97", "192.168.20.93"]


def test_login_without_group_gets_default_list():
    """Guruhga kirmagan xodim standart qoidani oladi."""
    assert _allowed_for("e.turdiyev", {}, blocked=False, default=PUBLIC) == PUBLIC


def test_login_without_group_is_unrestricted_when_restriction_off():
    assert _allowed_for("e.turdiyev", {}, blocked=False, default=["*"]) == ["*"]


def test_policy_all_sends_star_even_when_restricted():
    """To'liq ruxsat — istisno: standart cheklov unga ta'sir qilmaydi."""
    policies = {"e.turdiyev": _policy(pg.ALL)}
    assert _allowed_for("e.turdiyev", policies, blocked=False, default=PUBLIC) == ["*"]


def test_policy_allowed_sends_tokens():
    tokens = (*PUBLIC, "Canon MF3010")
    policies = {"e.turdiyev": _policy(pg.ALLOWED, tokens)}
    assert _allowed_for("e.turdiyev", policies, blocked=False, default=PUBLIC) == list(tokens)


def test_policy_allowed_without_printers_blocks_everything():
    """`allowed` guruhda nishon umuman bo'lmasa — hech qaysi printer ruxsat emas.

    Bu ataylab `["*"]` emas: admin “ma'lum printerlar” deb aytgan, shuning
    uchun ro'yxat bo'sh bo'lsa javob ham bo'sh bo'lishi kerak.
    """
    policies = {"e.turdiyev": _policy(pg.ALLOWED)}
    assert _allowed_for("e.turdiyev", policies, blocked=False, default=["*"]) == []


def test_individual_block_overrides_group_policy():
    """Shaxsiy “Bloklash” guruh ruxsatidan ustun turadi.

    Guruh to'liq ruxsat bergan bo'lsa ham bloklangan odam chiqara olmaydi —
    shaxsiy qaror aniqroq va uni tasodifan guruh bekor qilmasligi kerak.
    """
    policies = {"e.turdiyev": _policy(pg.ALL)}
    assert _allowed_for("e.turdiyev", policies, blocked=True, default=PUBLIC) == []


# ---------------------------------------------------------------------------
# Standart qoida
# ---------------------------------------------------------------------------


def test_default_access_sends_star_when_off():
    access = pg.DefaultAccess(restrict=False, device_ids=(1,), tokens=tuple(PUBLIC))
    assert access.allowed_printers() == ["*"]


def test_default_access_sends_public_tokens_when_on():
    access = pg.DefaultAccess(restrict=True, device_ids=(1,), tokens=tuple(PUBLIC))
    assert access.allowed_printers() == PUBLIC


def test_default_access_fails_open_without_tokens():
    """Ma'lumot xatosi tufayli butun idora chop etishdan to'xtab qolmasin."""
    access = pg.DefaultAccess(restrict=True, device_ids=(1,), tokens=())
    assert access.allowed_printers() == ["*"]


# ---------------------------------------------------------------------------
# Agentga qaysi nishonlar ketadi
# ---------------------------------------------------------------------------


def test_tokens_use_only_current_ip():
    """Eski IP'ni keyin boshqa printer olgan bo'lishi mumkin — u ochilib qolmasin."""
    aliases = [
        ("mac", "40:F8:DF:63:E7:F8"),
        ("ip", "192.168.20.122"),
        ("ip", "192.168.20.146"),
    ]
    assert pg.device_tokens(aliases, "192.168.20.122") == ["40:F8:DF:63:E7:F8", "192.168.20.122"]


def test_tokens_fall_back_to_ip_aliases_without_current_ip():
    assert pg.device_tokens([("ip", "192.168.20.93")], None) == ["192.168.20.93"]


def test_tokens_skip_names_for_network_printer():
    """"Canon Katta" nomi 10 xil printerda uchraydi — nom bilan ruxsat berilmaydi."""
    aliases = [("mac", "40:F8:DF:63:E7:F8"), ("name", "Canon Katta")]
    assert pg.device_tokens(aliases, None) == ["40:F8:DF:63:E7:F8"]


def test_tokens_use_name_for_usb_and_virtual_printers():
    assert pg.device_tokens([("name", "Microsoft Print to PDF")], None) == [
        "Microsoft Print to PDF"
    ]


def test_port_name_as_last_ip_is_ignored():
    assert pg.device_tokens([("ip", "192.168.20.93")], "USB001") == ["192.168.20.93"]


def test_blocked_and_unlimited_markers_unchanged():
    """Agent shartnomasidagi maxsus qiymatlar o'zgarmaganiga kafolat."""
    assert (UNLIMITED, BLOCKED) == (-1, 0)


# ---------------------------------------------------------------------------
# Endpointlar
# ---------------------------------------------------------------------------


def test_list_groups_builds_without_error(client):
    r = client.get("/api/printer-groups")
    assert r.status_code == 200
    assert r.json() == []


def test_list_groups_without_bearer_rejected():
    with TestClient(app) as c:
        r = c.get("/api/printer-groups")
    assert r.status_code == 401


def test_access_defaults_to_unrestricted(client):
    r = client.get("/api/printer-access")
    assert r.status_code == 200
    assert r.json() == {"restrictDefault": False, "publicDeviceIds": []}


def test_access_cannot_be_enabled_without_public_printers(client):
    """Bo'sh ro'yxat bilan cheklovni yoqish hammani to'xtatib qo'ygan bo'lardi."""
    r = client.put("/api/printer-access", json={"restrictDefault": True, "publicDeviceIds": []})
    assert r.status_code == 422


def test_access_requires_bearer():
    with TestClient(app) as c:
        r = c.get("/api/printer-access")
    assert r.status_code == 401


def test_quota_sync_is_unrestricted_until_enabled(client):
    """Tugma yoqilmaguncha agentlar avvalgidek `["*"]` oladi."""
    body = {
        "computer": "PC-1",
        "periodKey": "2026-Q4",
        "timestamp": "2026-11-09T09:15:00Z",
        "users": [{"user": "jane", "pagesUsedHere": 1, "pagesUsed": 1, "limit": -1}],
    }
    r = client.post("/api/print-quotas", json=body)
    assert r.status_code == 200
    assert r.json()["allowedPrinters"] == ["*"]
    assert r.json()["users"][0]["allowedPrinters"] == ["*"]


def test_violations_query_covers_ungrouped_only_when_public_list_exists():
    from datetime import datetime, timezone

    from sqlalchemy.dialects import postgresql

    start = datetime(2026, 10, 1, tzinfo=timezone.utc)
    end = datetime(2026, 11, 1, tzinfo=timezone.utc)
    with_default = str(
        pg.violations_stmt(start, end, include_default=True).compile(dialect=postgresql.dialect())
    )
    without_default = str(
        pg.violations_stmt(start, end, include_default=False).compile(dialect=postgresql.dialect())
    )
    assert "printer_group_members.id IS NULL" in with_default
    assert "printer_group_members.id IS NULL" not in without_default


@pytest.mark.parametrize("policy", ["all", "allowed"])
def test_valid_policies_accepted_by_schema(policy):
    from app.schemas import PrinterGroupIn

    assert PrinterGroupIn(name="Sinov", policy=policy).policy == policy


def test_unknown_policy_rejected(client):
    r = client.post("/api/printer-groups", json={"name": "Sinov", "policy": "hammasi"})
    assert r.status_code == 422


def test_partial_update_distinguishes_absent_from_empty():
    """Maydon yuborilmasa tegilmaydi, bo'sh ro'yxat yuborilsa tozalanadi.

    Ikkisi bir xil emas: `logins: []` “a'zolarni olib tashla” degani, maydonning
    yo'qligi esa “a'zolarga tegma”.
    """
    from app.schemas import PrinterGroupPatchIn

    assert "logins" not in PrinterGroupPatchIn(name="X").model_fields_set
    assert "logins" in PrinterGroupPatchIn(logins=[]).model_fields_set
