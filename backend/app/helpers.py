from decimal import Decimal
from typing import Optional


def fmt_cents(cents: Optional[int]) -> str:
    euros = (Decimal(cents or 0) / Decimal(100)).quantize(Decimal("0.01"))
    return f"{euros:.2f}".replace('.', ',')
