from pydantic import BaseModel, model_validator, field_serializer
from typing import Optional, List, Literal
import datetime

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
    debit_minor: int
    credit_minor: int

    class Config:
        from_attributes = True


class EntriesResponse(BaseModel):
    rows: List[EntryOut]
    total: int


# ----------- Balance -----------
class BalanceRow(BaseModel):
    accnum: str
    acclib: str
    debit_minor: int
    credit_minor: int
    solde_minor: int
    count: int



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
    debit_minor: int
    credit_minor: int



class PieceGetResponse(BaseModel):
    rows: List[PieceEntryOut]


class PieceChange(BaseModel):
    op: Literal["add", "modify", "delete"]
    entry_id: Optional[int] = None
    date: Optional[datetime.date] = None
    accnum: Optional[str] = None
    acclib: Optional[str] = None
    lib: Optional[str] = None
    debit_minor: Optional[int] = None
    credit_minor: Optional[int] = None


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
    debit_minor: int
    credit_minor: int
    diff_minor: int



class UnbalancedPieceListResponse(BaseModel):
    items: List[UnbalancedPieceItem]
    total: int


class UnbalancedJournalItem(BaseModel):
    jnl: str
    count: int
    debit_minor: int
    credit_minor: int
    diff_minor: int



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
