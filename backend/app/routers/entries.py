from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, func
from typing import Optional
from ..database import get_db
from ..models import Entry, Account
from ..schemas import EntriesResponse, EntryOut

router = APIRouter(prefix="/api/entries", tags=["entries"])

@router.get("", response_model=EntriesResponse)
def list_entries(
    client_id: int = Query(...),
    exercice_id: int = Query(...),
    journal: Optional[str] = None,
    compte: Optional[str] = None,   # accnum
    piece_ref: Optional[str] = None,
    min_date: Optional[str] = None,
    max_date: Optional[str] = None,
    min_amt: Optional[float] = None,
    max_amt: Optional[float] = None,
    search: Optional[str] = None,
    sort: Optional[str] = "date,id",   # accepte "accnum"
    page: int = 1,
    page_size: int = 20000,
    db: Session = Depends(get_db),
):
    if page < 1 or page_size < 1:
        raise HTTPException(400, "page/page_size invalides")

    # Base query: on sélectionne des Entry, on précharge Account pour éviter N+1
    q = (
        select(Entry)
        .options(selectinload(Entry.account))
        .where(Entry.client_id == client_id, Entry.exercice_id == exercice_id)
    )

    # Filtres simples
    if journal:
        q = q.where(Entry.jnl == journal)
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

    # Besoin d'un JOIN Account ? (filtre par compte ou tri sur accnum)
    sort_parts = [(p.strip(), p.strip().startswith("-")) for p in (sort or "").split(",") if p.strip()]
    needs_account_join = bool(compte) or any((s[0][1:] if s[1] else s[0]) == "accnum" for s in sort_parts)

    if compte:
        # Filtrer par Account.accnum
        q = q.join(Account, Account.id == Entry.account_id).where(Account.accnum == compte)

    # Tri limité (possède accnum via Account)
    # NB: si tri par accnum demandé, on s'assure d'avoir le JOIN.
    if needs_account_join and not compte:
        q = q.join(Account, Account.id == Entry.account_id)

    allowed = {
        "date": Entry.date,
        "jnl": Entry.jnl,
        "piece_ref": Entry.piece_ref,
        "debit": Entry.debit,
        "credit": Entry.credit,
        "id": Entry.id,
        "accnum": Account.accnum,   # tri via Account
    }

    order_cols = []
    for part, is_desc in sort_parts:
        key = part[1:] if is_desc else part
        col = allowed.get(key)
        if col is not None:
            order_cols.append(col.desc() if is_desc else col.asc())
    if not order_cols:
        order_cols = [Entry.date.asc(), Entry.id.asc()]

    # Total avant pagination
    total = db.scalar(select(func.count()).select_from(q.subquery()))

    # Pagination
    q = q.order_by(*order_cols).offset((page - 1) * page_size).limit(page_size)

    rows = db.execute(q).scalars().all()

    # Construire la sortie enrichie (accnum/acclib viennent de la relation Account)
    out_rows = []
    for e in rows:
        accnum = e.account.accnum if e.account else ""
        acclib = e.account.acclib if e.account else ""
        out_rows.append(EntryOut(
            id=e.id,
            date=e.date,
            jnl=e.jnl,
            piece_ref=e.piece_ref,
            account_id=e.account_id,
            accnum=accnum,
            acclib=acclib,
            lib=e.lib,
            debit=e.debit,
            credit=e.credit,
        ))

    return {"rows": out_rows, "total": int(total or 0)}
