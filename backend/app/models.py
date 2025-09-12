import datetime
from decimal import Decimal
from sqlalchemy import String, Date, Numeric, ForeignKey, UniqueConstraint, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

class Client(Base):
    __tablename__ = "clients"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)

    exercices: Mapped[list["Exercice"]] = relationship(
        back_populates="client",
        passive_deletes=True,
    )
    accounts: Mapped[list["Account"]] = relationship(
        back_populates="client",
        passive_deletes=True,
    )
    journals: Mapped[list["Journal"]] = relationship(
        back_populates="client",
        passive_deletes=True,
    )


class Exercice(Base):
    __tablename__ = "exercices"
    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(32), nullable=False)
    date_start: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    date_end: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="OPEN")

    client: Mapped["Client"] = relationship(back_populates="exercices")

    entries: Mapped[list["Entry"]] = relationship(
        back_populates="exercice",
        passive_deletes=True,
    )
    history_events: Mapped[list["HistoryEvent"]] = relationship(
        back_populates="exercice",
        passive_deletes=True,
    )

class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (UniqueConstraint("client_id", "accnum", name="uix_client_accnum"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    accnum: Mapped[str] = mapped_column(String(64), nullable=False)
    acclib: Mapped[str] = mapped_column(String(255), nullable=False)

    client: Mapped["Client"] = relationship(back_populates="accounts")

class Journal(Base):
    __tablename__ = "journals"
    __table_args__ = (UniqueConstraint("client_id", "jnl", name="uix_client_jnl"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    jnl: Mapped[str] = mapped_column(String(32), nullable=False)
    jnl_lib: Mapped[str] = mapped_column(String(255), nullable=False)

    client: Mapped["Client"] = relationship(back_populates="journals")

class Entry(Base):
    __tablename__ = "entries"
    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    exercice_id: Mapped[int] = mapped_column(ForeignKey("exercices.id", ondelete="CASCADE"), nullable=False, index=True)
    date: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)
    jnl: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    piece_ref: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    accnum: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    lib: Mapped[str] = mapped_column(String(255), nullable=False)
    debit: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    credit: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)

    exercice: Mapped["Exercice"] = relationship(back_populates="entries")

class HistoryEvent(Base):
    __tablename__ = "history_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    exercice_id: Mapped[int] = mapped_column(ForeignKey("exercices.id", ondelete="CASCADE"), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    counts_json: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    exercice: Mapped["Exercice"] = relationship(back_populates="history_events")
