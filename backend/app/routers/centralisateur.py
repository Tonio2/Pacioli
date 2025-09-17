from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func, delete
import datetime as dt

from ..database import get_db
from ..models import Entry, Journal
from ..crud import get_exercice

router = APIRouter(prefix="/api/centralisateur", tags=["centralisateur"])

# --- Utils ---

def iter_months_in_range(start: dt.date, end: dt.date):
    """Yield (label "YYYY-MM", first_day, last_day) for each month intersecting [start, end]."""
    if end < start:
        return
    year = start.year
    month = start.month
    while True:
        first_day = dt.date(year, month, 1)
        # last day of this month
        if month == 12:
            last_day = dt.date(year, 12, 31)
        else:
            last_day = dt.date(year, month + 1, 1) - dt.timedelta(days=1)
        # clamp to exercice range
        d1 = max(first_day, start)
        d2 = min(last_day, end)
        label = f"{year:04d}-{month:02d}"
        yield label, d1, d2
        # stop condition
        if year == end.year and month == end.month:
            break
        # increment month
        month += 1
        if month > 12:
            month = 1
            year += 1


@router.get("")
def get_centralisateur(client_id: int = Query(...), exercice_id: int = Query(...), db: Session = Depends(get_db)):
    ex = get_exercice(db, exercice_id)
    if ex.client_id != client_id:
        # sécurité simple: l'exercice doit appartenir au client passé
        raise HTTPException(status_code=400, detail="exercice/client mismatch")

    # Liste de référence des journaux du client
    jrows = db.execute(select(Journal).where(Journal.client_id == client_id).order_by(Journal.jnl)).scalars().all()
    journals = [{"jnl": j.jnl, "jnl_lib": j.jnl_lib} for j in jrows]

    months = []
    # Pour chaque mois, agréger entries et compléter avec tous les journaux
    for label, d1, d2 in iter_months_in_range(ex.date_start, ex.date_end):
        q = (
            select(
                Entry.jnl.label("jnl"),
                func.count().label("count"),
                func.coalesce(func.sum(Entry.debit_minor), 0).label("debit_minor"),
                func.coalesce(func.sum(Entry.credit_minor), 0).label("credit_minor"),
            )
            .where(
                Entry.exercice_id == exercice_id,
                Entry.date >= d1,
                Entry.date <= d2,
            )
            .group_by(Entry.jnl)
        )
        by_jnl = {r.jnl: {"count": r.count or 0, "debit_minor": int(r.debit_minor or 0), "credit_minor": int(r.credit_minor or 0)} for r in db.execute(q)}

        rows = []
        for j in journals:
            cur = by_jnl.get(j["jnl"], {"count": 0, "debit_minor": 0, "credit_minor": 0})
            diff = cur["debit_minor"] - cur["credit_minor"]
            rows.append({
                "jnl": j["jnl"],
                "jnl_lib": j["jnl_lib"],
                "count": cur["count"],
                "debit_minor": cur["debit_minor"],
                "credit_minor": cur["credit_minor"],
                "diff_minor": diff,
            })
        months.append({"month": label, "rows": rows})

    return {
        "exercice": {
            "date_start": ex.date_start.isoformat(),
            "date_end": ex.date_end.isoformat(),
        },
        "journals": journals,
        "months": months,
    }


@router.delete("/entries")
def delete_entries_for_month(
    exercice_id: int = Query(...),
    jnl: str = Query(...),
    month: str = Query(..., description='YYYY-MM'),
    db: Session = Depends(get_db),
):
    # parse month
    try:
        year = int(month.split("-")[0])
        mon = int(month.split("-")[1])
        first_day = dt.date(year, mon, 1)
        if mon == 12:
            last_day = dt.date(year, 12, 31)
        else:
            last_day = dt.date(year, mon + 1, 1) - dt.timedelta(days=1)
    except Exception:
        raise HTTPException(400, detail="Paramètre month invalide (attendu YYYY-MM)")

    ex = get_exercice(db, exercice_id)
    # borne aux dates de l'exercice
    d1 = max(first_day, ex.date_start)
    d2 = min(last_day, ex.date_end)
    if d1 > d2:
        return {"deleted_count": 0}

    res = db.execute(
        delete(Entry).where(
            Entry.exercice_id == exercice_id,
            Entry.jnl == jnl,
            Entry.date >= d1,
            Entry.date <= d2,
        )
    )
    deleted = res.rowcount or 0
    db.commit()
    return {"deleted_count": int(deleted)}
