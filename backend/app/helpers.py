from decimal import Decimal
from typing import Optional


NBSP = "\u00A0"  # espace insécable

def fmt_cents_fec(cents: Optional[int]) -> str:
    """
    Format FEC: pas de séparateur de milliers, virgule décimale, pas de symbole.
    Ex: 123456 -> '1234,56'
    """
    euros = (Decimal(cents or 0) / Decimal(100)).quantize(Decimal("0.01"))
    # f"{euros:.2f}" donne '1234.56' -> remplace le point par virgule
    return f"{euros:.2f}".replace(".", ",")

def fmt_cents_fr(cents: Optional[int], with_symbol: bool = True) -> str:
    """
    Format FR lisible: séparateur milliers = NBSP, virgule décimale, option symbole €.
    Ex: 123456 -> '1 234,56 €'
    Ex: -123456 -> '-1 234,56 €'
    """
    euros = (Decimal(cents or 0) / Decimal(100)).quantize(Decimal("0.01"))
    # D'abord un format US '1,234.56', puis on permute séparateurs et insère NBSP
    s = f"{euros:,.2f}"              # '1,234.56' ou '-1,234.56'
    s = s.replace(",", "§")          # gardien provisoire
    s = s.replace(".", ",")          # décimale FR
    s = s.replace("§", NBSP)         # milliers = NBSP
    if with_symbol:
        # espace insécable avant le symbole (typo FR)
        s = f"{s}{NBSP}€"
    return s
