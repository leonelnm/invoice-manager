from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(150))
    is_active: Mapped[bool] = mapped_column(default=True)
    is_admin: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class SourceSystem(Base):
    __tablename__ = "source_systems"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(default=True)


class InvoiceSequence(Base):
    __tablename__ = "invoice_sequences"
    id: Mapped[int] = mapped_column(primary_key=True)
    series: Mapped[str] = mapped_column(String(30), default="FAC")
    fiscal_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_number: Mapped[int] = mapped_column(Integer, default=0)
    __table_args__ = (UniqueConstraint("series", "fiscal_year", name="uq_sequence"),)


class Invoice(Base):
    __tablename__ = "invoices"
    id: Mapped[int] = mapped_column(primary_key=True)
    sequence_id: Mapped[int] = mapped_column(ForeignKey("invoice_sequences.id"))
    sequence_number: Mapped[int] = mapped_column(Integer)
    invoice_number: Mapped[str] = mapped_column(String(80), unique=True)
    source_system_id: Mapped[int] = mapped_column(ForeignKey("source_systems.id"))
    report_id: Mapped[str] = mapped_column(String(150))
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    source_system: Mapped[SourceSystem] = relationship()
    user: Mapped[User] = relationship()
    __table_args__ = (
        UniqueConstraint("sequence_id", "sequence_number", name="uq_sequence_number"),
        UniqueConstraint("source_system_id", "report_id", name="uq_source_report"),
        Index("ix_invoice_report", "report_id"),
        Index("ix_invoice_source_date", "source_system_id", "created_at"),
    )


class IdempotencyRequest(Base):
    __tablename__ = "idempotency_requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(100), unique=True)
    request_fingerprint: Mapped[str] = mapped_column(String(64))
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"))
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    invoice: Mapped[Invoice] = relationship()
