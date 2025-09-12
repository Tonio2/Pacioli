from datetime import date
from decimal import Decimal
from typing import Iterable

class ValidationError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


def ensure_dates_in_exercice(rows: Iterable[dict], start: date, end: date):
    for r in rows:
        d: date = r["date"]
        if not (start <= d <= end):
            raise ValidationError(f"Date hors exercice: {d} (attendu {start}..{end})")


def ensure_batch_balanced(rows: Iterable[dict]):
    total = Decimal("0")
    for r in rows:
        total += (r.get("debit", Decimal("0")) - r.get("credit", Decimal("0")))
    if total.copy_abs() > Decimal("0.005"):
        raise ValidationError(f"Lot non équilibré (Δ={total}) : Σ(debit)-Σ(credit) doit être 0")
