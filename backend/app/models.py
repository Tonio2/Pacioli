import datetime
from sqlalchemy import Integer, String, Date, ForeignKey, UniqueConstraint, DateTime, func
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
    entries: Mapped[list["Entry"]] = relationship(back_populates="account")

class Journal(Base):
    __tablename__ = "journals"
    __table_args__ = (UniqueConstraint("client_id", "jnl", name="uix_client_jnl"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    jnl: Mapped[str] = mapped_column(String(32), nullable=False)
    jnl_lib: Mapped[str] = mapped_column(String(255), nullable=False)

    client: Mapped["Client"] = relationship(back_populates="journals")

class JournalSequence(Base):
    __tablename__ = "journal_sequences"
    __table_args__ = (UniqueConstraint("exercice_id", "jnl", name="uix_seq_ex_jnl"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    exercice_id: Mapped[int] = mapped_column(ForeignKey("exercices.id", ondelete="CASCADE"), nullable=False, index=True)
    jnl: Mapped[str] = mapped_column(String(32), nullable=False)
    last_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Entry(Base):
    __tablename__ = "entries"
    id: Mapped[int] = mapped_column(primary_key=True)
    exercice_id: Mapped[int] = mapped_column(ForeignKey("exercices.id", ondelete="CASCADE"), nullable=False, index=True)
    date: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)
    jnl: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    piece_ref: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False, index=True)
    lib: Mapped[str] = mapped_column(String(255), nullable=False)
    debit_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    credit_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    piece_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    valid_date: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)
    montant_minor: Mapped[int] = mapped_column(Integer, nullable=True)
    i_devise: Mapped[str] = mapped_column(String(32), nullable=True)

    exercice: Mapped["Exercice"] = relationship(back_populates="entries")
    account: Mapped["Account"] = relationship(back_populates="entries")

class HistoryEvent(Base):
    __tablename__ = "history_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    exercice_id: Mapped[int] = mapped_column(ForeignKey("exercices.id", ondelete="CASCADE"), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    counts_json: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    exercice: Mapped["Exercice"] = relationship(back_populates="history_events")
