"""Printerning MAC yoki IP manzili o'zgarganda tizim nima qiladi (haqiqiy Postgres).

Agent ruxsatni MAC, IP yoki nomdan istalgan biri mos kelganda beradi. Shu sababli
ruxsat ro'yxatida MAC ham, joriy IP ham turadi: biri o'zgarsa, ikkinchisi ishlaydi.
"""

from datetime import datetime, timezone

from alembic import command

from conftest import alembic_config
from test_pg_agent_contract import job, send_jobs, sync

NOW = datetime.now(timezone.utc)
OLD_MAC, OLD_IP = "40:F8:DF:64:C6:97", "192.168.20.93"
NEW_MAC, NEW_IP = "40:F8:DF:AA:BB:CC", "192.168.20.200"


def agent_allows(allowed: list[str], mac: str = "", ip: str = "", name: str = "") -> bool:
    """Agent hujjatidagi `IsPrinterAllowed` mantig'i."""
    hex_only = lambda v: "".join(c for c in v if c in "0123456789abcdefABCDEF").upper()  # noqa: E731
    if "*" in allowed:
        return True
    return any(
        (mac and len(hex_only(mac)) == 12 and hex_only(t) == hex_only(mac))
        or (ip and t == ip)
        or (name and t.lower() == name.lower())
        for t in allowed
    )


def printers(pg) -> list[dict]:
    return pg.client.get("/api/printers").json()


def make_public(pg, device_id: int) -> None:
    pg.client.put(
        "/api/printer-access", json={"publicDeviceIds": [device_id], "restrictDefault": True}
    ).raise_for_status()


def allowed_now(pg) -> list[str]:
    return sync(pg, "ali").json()["allowedPrinters"]


def violations(pg) -> list[dict]:
    period = {"period_type": "quarter", "year": NOW.year, "period_no": (NOW.month - 1) // 3 + 1}
    return pg.client.get("/api/printer-groups/violations", params=period).json()


def test_ip_change_with_same_mac_is_followed_automatically(pg):
    send_jobs(pg, job(1, printerMac=OLD_MAC, printerIp=OLD_IP))
    device_id = printers(pg)[0]["id"]
    make_public(pg, device_id)

    send_jobs(pg, job(2, printerMac=OLD_MAC, printerIp=NEW_IP))

    assert len(printers(pg)) == 1
    assert printers(pg)[0]["lastIp"] == NEW_IP
    allowed = allowed_now(pg)
    assert NEW_IP in allowed and OLD_IP not in allowed


def test_failed_job_on_stale_ip_does_not_move_the_current_ip(pg):
    send_jobs(pg, job(1, printerMac=OLD_MAC, printerIp=OLD_IP))
    send_jobs(pg, job(2, printerMac=OLD_MAC, printerIp=NEW_IP, success=False, pages=0))
    assert printers(pg)[0]["lastIp"] == OLD_IP


def test_job_without_mac_is_matched_by_ip(pg):
    """Boshqa pod-tarmoqdagi kompyuter MAC'ni ko'rmaydi, u IP bo'yicha tanib olinadi."""
    send_jobs(pg, job(1, printerMac=OLD_MAC, printerIp=OLD_IP))
    send_jobs(pg, job(2, printer="Boshqa nom", printerMac="", printerIp=OLD_IP))
    assert len(printers(pg)) == 1


def test_network_card_replaced_keeps_printing_and_needs_a_merge(pg):
    """MAC almashdi, IP o'sha: chop etish to'xtamaydi, statistika ikkiga bo'linadi."""
    send_jobs(pg, job(1, printerMac=OLD_MAC, printerIp=OLD_IP))
    old_id = printers(pg)[0]["id"]
    make_public(pg, old_id)

    assert agent_allows(allowed_now(pg), mac=NEW_MAC, ip=OLD_IP)

    send_jobs(pg, job(2, printerMac=NEW_MAC, printerIp=OLD_IP))
    devices = printers(pg)
    assert len(devices) == 2

    # Birlashtirilguncha yangi yozuv hisobotda ruxsatsiz printer bo'lib ko'rinadi.
    assert len(violations(pg)) == 1

    new_id = next(d["id"] for d in devices if d["id"] != old_id)
    pg.client.post(f"/api/printers/{old_id}/merge", json={"sourceId": new_id}).raise_for_status()

    assert len(printers(pg)) == 1
    allowed = allowed_now(pg)
    assert NEW_MAC in allowed and OLD_MAC in allowed
    assert agent_allows(allowed, mac=NEW_MAC)
    assert violations(pg) == []


def test_printer_replaced_with_new_mac_and_ip_is_blocked_until_admin_acts(pg):
    send_jobs(pg, job(1, printerMac=OLD_MAC, printerIp=OLD_IP))
    old_id = printers(pg)[0]["id"]
    make_public(pg, old_id)

    assert not agent_allows(allowed_now(pg), mac=NEW_MAC, ip=NEW_IP, name="Canon Katta")

    # Admin yangi qurilmani eskisiga qo'shadi va ruxsat darhol tiklanadi.
    send_jobs(pg, job(2, printerMac=NEW_MAC, printerIp=NEW_IP))
    new_id = next(d["id"] for d in printers(pg) if d["id"] != old_id)
    pg.client.post(f"/api/printers/{old_id}/merge", json={"sourceId": new_id}).raise_for_status()
    assert agent_allows(allowed_now(pg), mac=NEW_MAC)


def test_merge_keeps_the_public_list_and_history(pg):
    send_jobs(pg, job(1, printerMac=OLD_MAC, printerIp=OLD_IP, pages=2))
    send_jobs(pg, job(2, printerMac=NEW_MAC, printerIp=NEW_IP, pages=3))
    source, target = sorted(d["id"] for d in printers(pg))
    pg.client.put("/api/printer-access", json={"publicDeviceIds": [source]}).raise_for_status()

    pg.client.post(f"/api/printers/{target}/merge", json={"sourceId": source}).raise_for_status()

    assert pg.client.get("/api/printer-access").json()["publicDeviceIds"] == [target]
    period = {"period_type": "quarter", "year": NOW.year, "period_no": (NOW.month - 1) // 3 + 1}
    stats = pg.client.get("/api/stats/printers", params=period).json()
    assert [(s["deviceId"], s["pages"]) for s in stats] == [(target, 5)]


def test_models_and_migrations_agree(pg, pg_url):
    """Modelga ustun qo'shilib migratsiya yozilmasa, shu test yiqiladi."""
    command.check(alembic_config(pg_url))
