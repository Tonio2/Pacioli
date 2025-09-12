from pydantic import BaseModel, model_validator
from typing import Optional, List, Literal
import datetime
from decimal import Decimal

class EntryOut(BaseModel):
    id: int
    date: datetime.date
    jnl: str
    piece_ref: str
    accnum: str
    lib: str
    debit: Decimal
    credit: Decimal

    class Config:
        from_attributes = True

class EntriesResponse(BaseModel):
    rows: List[EntryOut]
    total: int

class PieceChange(BaseModel):
    op: Literal["add", "modify", "delete"]
    entry_id: Optional[int] = None
    date: Optional[datetime.date] = None
    accnum: Optional[str] = None
    lib: Optional[str] = None
    debit: Optional[Decimal] = None
    credit: Optional[Decimal] = None

class PieceCommitRequest(BaseModel):
    client_id: int
    exercice_id: int
    journal: str
    piece_ref: str
    description: Optional[str] = None
    changes: List[PieceChange]

class BalanceRow(BaseModel):
    accnum: str
    acclib: str
    debit: Decimal
    credit: Decimal
    solde: Decimal
    count: int

class BalanceResponse(BaseModel):
    rows: List[BalanceRow]
    total_accounts: int


class ClientCreate(BaseModel):
    name: str

class ClientOut(BaseModel):
    id: int
    name: str
    class Config:
        from_attributes = True

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
