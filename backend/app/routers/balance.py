from decimal import Decimal
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from ..helpers import fmt_cents_fr
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
            func.sum(Entry.debit_minor).label("debit_minor"),
            func.sum(Entry.credit_minor).label("credit_minor"),
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
            sub.c.debit_minor,
            sub.c.credit_minor,
            (sub.c.debit_minor - sub.c.credit_minor).label("solde_minor"),
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
            "debit_minor": r.debit_minor or 0,
            "credit_minor": r.credit_minor or 0,
            "solde_minor": r.solde_minor or 0,
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
            func.sum(Entry.debit_minor).label("debit_minor"),
            func.sum(Entry.credit_minor).label("credit_minor"),
        )
        .where(Entry.exercice_id == exercice_id)
        .group_by(Entry.account_id)
        .subquery()
    )

    q = (
        select(
            Account.accnum.label("accnum"),
            func.coalesce(Account.acclib, Account.accnum).label("acclib"),
            sub.c.debit_minor,
            sub.c.credit_minor,
        )
        .join(Account, Account.id == sub.c.account_id)
        .order_by(Account.accnum)
    )

    rows = db.execute(q).all()


    lines: list[str] = [
        "N° de compte\tIntitulé du compte\tCumul débit\tCumul crédit\tSolde débit\tSolde crédit"
    ]

    for r in rows:
        debit_minor = r.debit_minor
        credit_minor = r.credit_minor
        solde = debit_minor - credit_minor
        solde_debit_minor = solde if solde > 0 else 0
        solde_credit_minor = -solde if solde < 0 else 0

        accnum = r.accnum or ""
        acclib = (r.acclib or "").replace("\t", " ").replace("\n", " ")

        lines.append(
            f"{accnum}\t{acclib}\t{fmt_cents_fr(debit_minor)}\t{fmt_cents_fr(credit_minor)}\t{fmt_cents_fr(solde_debit_minor)}\t{fmt_cents_fr(solde_credit_minor)}"
        )

    content = "\n".join(lines) + ("\n" if lines else "")
    headers = {
        "Content-Type": "text/plain; charset=utf-8",
        "Content-Disposition": f'attachment; filename="balance.csv"',
    }
    return Response(content=content, media_type="text/plain", headers=headers)
