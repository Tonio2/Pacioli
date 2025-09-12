# backend/app/routers/controls.py
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from decimal import Decimal

from ..schemas import UnbalancedJournalListResponse, UnbalancedPieceListResponse
from ..database import get_db
from ..models import Entry

router = APIRouter(prefix="/api/controls", tags=["controls"])

def _d(x) -> Decimal:
    return Decimal(x or 0)

def _fmt_csv_val(v: str) -> str:
    # CSV simple ; si tu préfères le TSV, remplace ';' par '\t'
    return (v or "").replace("\n", " ").replace(";", " ")

@router.get("/unbalanced-pieces", response_model=UnbalancedPieceListResponse)
def unbalanced_pieces(
    exercice_id: int = Query(...),
    page: int = 1,
    page_size: int = 100,
    db: Session = Depends(get_db),
):
    if page < 1 or page_size < 1:
        page, page_size = 1, 100

    sub = (
        select(
            Entry.jnl.label("jnl"),
            Entry.piece_ref.label("piece_ref"),
            func.count().label("count"),
            func.sum(Entry.debit).label("debit"),
            func.sum(Entry.credit).label("credit"),
        )
        .where(Entry.exercice_id == exercice_id)
        .group_by(Entry.jnl, Entry.piece_ref)
        .having(func.coalesce(func.sum(Entry.debit), 0) != func.coalesce(func.sum(Entry.credit), 0))
        .subquery()
    )

    total = db.scalar(select(func.count()).select_from(sub)) or 0

    q = (
        select(
            sub.c.jnl,
            sub.c.piece_ref,
            sub.c.count,
            sub.c.debit,
            sub.c.credit,
        )
        .order_by(sub.c.jnl, sub.c.piece_ref)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = db.execute(q).all()

    items = []
    for r in rows:
        debit = Decimal(r.debit or 0)
        credit = Decimal(r.credit or 0)
        diff = debit - credit
        if diff != 0:   # <— garde seulement les vrais déséquilibres
            items.append({
                "jnl": r.jnl,
                "piece_ref": r.piece_ref,
                "count": r.count or 0,
                "debit": debit,
                "credit": credit,
                "diff": diff,
            })

    return {"items": items, "total": int(total)}

@router.get("/unbalanced-pieces/export")
def unbalanced_pieces_export(
    exercice_id: int = Query(...),
    db: Session = Depends(get_db),
):
    sub = (
        select(
            Entry.jnl.label("jnl"),
            Entry.piece_ref.label("piece_ref"),
            func.count().label("count"),
            func.sum(Entry.debit).label("debit"),
            func.sum(Entry.credit).label("credit"),
        )
        .where(Entry.exercice_id == exercice_id)
        .group_by(Entry.jnl, Entry.piece_ref)
        .having(func.coalesce(func.sum(Entry.debit), 0) != func.coalesce(func.sum(Entry.credit), 0))
        .order_by(Entry.jnl, Entry.piece_ref)
    )

    rows = db.execute(sub).all()

    def fmt(n: Decimal) -> str:
        # format FR ; change si besoin
        return f"{_d(n):.2f}".replace(".", ",")

    lines = ["journal;piece_ref;nb_ecritures;debit;credit;diff"]
    for r in rows:
        debit = _d(r.debit)
        credit = _d(r.credit)
        diff = debit - credit
        lines.append(
            ";".join(
                [
                    _fmt_csv_val(r.jnl or ""),
                    _fmt_csv_val(r.piece_ref or ""),
                    str(r.count or 0),
                    fmt(debit),
                    fmt(credit),
                    fmt(diff),
                ]
            )
        )

    content = "\n".join(lines) + "\n"
    headers = {
        "Content-Type": "text/csv; charset=utf-8",
        "Content-Disposition": f'attachment; filename="pieces_desequilibre.csv"',
    }
    return Response(content=content, media_type="text/csv", headers=headers)

@router.get("/unbalanced-journals", response_model=UnbalancedJournalListResponse)
def unbalanced_journals(
    exercice_id: int = Query(...),
    db: Session = Depends(get_db),
):
    sub = (
        select(
            Entry.jnl.label("jnl"),
            func.count().label("count"),
            func.sum(Entry.debit).label("debit"),
            func.sum(Entry.credit).label("credit"),
        )
        .where(Entry.exercice_id == exercice_id)
        .group_by(Entry.jnl)
        .having(func.coalesce(func.sum(Entry.debit), 0) != func.coalesce(func.sum(Entry.credit), 0))
        .order_by(Entry.jnl)
    )
    rows = db.execute(sub).all()
    items = [
        {
            "jnl": r.jnl,
            "count": r.count or 0,
            "debit": Decimal(r.debit or 0),
            "credit": Decimal(r.credit or 0),
            "diff": Decimal(r.debit or 0) - Decimal(r.credit or 0),
        }
        for r in rows
    ]
    return {"items": items, "total": len(items)}

@router.get("/unbalanced-journals/export")
def unbalanced_journals_export(
    exercice_id: int = Query(...),
    db: Session = Depends(get_db),
):
    sub = (
        select(
            Entry.jnl.label("jnl"),
            func.count().label("count"),
            func.sum(Entry.debit).label("debit"),
            func.sum(Entry.credit).label("credit"),
        )
        .where(Entry.exercice_id == exercice_id)
        .group_by(Entry.jnl)
        .having(func.coalesce(func.sum(Entry.debit), 0) != func.coalesce(func.sum(Entry.credit), 0))
        .order_by(Entry.jnl)
    )
    rows = db.execute(sub).all()

    def fmt(n: Decimal) -> str:
        return f"{_d(n):.2f}".replace(".", ",")

    lines = ["journal;nb_ecritures;debit;credit;diff"]
    for r in rows:
        debit = _d(r.debit)
        credit = _d(r.credit)
        diff = debit - credit
        lines.append(
            ";".join(
                [
                    _fmt_csv_val(r.jnl or ""),
                    str(r.count or 0),
                    fmt(debit),
                    fmt(credit),
                    fmt(diff),
                ]
            )
        )

    content = "\n".join(lines) + "\n"
    headers = {
        "Content-Type": "text/csv; charset=utf-8",
        "Content-Disposition": f'attachment; filename="journaux_desequilibre.csv"',
    }
    return Response(content=content, media_type="text/csv", headers=headers)
