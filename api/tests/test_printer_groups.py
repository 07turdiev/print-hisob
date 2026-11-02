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


def test_login_without_group_is_unrestricted():
    """Guruhga kirmagan xodim cheklanmaydi — cheklov faqat ongli qo'yiladi."""
    assert _allowed_for("e.turdiyev", {}, blocked=False) == ["*"]


def test_policy_all_sends_star():
    policies = {"e.turdiyev": _policy(pg.ALL)}
    assert _allowed_for("e.turdiyev", policies, blocked=False) == ["*"]


def test_policy_allowed_sends_tokens():
    """Qurilmaning barcha nishonlari yuboriladi: agent qaysinisini ko'rishi noma'lum."""
    policies = {"e.turdiyev": _policy(pg.ALLOWED, ("52:54:00:12:34:56", "192.168.1.50"))}
    assert _allowed_for("e.turdiyev", policies, blocked=False) == [
        "52:54:00:12:34:56",
        "192.168.1.50",
    ]


def test_policy_allowed_without_printers_blocks_everything():
    """`allowed` tanlangan, lekin printer belgilanmagan — hech qaysisi ruxsat emas.

    Bu ataylab `["*"]` emas: admin “faqat belgilanganlar” deb aytgan, shuning
    uchun ro'yxat bo'sh bo'lsa javob ham bo'sh bo'lishi kerak.
    """
    assert _allowed_for("e.turdiyev", {"e.turdiyev": _policy(pg.ALLOWED)}, blocked=False) == []


def test_policy_none_sends_empty_list():
    assert _allowed_for("e.turdiyev", {"e.turdiyev": _policy(pg.NONE)}, blocked=False) == []


def test_individual_block_overrides_group_policy():
    """Shaxsiy “Bloklash” guruh ruxsatidan ustun turadi.

    Guruh to'liq ruxsat bergan bo'lsa ham bloklangan odam chiqara olmaydi —
    shaxsiy qaror aniqroq va uni tasodifan guruh bekor qilmasligi kerak.
    """
    policies = {"e.turdiyev": _policy(pg.ALL)}
    assert _allowed_for("e.turdiyev", policies, blocked=True) == []


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


@pytest.mark.parametrize("policy", ["all", "allowed", "none"])
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
