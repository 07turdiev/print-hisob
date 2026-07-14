from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class PrintJob(Base):
    __tablename__ = "print_jobs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    computer: Mapped[str] = mapped_column(String(255))
    user_name: Mapped[str] = mapped_column("user_name", String(255))
    document: Mapped[str] = mapped_column(Text)
    printer: Mapped[str] = mapped_column(String(255))
    # IP bo'lmagan port nomlari ham keladi (WSD-..., USB001), shuning uchun matn.
    printer_ip: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Jismoniy varaq (qog'oz) soni — agent duplex hisobini o'zi qilib, tayyor
    # holda yuboradi (masalan 3 sahifali duplex hujjat -> pages=2).
    pages: Mapped[int] = mapped_column(Integer, default=0)
    # Hujjatdagi sahifalar soni (fayl ichidagi sahifa soni, varaq emas) — faqat
    # ma'lumot uchun, sarf hisobida ishlatilmaydi. Eski agentlar yubormasa 0.
    document_pages: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    # Ikki tomonlama (duplex) chop etilganmi — ma'lumot uchun, `pages`da hisobga
    # olingan bo'ladi (agent tomonidan). Eski agentlar bu maydonni yubormaydi ->
    # server tomonda False deb olinadi.
    duplex: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    printed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    success: Mapped[bool] = mapped_column(Boolean)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Bir xil chop etish hodisasi qayta yuborilganda dublikat yozilmasligi uchun.
    dedup_key: Mapped[str] = mapped_column(String(64), unique=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("ix_print_jobs_printed_at", "printed_at"),
        Index("ix_print_jobs_computer_printed_at", "computer", "printed_at"),
        Index("ix_print_jobs_user_name", "user_name"),
        Index("ix_print_jobs_printer", "printer"),
    )


class Employee(Base):
    """AD (Active Directory)'dan soatlik sinxronlanadigan xodimlar ro'yxati."""

    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    # `print_jobs.user_name` bilan mos keladigan login (masalan, domen login'i).
    login: Mapped[str] = mapped_column(String(255), unique=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)  # bo'lim
    # AD lavozim (job title) maydoni, masalan "Bosh mutaxassis".
    position: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Ishdan bo'shagan xodimlar "full" sinxronizatsiyada shu bayroq bilan o'chiriladi.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("ix_employees_department", "department"),
        Index("ix_employees_is_active", "is_active"),
    )


class EmployeeQuota(Base):
    """Har bir xodim uchun oylik yoki choraklik qog'oz kvotasi (limiti)."""

    __tablename__ = "employee_quotas"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    login: Mapped[str] = mapped_column(String(255))
    # "month" yoki "quarter".
    period_type: Mapped[str] = mapped_column(String(10))
    year: Mapped[int] = mapped_column(Integer)
    # Oy uchun 1..12, chorak uchun 1..4.
    period_no: Mapped[int] = mapped_column(Integer)
    allocated_pages: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "login", "period_type", "year", "period_no", name="uq_employee_quotas_period"
        ),
        Index("ix_employee_quotas_login", "login"),
        Index("ix_employee_quotas_period", "period_type", "year", "period_no"),
    )


class AgentStatus(Base):
    """Agent (.exe)dan davriy sog'lik signali (heartbeat).

    Har bir kompyuter uchun bitta qator — har safar eng so'nggi hisobot bilan
    ustiga yoziladi (`computer` bo'yicha upsert), tarix saqlanmaydi.
    """

    __tablename__ = "agent_status"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    computer: Mapped[str] = mapped_column(String(255), unique=True)
    # Windows displey nomi (masalan "Sarvar Mamatqulov") — AD login emas,
    # shuning uchun `Employee.login` bilan bog'lanmaydi.
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    working: Mapped[bool] = mapped_column(Boolean)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_agent_status_reported_at", "reported_at"),
        Index("ix_agent_status_working", "working"),
    )
