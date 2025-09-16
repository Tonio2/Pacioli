from datetime import date
from decimal import Decimal
from typing import Iterable

from fastapi import HTTPException

class ValidationError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


def ensure_dates_in_exercice(rows: Iterable[dict], start: date, end: date):
    for r in rows:
        d: date = r["date"]
        if not (start <= d <= end):
            raise ValidationError(f"Date hors exercice: {d} (attendu {start}..{end})")


def ensure_batch_balanced(rows: Iterable[dict]):
    total = Decimal(0)
    for r in rows:
        total += (r.get("debit", Decimal(0)) - r.get("credit", Decimal(0)))
    if total.copy_abs() != Decimal(0):
        raise ValidationError(f"Lot non équilibré (Δ={total}) : Σ(debit)-Σ(credit) doit être 0")

def ensure_batch_balanced_minor(rows: Iterable[dict]):
    total = 0
    for r in rows:
        total += (r.get("debit_minor", 0) - r.get("credit_minor", 0))
    if total != 0:
        raise ValidationError(f"Lot non équilibré (Δ={total} cents)")

def check_one_side(debit_m: int | None, credit_m: int | None):
    d = debit_m or 0
    c = credit_m or 0
    if d < 0 or c < 0:
        raise HTTPException(400, "Montants négatifs interdits")
    if (d > 0 and c > 0) or (d == 0 and c == 0):
        raise HTTPException(400, "Chaque ligne doit avoir soit un débit soit un crédit (exclusif)")
