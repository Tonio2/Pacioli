from decimal import Decimal
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from ..database import get_db
from ..models import Entry, Account

router = APIRouter(prefix="/api/balance", tags=["balance"])

@router.get("")
def balance(client_id: int = Query(...), exercice_id: int = Query(...), db: Session = Depends(get_db)):
    sub = (
        select(Entry.accnum,
               func.sum(Entry.debit).label("debit"),
               func.sum(Entry.credit).label("credit"),
               func.count().label("count"))
        .where(Entry.client_id==client_id, Entry.exercice_id==exercice_id)
        .group_by(Entry.accnum)
        .subquery()
    )
    q = (
        select(sub.c.accnum,
               func.coalesce(Account.acclib, sub.c.accnum).label("acclib"),
               sub.c.debit, sub.c.credit, (sub.c.debit - sub.c.credit).label("solde"), sub.c.count)
        .join(Account, (Account.client_id==client_id) & (Account.accnum==sub.c.accnum), isouter=True)
        .order_by(sub.c.accnum)
    )
    rows = db.execute(q).all()
    out = [
        {
            "accnum": r.accnum,
            "acclib": r.acclib,
            "debit": float(r.debit or 0),
            "credit": float(r.credit or 0),
            "solde": float((r.debit or 0) - (r.credit or 0)),
            "count": r.count,
        }
        for r in rows
    ]
    return {"rows": out, "total_accounts": len(out)}

@router.get("/export")
def export_balance_txt(
    client_id: int = Query(...),
    exercice_id: int = Query(...),
    db: Session = Depends(get_db),
):
    # Reprend exactement la même logique que la route JSON
    sub = (
        select(
            Entry.accnum,
            func.sum(Entry.debit).label("debit"),
            func.sum(Entry.credit).label("credit"),
            func.count().label("count"),
        )
        .where(Entry.client_id == client_id, Entry.exercice_id == exercice_id)
        .group_by(Entry.accnum)
        .subquery()
    )
    q = (
        select(
            sub.c.accnum,
            func.coalesce(Account.acclib, sub.c.accnum).label("acclib"),
            sub.c.debit,
            sub.c.credit,
        )
        .join(
            Account,
            (Account.client_id == client_id) & (Account.accnum == sub.c.accnum),
            isouter=True,
        )
        .order_by(sub.c.accnum)
    )
    rows = db.execute(q).all()

    def _d(x) -> Decimal:
        return Decimal(x or 0)

    # Option : format FR (virgule décimale) ; Excel FR gère très bien le TSV avec virgules
    def fmt(n: Decimal) -> str:
        return f"{n:.2f}".replace(".", ",")

    # En-tête
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
        "Content-Disposition": f'attachment; filename="balance_{client_id}_{exercice_id}.txt"',
    }
    return Response(content=content, media_type="text/plain", headers=headers)
