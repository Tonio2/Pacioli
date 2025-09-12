from pydantic import BaseModel, model_validator, field_serializer
from typing import Optional, List, Literal
import datetime
from decimal import Decimal

# ----------- Entrées -----------
class EntryOut(BaseModel):
    id: int
    date: datetime.date
    jnl: str
    piece_ref: str
    account_id: int
    accnum: str
    acclib: str
    lib: str
    debit: Decimal
    credit: Decimal

    @field_serializer("debit", "credit", mode="plain")
    def _dec_as_float(self, v: Decimal) -> float:
        return float(v or 0)

    class Config:
        from_attributes = True


class EntriesResponse(BaseModel):
    rows: List[EntryOut]
    total: int


# ----------- Balance -----------
class BalanceRow(BaseModel):
    accnum: str
    acclib: str
    debit: Decimal
    credit: Decimal
    solde: Decimal
    count: int

    @field_serializer("debit", "credit", "solde", mode="plain")
    def _dec_as_float(self, v: Decimal) -> float:
        return float(v or 0)


class BalanceResponse(BaseModel):
    rows: List[BalanceRow]
    total_accounts: int


# ----------- Pièce -----------
class PieceEntryOut(BaseModel):
    id: int
    date: datetime.date
    jnl: str
    piece_ref: str
    account_id: int
    accnum: str
    acclib: str
    lib: str
    debit: Decimal
    credit: Decimal

    @field_serializer("debit", "credit", mode="plain")
    def _dec_as_float(self, v: Decimal) -> float:
        return float(v or 0)


class PieceGetResponse(BaseModel):
    rows: List[PieceEntryOut]


class PieceChange(BaseModel):
    op: Literal["add", "modify", "delete"]
    entry_id: Optional[int] = None
    date: Optional[datetime.date] = None
    accnum: Optional[str] = None
    acclib: Optional[str] = None
    lib: Optional[str] = None
    debit: Optional[Decimal] = None
    credit: Optional[Decimal] = None


class PieceCommitRequest(BaseModel):
    exercice_id: int
    journal: str
    piece_ref: str
    description: Optional[str] = None
    changes: List[PieceChange]


class PieceCommitResponse(BaseModel):
    added: int
    modified: int
    deleted: int
    warnings: dict


# ----------- Contrôles (déséquilibres) -----------
class UnbalancedPieceItem(BaseModel):
    jnl: str
    piece_ref: str
    count: int
    debit: Decimal
    credit: Decimal
    diff: Decimal

    @field_serializer("debit", "credit", "diff", mode="plain")
    def _dec_as_float(self, v: Decimal) -> float:
        return float(v or 0)


class UnbalancedPieceListResponse(BaseModel):
    items: List[UnbalancedPieceItem]
    total: int


class UnbalancedJournalItem(BaseModel):
    jnl: str
    count: int
    debit: Decimal
    credit: Decimal
    diff: Decimal

    @field_serializer("debit", "credit", "diff", mode="plain")
    def _dec_as_float(self, v: Decimal) -> float:
        return float(v or 0)


class UnbalancedJournalListResponse(BaseModel):
    items: List[UnbalancedJournalItem]
    total: int


# ----------- Accounts / Journals / Clients -----------
class AccountOut(BaseModel):
    id: int
    accnum: str
    acclib: str

class AccountCreate(BaseModel):
    client_id: int
    accnum: str
    acclib: str

class JournalOut(BaseModel):
    id: int
    jnl: str
    jnl_lib: str

class JournalCreate(BaseModel):
    client_id: int
    jnl: str
    jnl_lib: str

class ClientCreate(BaseModel):
    name: str

class ClientOut(BaseModel):
    id: int
    name: str
    class Config:
        from_attributes = True


# ----------- Exercice -----------
class ExerciceCreate(BaseModel):
    client_id: int
    label: str
    date_start: datetime.date
    date_end: datetime.date
    status: str = "OPEN"

    @model_validator(mode="after")
    def _check_dates(self) -> "ExerciceCreate":
        if self.date_end < self.date_start:
            raise ValueError("date_end < date_start")
        return self

class ExerciceOut(BaseModel):
    id: int
    client_id: int
    label: str
    date_start: datetime.date
    date_end: datetime.date
    status: str
    class Config:
        from_attributes = True

# --- Pages ---

class PageInfo(BaseModel):
    next: str | None
    prev: str | None
    has_next: bool
    has_prev: bool

class EntriesPage(BaseModel):
    rows: List[EntryOut]
    page_info: PageInfo
