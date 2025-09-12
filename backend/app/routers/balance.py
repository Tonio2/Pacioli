from decimal import Decimal
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from ..schemas import BalanceResponse
from ..database import get_db
from ..models import Entry, Account

router = APIRouter(prefix="/api/balance", tags=["balance"])

@router.get("", response_model=BalanceResponse)
def balance(exercice_id: int = Query(...), db: Session = Depends(get_db)):
    # Agrégats par account_id
    sub = (
        select(
            Entry.account_id.label("account_id"),
            func.sum(Entry.debit).label("debit"),
            func.sum(Entry.credit).label("credit"),
            func.count().label("count"),
        )
        .where(Entry.exercice_id == exercice_id)
        .group_by(Entry.account_id)
        .subquery()
    )

    q = (
        select(
            Account.accnum.label("accnum"),
            func.coalesce(Account.acclib, Account.accnum).label("acclib"),
            sub.c.debit,
            sub.c.credit,
            (sub.c.debit - sub.c.credit).label("solde"),
            sub.c.count,
        )
        .join(Account, Account.id == sub.c.account_id)
        .order_by(Account.accnum)
    )

    rows = db.execute(q).all()
    out = [
        {
            "accnum": r.accnum,
            "acclib": r.acclib,
            "debit": r.debit or Decimal(0),
            "credit": r.credit or Decimal(0),
            "solde": r.solde or Decimal(0),
            "count": r.count,
        }
        for r in rows
    ]
    return {"rows": out, "total_accounts": len(out)}

@router.get("/export")
def export_balance_txt(
    exercice_id: int = Query(...),
    db: Session = Depends(get_db),
):
    sub = (
        select(
            Entry.account_id.label("account_id"),
            func.sum(Entry.debit).label("debit"),
            func.sum(Entry.credit).label("credit"),
        )
        .where(Entry.exercice_id == exercice_id)
        .group_by(Entry.account_id)
        .subquery()
    )

    q = (
        select(
            Account.accnum.label("accnum"),
            func.coalesce(Account.acclib, Account.accnum).label("acclib"),
            sub.c.debit,
            sub.c.credit,
        )
        .join(Account, Account.id == sub.c.account_id)
        .order_by(Account.accnum)
    )

    rows = db.execute(q).all()

    def _d(x) -> Decimal:
        return Decimal(x or 0)

    def fmt(n: Decimal) -> str:
        return f"{n:.2f}".replace(".", ",")

    lines: list[str] = [
        "N° de compte\tIntitulé du compte\tCumul débit\tCumul crédit\tSolde débit\tSolde crédit"
    ]

    for r in rows:
        debit = _d(r.debit)
        credit = _d(r.credit)
        solde = debit - credit
        solde_debit = solde if solde > 0 else Decimal(0)
        solde_credit = -solde if solde < 0 else Decimal(0)

        accnum = r.accnum or ""
        acclib = (r.acclib or "").replace("\t", " ").replace("\n", " ")

        lines.append(
            f"{accnum}\t{acclib}\t{fmt(debit)}\t{fmt(credit)}\t{fmt(solde_debit)}\t{fmt(solde_credit)}"
        )

    content = "\n".join(lines) + ("\n" if lines else "")
    headers = {
        "Content-Type": "text/plain; charset=utf-8",
        "Content-Disposition": f'attachment; filename="balance.csv"',
    }
    return Response(content=content, media_type="text/plain", headers=headers)
