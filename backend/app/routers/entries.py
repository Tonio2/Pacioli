from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func
from typing import Optional
from ..database import get_db
from ..models import Entry
from ..schemas import EntriesResponse, EntryOut

router = APIRouter(prefix="/api/entries", tags=["entries"])

@router.get("", response_model=EntriesResponse)
def list_entries(
    client_id: int = Query(...),
    exercice_id: int = Query(...),
    journal: Optional[str] = None,
    compte: Optional[str] = None,
    piece_ref: Optional[str] = None,
    min_date: Optional[str] = None,
    max_date: Optional[str] = None,
    min_amt: Optional[float] = None,
    max_amt: Optional[float] = None,
    search: Optional[str] = None,
    sort: Optional[str] = "date,id",
    page: int = 1,
    page_size: int = 20000,
    db: Session = Depends(get_db),
):
    if page < 1 or page_size < 1:
        raise HTTPException(400, "page/page_size invalides")

    q = select(Entry).where(Entry.client_id==client_id, Entry.exercice_id==exercice_id)

    if journal:
        q = q.where(Entry.jnl == journal)
    if compte:
        q = q.where(Entry.accnum == compte)
    if piece_ref:
        q = q.where(Entry.piece_ref == piece_ref)
    if min_date:
        q = q.where(Entry.date >= min_date)
    if max_date:
        q = q.where(Entry.date <= max_date)
    if min_amt is not None:
        q = q.where((Entry.debit - Entry.credit) >= min_amt)
    if max_amt is not None:
        q = q.where((Entry.debit - Entry.credit) <= max_amt)
    if search:
        like = f"%{search}%"
        q = q.where(Entry.lib.ilike(like))

    # Tri limité
    allowed = {"date": Entry.date, "accnum": Entry.accnum, "jnl": Entry.jnl, "piece_ref": Entry.piece_ref, "debit": Entry.debit, "credit": Entry.credit, "id": Entry.id}
    order_cols = []
    for part in (sort or "").split(","):
        part = part.strip()
        if not part:
            continue
        desc = part.startswith("-")
        key = part[1:] if desc else part
        col = allowed.get(key)
        if col is not None:
            order_cols.append(col.desc() if desc else col.asc())
    if not order_cols:
        order_cols = [Entry.date.asc(), Entry.id.asc()]

    total = db.scalar(select(func.count()).select_from(q.subquery()))
    q = q.order_by(*order_cols).offset((page-1)*page_size).limit(page_size)
    rows = db.execute(q).scalars().all()
    return {"rows": [EntryOut.model_validate(r) for r in rows], "total": int(total or 0)}
