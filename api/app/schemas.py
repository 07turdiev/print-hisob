import hashlib
from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StringConstraints, model_validator

from app.periods import PeriodType, validate_period_no


def _empty_to_none(value: object) -> object:
    if isinstance(value, str) and not value.strip():
        return None
    return value


def _text(max_length: int):
    return Annotated[str, StringConstraints(strip_whitespace=True, max_length=max_length)]


def _optional_text(max_length: int):
    """Bo'sh satr ("") NULL sifatida yoziladi."""
    return Annotated[_text(max_length) | None, BeforeValidator(_empty_to_none)]


class PrintJobIn(BaseModel):
    """Bitta chop etish hodisasi (agent yuboradigan camelCase kalitlar)."""

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "examples": [
                {
                    "user": "jsmith",
                    "document": "Quarterly Report.docx",
                    "printer": "HP LaserJet M404",
                    "printerIp": "192.168.1.50",
                    "pages": 2,
                    "documentPages": 3,
                    "duplex": True,
                    "timestamp": "2026-07-10T14:32:10.1234567+00:00",
                    "success": True,
                    "reason": "",
                }
            ]
        },
    )

    user_name: _text(255) = Field(alias="user")
    document: _text(8192)
    printer: _text(255)
    printer_ip: _optional_text(255) = Field(default=None, alias="printerIp")
    # Agent duplex hisobini o'zi qilib, jismoniy varaq (qog'oz) sonini tayyor
    # holda yuboradi — masalan 3 sahifali duplex hujjat uchun `pages=2`.
    pages: int = Field(default=0, ge=0, description="Qog'oz (varaq) soni — duplex hisobi allaqachon qo'llangan")
    # Hujjatdagi sahifalar soni (fayl ichidagi sahifa soni) — faqat ma'lumot
    # uchun, sarf hisobida ishlatilmaydi.
    document_pages: int = Field(
        default=0, ge=0, alias="documentPages", description="Fayldagi sahifalar soni (varaq emas, faqat ma'lumot uchun)"
    )
    # Ikki tomonlama chop etish — faqat ma'lumot uchun (allaqachon `pages`da
    # hisobga olingan). Eski agentlar bu maydonni yubormasligi mumkin, standart `False`.
    duplex: bool = Field(
        default=False, description="Ikki tomonlama (duplex) chop etilganmi (ma'lumot uchun)"
    )
    # .NET `DateTimeOffset.ToString("o")` 7 xonali kasr beradi; pydantic uni
    # 6 xonaga kesib qabul qiladi (Postgres timestamptz aniqligi ham shu).
    timestamp: datetime
    success: bool
    reason: _optional_text(4096) = None

    def normalized_timestamp(self) -> datetime:
        """Vaqt mintaqasi ko'rsatilmagan bo'lsa UTC deb hisoblaymiz."""
        if self.timestamp.tzinfo is None:
            return self.timestamp.replace(tzinfo=timezone.utc)
        return self.timestamp

    def dedup_key(self, computer: str) -> str:
        ts = self.normalized_timestamp().astimezone(timezone.utc).isoformat()
        raw = "\x1f".join([computer, self.user_name, self.document, self.printer, ts])
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class PrintJobBatch(BaseModel):
    """POST /api/print-jobs tanasi."""

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "examples": [
                {
                    "computer": "DESKTOP-ABC123",
                    "jobs": [
                        {
                            "user": "jsmith",
                            "document": "Quarterly Report.docx",
                            "printer": "HP LaserJet M404",
                            "printerIp": "192.168.1.50",
                            "pages": 2,
                            "documentPages": 3,
                            "duplex": True,
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
                            "documentPages": 0,
                            "timestamp": "2026-07-10T14:35:02.9876543+00:00",
                            "success": False,
                            "reason": "Print job was canceled or deleted before completing",
                        },
                    ],
                }
            ]
        },
    )

    computer: _text(255) = Field(description="Hodisalarni yuborgan ish stantsiyasi nomi")
    jobs: list[PrintJobIn] = Field(
        default_factory=list,
        max_length=5000,
        description="Chop etish hodisalari (eng ko'pi 5000 ta)",
    )


class IngestResult(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "computer": "DESKTOP-ABC123",
                    "received": 2,
                    "inserted": 2,
                    "duplicates": 0,
                }
            ]
        }
    )

    computer: str
    received: int = Field(description="Paketda kelgan hodisalar soni")
    inserted: int = Field(description="Bazaga yangi qo'shilgan qatorlar soni")
    duplicates: int = Field(description="Avval yozilgani uchun o'tkazib yuborilganlar")


class PrintJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    computer: str
    user_name: str = Field(serialization_alias="user")
    document: str
    printer: str
    printer_ip: str | None = Field(serialization_alias="printerIp")
    pages: int
    document_pages: int = Field(default=0, serialization_alias="documentPages")
    duplex: bool = False
    printed_at: datetime = Field(serialization_alias="timestamp")
    success: bool
    reason: str | None


# ---------------------------------------------------------------------------
# AD (Active Directory) sinxronizatsiyasi — xodimlar
# ---------------------------------------------------------------------------


class EmployeeIn(BaseModel):
    """Bitta xodim yozuvi (AD sinxronizatsiya skripti yuboradigan camelCase kalitlar)."""

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "examples": [
                {
                    "login": "jsmith",
                    "fullName": "John Smith",
                    "department": "Buxgalteriya",
                    "position": "Bosh mutaxassis",
                    "active": True,
                }
            ]
        },
    )

    login: _text(255)
    full_name: _optional_text(255) = Field(default=None, alias="fullName")
    department: _optional_text(255) = Field(default=None, alias="department")
    # AD lavozim (job title), masalan "Bosh mutaxassis".
    position: _optional_text(255) = Field(default=None, alias="position")
    is_active: bool = Field(default=True, alias="active")


class EmployeeSyncBatch(BaseModel):
    """POST /api/ad-sync tanasi."""

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "examples": [
                {
                    "mode": "delta",
                    "employees": [
                        {
                            "login": "jsmith",
                            "fullName": "John Smith",
                            "department": "Buxgalteriya",
                            "active": True,
                        }
                    ],
                }
            ]
        },
    )

    mode: Literal["full", "delta"] = Field(
        default="delta",
        description=(
            "'full' — AD'dagi to'liq joriy holat (ro'yxatda yo'q xodimlar ishdan bo'shagan "
            "deb belgilanadi); 'delta' — faqat o'zgargan xodimlarni yangilaydi."
        ),
    )
    employees: list[EmployeeIn] = Field(
        default_factory=list,
        max_length=20000,
        description="Xodimlar ro'yxati",
    )


class EmployeeSyncResult(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"mode": "full", "received": 42, "upserted": 42, "deactivated": 1}]
        }
    )

    mode: str
    received: int = Field(description="Paketda kelgan xodimlar soni")
    upserted: int = Field(description="Bazaga qo'shilgan/yangilangan qatorlar soni")
    deactivated: int = Field(
        description="'full' rejimida ro'yxatda yo'qligi uchun nofaol qilinganlar soni"
    )


# ---------------------------------------------------------------------------
# Kvotalar (har xodim uchun oylik/choraklik qog'oz limiti)
# ---------------------------------------------------------------------------


class EmployeeQuotaIn(BaseModel):
    """PUT /api/quotas uchun bitta kvota yozuvi."""

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "examples": [
                {
                    "login": "jsmith",
                    "periodType": "quarter",
                    "year": 2026,
                    "periodNo": 3,
                    "allocatedPages": 1500,
                }
            ]
        },
    )

    login: _text(255)
    period_type: PeriodType = Field(
        alias="periodType", description="'month' yoki 'quarter'"
    )
    year: int = Field(ge=2000, le=2100)
    period_no: int = Field(
        alias="periodNo", description="Oy uchun 1..12, chorak uchun 1..4"
    )
    allocated_pages: int = Field(default=0, ge=0, alias="allocatedPages")

    @model_validator(mode="after")
    def _check_period_no(self) -> "EmployeeQuotaIn":
        try:
            validate_period_no(self.period_type, self.period_no)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        return self


class EmployeeQuotaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    login: str
    period_type: str = Field(serialization_alias="periodType")
    year: int
    period_no: int = Field(serialization_alias="periodNo")
    allocated_pages: int = Field(serialization_alias="allocatedPages")


# ---------------------------------------------------------------------------
# Statistika (chorak/oy bo'yicha agregatsiya)
# ---------------------------------------------------------------------------


class StatsSummaryOut(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "periodType": "quarter",
                    "year": 2026,
                    "periodNo": 3,
                    "totalPages": 12480,
                    "totalJobs": 934,
                    "successRate": 0.97,
                    "activePrinters": 6,
                    "defaultQuota": 300,
                }
            ]
        }
    )

    period_type: str = Field(serialization_alias="periodType")
    year: int
    period_no: int = Field(serialization_alias="periodNo")
    total_pages: int = Field(serialization_alias="totalPages")
    total_jobs: int = Field(serialization_alias="totalJobs")
    success_rate: float = Field(serialization_alias="successRate")
    active_printers: int = Field(serialization_alias="activePrinters")
    default_quota: int = Field(
        serialization_alias="defaultQuota",
        description=(
            "Ushbu davr turi (oy/chorak) uchun standart kvota — xodim uchun aniq "
            "kvota belgilanmagan bo'lsa shu qiymat 'allocated' sifatida ishlatiladi."
        ),
    )


class EmployeeStatOut(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "login": "jsmith",
                    "fullName": "John Smith",
                    "department": "Buxgalteriya",
                    "position": "Bosh mutaxassis",
                    "used": 1780,
                    "allocated": 1500,
                    "remaining": -280,
                    "overLimit": True,
                    "matchStatus": "active",
                }
            ]
        }
    )

    login: str
    full_name: str | None = Field(serialization_alias="fullName")
    department: str | None
    position: str | None = None
    used: int
    allocated: int
    remaining: int
    over_limit: bool = Field(serialization_alias="overLimit")
    match_status: Literal["active", "inactive", "unmatched"] = Field(
        serialization_alias="matchStatus"
    )


class TimeseriesPointOut(BaseModel):
    date: str = Field(description="Kun (YYYY-MM-DD)")
    pages: int
    jobs: int


class TopItemOut(BaseModel):
    name: str
    pages: int
    jobs: int


class TopStatsOut(BaseModel):
    printers: list[TopItemOut]
    computers: list[TopItemOut]
    departments: list[TopItemOut]


class FailureReasonOut(BaseModel):
    reason: str = Field(description="Xato sababi (bo'sh bo'lsa 'Sabab ko'rsatilmagan')")
    count: int


class PrinterStatOut(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "HP LaserJet M404",
                    "pages": 4210,
                    "jobs": 318,
                    "successRate": 0.98,
                    "failedJobs": 6,
                }
            ]
        }
    )

    name: str
    pages: int
    jobs: int
    success_rate: float = Field(serialization_alias="successRate")
    failed_jobs: int = Field(serialization_alias="failedJobs")


class DepartmentRollupOut(BaseModel):
    """Bo'lim bo'yicha davr uchun yig'indi (chop etganlar bilan cheklanmagan)."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "Buxgalteriya",
                    "pages": 3400,
                    "jobs": 210,
                    "employeeCount": 12,
                    "totalAllocated": 3000,
                    "remaining": -400,
                    "overLimit": True,
                }
            ]
        }
    )

    name: str
    pages: int = Field(description="Davrda sarflangan (chop etilgan) sahifalar")
    jobs: int
    employee_count: int = Field(serialization_alias="employeeCount", description="Faol xodimlar soni")
    total_allocated: int = Field(
        serialization_alias="totalAllocated", description="Xodimlar kvotalari yig'indisi"
    )
    remaining: int = Field(description="totalAllocated - pages")
    over_limit: bool = Field(serialization_alias="overLimit")


# ---------------------------------------------------------------------------
# Xodimlar ro'yxati (dashboard "Xodimlar" bo'limi uchun — faqat chop etganlar emas)
# ---------------------------------------------------------------------------


class EmployeeOut(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "login": "jsmith",
                    "fullName": "John Smith",
                    "department": "Buxgalteriya",
                    "position": "Bosh mutaxassis",
                    "isActive": True,
                    "syncedAt": "2026-07-11T09:00:00+00:00",
                }
            ]
        },
    )

    login: str
    full_name: str | None = Field(serialization_alias="fullName")
    department: str | None
    position: str | None = None
    is_active: bool = Field(serialization_alias="isActive")
    synced_at: datetime = Field(serialization_alias="syncedAt")


class AdSyncStatusOut(BaseModel):
    """`GET /api/ad-sync/status` — dashboard uchun AD sinxronizatsiyasining
    so'nggi holati (soatlik skript hali ishlab turibdimi)."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "lastSyncedAt": "2026-07-13T05:52:35Z",
                    "employeeCount": 157,
                    "activeCount": 157,
                    "minutesSinceSync": 14512,
                    "isStale": True,
                }
            ]
        }
    )

    last_synced_at: datetime | None = Field(
        serialization_alias="lastSyncedAt",
        description="`MAX(employees.synced_at)` — AD'dan oxirgi marta ma'lumot kelgan vaqt. Hali xodim yo'q bo'lsa `null`.",
    )
    employee_count: int = Field(serialization_alias="employeeCount", description="Jami xodimlar soni")
    active_count: int = Field(
        serialization_alias="activeCount", description="Faol (`is_active=true`) xodimlar soni"
    )
    minutes_since_sync: int | None = Field(
        serialization_alias="minutesSinceSync",
        description="So'nggi sinxronizatsiyadan beri o'tgan to'liq daqiqalar. Hech qachon sinxronlanmagan bo'lsa `null`.",
    )
    is_stale: bool = Field(
        serialization_alias="isStale",
        description="So'nggi sinxronizatsiya `AD_SYNC_STALE_MINUTES`dan eski (yoki umuman xodim yo'q) bo'lsa `true`.",
    )


# ---------------------------------------------------------------------------
# Agent (.exe) sog'lik signali (heartbeat)
# ---------------------------------------------------------------------------


class AgentStatusIn(BaseModel):
    """`POST /api/agent-status` tanasi — agent davriy yuboradigan sog'lik signali.

    Bitta kompyuter uchun bitta hisobot; bazada shu kompyuter bo'yicha eng
    so'nggi qiymatlar bilan ustiga yoziladi (tarix saqlanmaydi).
    """

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "examples": [
                {
                    "computer": "DESKTOP-20DJFSC",
                    "username": "jdoe",
                    "version": "1.4.11",
                    "working": True,
                    "detail": "",
                    "bootTimeUtc": "2026-07-20T05:12:44+00:00",
                    "uptimeSeconds": 274320,
                    "agentUptimeSeconds": 63,
                    "timestamp": "2026-07-23T09:38:47+00:00",
                }
            ]
        },
    )

    computer: _text(255)
    # Windows displey nomi ("Sarvar Mamatqulov"), AD login emas — `Employee`ga
    # bog'lanmaydi, faqat ma'lumot sifatida saqlanadi.
    username: _optional_text(255) = None
    version: _optional_text(50) = None
    working: bool
    # Xato/holat matni. Bo'sh satr ("") NULL sifatida saqlanadi.
    detail: _optional_text(4096) = None
    # Ish stantsiyasi qachon yoqilgani. Eski agentlar yubormaydi -> None.
    boot_time_utc: datetime | None = Field(default=None, alias="bootTimeUtc")
    # Ish stantsiyasining ishlab turgan vaqti (soniyalarda). Eski agentlar
    # yubormaydi -> None.
    uptime_seconds: int | None = Field(default=None, ge=0, alias="uptimeSeconds")
    # Agent jarayonining ishlab turgan vaqti (soniyalarda) — kichik bo'lsa
    # yaqinda qayta ishga tushgan (ehtimol crash-loop) degani.
    agent_uptime_seconds: int | None = Field(default=None, ge=0, alias="agentUptimeSeconds")
    # .NET 7 xonali kasr soniya yoki oddiy "...Z" formatida qabul qilinadi.
    timestamp: datetime

    def normalized_timestamp(self) -> datetime:
        """Vaqt mintaqasi ko'rsatilmagan bo'lsa UTC deb hisoblaymiz."""
        if self.timestamp.tzinfo is None:
            return self.timestamp.replace(tzinfo=timezone.utc)
        return self.timestamp

    def normalized_boot_time(self) -> datetime | None:
        """`bootTimeUtc` uchun ham xuddi shu qoida — vaqt mintaqasiz bo'lsa UTC."""
        if self.boot_time_utc is None:
            return None
        if self.boot_time_utc.tzinfo is None:
            return self.boot_time_utc.replace(tzinfo=timezone.utc)
        return self.boot_time_utc


class AgentStatusResult(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"computer": "DESKTOP-20DJFSC", "status": "ok"}]}
    )

    computer: str
    status: str = "ok"


class AgentOut(BaseModel):
    """`GET /api/agents` javobidagi bitta qator."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "computer": "DESKTOP-20DJFSC",
                    "username": "jdoe",
                    "version": "1.4.11",
                    "working": True,
                    "detail": None,
                    "bootTimeUtc": "2026-07-20T05:12:44+00:00",
                    "uptimeSeconds": 274320,
                    "agentUptimeSeconds": 63,
                    "reportedAt": "2026-07-23T09:38:47+00:00",
                    "isStale": False,
                    "minutesSinceReport": 5,
                    "recentlyRestarted": True,
                }
            ]
        }
    )

    computer: str
    username: str | None
    version: str | None
    working: bool
    detail: str | None
    boot_time_utc: datetime | None = Field(serialization_alias="bootTimeUtc")
    uptime_seconds: int | None = Field(serialization_alias="uptimeSeconds")
    agent_uptime_seconds: int | None = Field(serialization_alias="agentUptimeSeconds")
    reported_at: datetime = Field(serialization_alias="reportedAt")
    is_stale: bool = Field(
        serialization_alias="isStale",
        description="`reported_at`dan beri `AGENT_STALE_MINUTES`dan ko'p vaqt o'tgan bo'lsa true",
    )
    minutes_since_report: int = Field(
        serialization_alias="minutesSinceReport", description="So'nggi hisobotdan beri o'tgan daqiqalar"
    )
    recently_restarted: bool = Field(
        serialization_alias="recentlyRestarted",
        description=(
            "Agent jarayoni `AGENT_RECENT_RESTART_SECONDS`dan kam vaqt oldin ishga "
            "tushgan bo'lsa true (yaqinda qayta ishga tushgan, ehtimol crash-loop)"
        ),
    )


class AgentsSummaryOut(BaseModel):
    """`GET /api/agents/summary` — dashboard KPI kartochkalari uchun."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"total": 42, "working": 38, "notWorking": 2, "stale": 4, "recentlyRestarted": 1}
            ]
        }
    )

    total: int
    working: int
    not_working: int = Field(serialization_alias="notWorking")
    stale: int = Field(description="`AGENT_STALE_MINUTES`dan ko'p vaqt signal bermagan agentlar soni")
    recently_restarted: int = Field(
        serialization_alias="recentlyRestarted",
        description="Agent jarayoni `AGENT_RECENT_RESTART_SECONDS`dan kam vaqt oldin ishga tushganlar soni",
    )


# ---------------------------------------------------------------------------
# Dashboard foydalanuvchisi autentifikatsiyasi (JWT)
# ---------------------------------------------------------------------------


class LoginIn(BaseModel):
    """`POST /api/auth/login` tanasi."""

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"username": "admin", "password": "maxfiy-parol"}]}
    )

    username: _text(255)
    password: _text(255)


class LoginOut(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "accessToken": "eyJhbGciOi...",
                    "tokenType": "bearer",
                    "expiresIn": 43200,
                }
            ]
        }
    )

    access_token: str = Field(serialization_alias="accessToken")
    token_type: str = Field(default="bearer", serialization_alias="tokenType")
    expires_in: int = Field(
        serialization_alias="expiresIn", description="Token amal qilish muddati (soniyalarda)"
    )
