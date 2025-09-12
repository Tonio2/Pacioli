from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, delete
from decimal import Decimal
from ..database import get_db
from ..models import Entry, HistoryEvent, Account
from ..schemas import PieceCommitRequest
from ..validators import ensure_batch_balanced, ensure_dates_in_exercice
from ..crud import list_unbalanced_pieces, get_exercice, find_or_create_account

router = APIRouter(prefix="/api", tags=["piece"])

@router.get("/piece")
def get_piece(client_id: int, exercice_id: int, journal: str, piece_ref: str, db: Session = Depends(get_db)):
    q = (
        select(Entry)
        .options(selectinload(Entry.account))
        .where(
            Entry.client_id == client_id,
            Entry.exercice_id == exercice_id,
            Entry.jnl == journal,
            Entry.piece_ref == piece_ref,
        )
        .order_by(Entry.date.asc(), Entry.id.asc())
    )
    rows = db.execute(q).scalars().all()
    return {"rows": [
        {
            "id": r.id,
            "date": r.date.isoformat(),
            "jnl": r.jnl,
            "piece_ref": r.piece_ref,
            "account_id": r.account_id,
            "accnum": r.account.accnum if r.account else "",
            "acclib": r.account.acclib if r.account else "",
            "lib": r.lib,
            "debit": Decimal(r.debit or 0),
            "credit": Decimal(r.credit or 0),
        }
        for r in rows
    ]}

@router.post("/piece/commit")
def commit_piece(req: PieceCommitRequest, db: Session = Depends(get_db)):
    ex = get_exercice(db, req.exercice_id)

    # Construire le lot (delta) pour validation
    delta_rows = []
    to_add = []
    to_mod = []
    to_del = []

    existing = {e.id: e for e in db.execute(
        select(Entry).where(
            Entry.client_id==req.client_id,
            Entry.exercice_id==req.exercice_id,
            Entry.jnl==req.journal,
            Entry.piece_ref==req.piece_ref,
        )
    ).scalars().all()}

    for ch in req.changes:
        if ch.op == "add":
            if ch.date is None or ch.accnum is None or ch.lib is None:
                raise HTTPException(400, "add: date, accnum, lib requis")
            d = {"date": ch.date, "debit": ch.debit or 0, "credit": ch.credit or 0}
            delta_rows.append({"date": ch.date, "debit": ch.debit or 0, "credit": ch.credit or 0})
            to_add.append(ch)
        elif ch.op == "modify":
            if not ch.entry_id or ch.entry_id not in existing:
                raise HTTPException(400, "modify: entry_id invalide")
            old = existing[ch.entry_id]
            new_date = ch.date or old.date
            new_debit = Decimal(ch.debit) if ch.debit is not None else old.debit
            new_credit = Decimal(ch.credit) if ch.credit is not None else old.credit
            delta_rows.append({"date": new_date, "debit": new_debit - old.debit, "credit": new_credit - old.credit})
            to_mod.append(ch)
        elif ch.op == "delete":
            if not ch.entry_id or ch.entry_id not in existing:
                raise HTTPException(400, "delete: entry_id invalide")
            old = existing[ch.entry_id]
            delta_rows.append({"date": old.date, "debit": Decimal("0") - old.debit, "credit": Decimal("0") - old.credit})
            to_del.append(ch)
        else:
            raise HTTPException(400, "op inconnue")

    ensure_dates_in_exercice(
        [r for r in ([{"date": ch.date} for ch in to_add if ch.date] + [{"date": (ch.date or existing[ch.entry_id].date)} for ch in to_mod])],
        ex.date_start, ex.date_end
    )
    ensure_batch_balanced(delta_rows)

    added = modified = deleted = 0
    try:
        # Adds
        for ch in to_add:
            # Résoudre ou créer le compte. N'update JAMAIS acclib si existe déjà.
            acc = db.execute(
                select(Account).where(Account.client_id==req.client_id, Account.accnum==ch.accnum)
            ).scalar_one_or_none()
            if acc is None:
                acc = find_or_create_account(db, req.client_id, ch.accnum, (ch.acclib or ch.accnum))
            e = Entry(
                client_id=req.client_id,
                exercice_id=req.exercice_id,
                date=ch.date,
                jnl=req.journal,
                piece_ref=req.piece_ref,
                account_id=acc.id,
                lib=ch.lib,
                debit=Decimal(ch.debit or 0),
                credit=Decimal(ch.credit or 0),
                piece_date=ch.date,
                valid_date=ch.date
            )
            db.add(e)
            added += 1

        # Mods
        for ch in to_mod:
            e = existing[ch.entry_id]
            if ch.date is not None:
                e.date = ch.date
            if ch.accnum is not None:
                acc = db.execute(
                    select(Account).where(Account.client_id==req.client_id, Account.accnum==ch.accnum)
                ).scalar_one_or_none()
                if acc is None:
                    acc = find_or_create_account(db, req.client_id, ch.accnum, (getattr(ch, "acclib", None) or ch.accnum))
                e.account_id = acc.id
            if ch.lib is not None:
                e.lib = ch.lib
            if ch.debit is not None:
                e.debit = Decimal(ch.debit)
            if ch.credit is not None:
                e.credit = Decimal(ch.credit)
            modified += 1

        # Dels
        for ch in to_del:
            e = existing[ch.entry_id]
            db.delete(e)
            deleted += 1

        db.flush()

        he = HistoryEvent(client_id=req.client_id, exercice_id=req.exercice_id, description=req.description or "", counts_json=f"{{\"added\":{added},\"modified\":{modified},\"deleted\":{deleted}}}")
        db.add(he)
        db.commit()
    except Exception:
        db.rollback()
        raise

    warnings = {"unbalanced_pieces": list_unbalanced_pieces(db, req.exercice_id, limit=50)}
    return {"added": added, "modified": modified, "deleted": deleted, "warnings": warnings}
