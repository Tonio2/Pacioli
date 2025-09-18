from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func, select
from ..database import get_db
from ..models import Entry, HistoryEvent, Account, JournalSequence
from ..schemas import PieceCommitRequest, PieceCommitResponse, PieceGetResponse
from ..validators import ensure_batch_balanced_minor, ensure_dates_in_exercice, check_one_side
from ..crud import get_next_ref, list_unbalanced_pieces, get_exercice, find_or_create_account

router = APIRouter(prefix="/api", tags=["piece"])

@router.get("/piece/next_ref")
def look_next_ref(exercice_id: int, journal: str, width: int = 5, db: Session = Depends(get_db)):
    return get_next_ref(db, exercice_id, journal)


@router.get("/piece", response_model=PieceGetResponse)
def get_piece(exercice_id: int, journal: str, piece_ref: str, db: Session = Depends(get_db)):
    q = (
        select(Entry)
        .options(selectinload(Entry.account))
        .where(
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
            "date": r.date,
            "jnl": r.jnl,
            "piece_ref": r.piece_ref,
            "account_id": r.account_id,
            "accnum": r.account.accnum if r.account else "",
            "acclib": r.account.acclib if r.account else "",
            "lib": r.lib,
            "debit_minor": r.debit_minor or 0,
            "credit_minor": r.credit_minor or 0,
        }
        for r in rows
    ]}

@router.post("/piece/commit", response_model=PieceCommitResponse)
def commit_piece(req: PieceCommitRequest, db: Session = Depends(get_db)):
    ex = get_exercice(db, req.exercice_id)
    client_id = ex.client_id

    # Construire le lot (delta) pour validation
    delta_rows = []
    to_add = []
    to_mod = []
    to_del = []

    existing = {e.id: e for e in db.execute(
        select(Entry).where(
            Entry.exercice_id==req.exercice_id,
            Entry.jnl==req.journal,
            Entry.piece_ref==req.piece_ref,
        )
    ).scalars().all()}


    for ch in req.changes:
        if ch.op == "add":
            if ch.date is None or ch.accnum is None or ch.lib is None:
                raise HTTPException(400, "add: date, accnum, lib requis")
            check_one_side(ch.debit_minor, ch.credit_minor)
            delta_rows.append({"date": ch.date, "debit_minor": ch.debit_minor or 0, "credit_minor": ch.credit_minor or 0})
            to_add.append(ch)
        elif ch.op == "modify":
            if not ch.entry_id or ch.entry_id not in existing:
                raise HTTPException(400, "modify: entry_id invalide")
            old = existing[ch.entry_id]
            new_date = ch.date or old.date
            new_debit_minor = ch.debit_minor if ch.debit_minor is not None else old.debit_minor
            new_credit_minor = ch.credit_minor if ch.credit_minor is not None else old.credit_minor
            delta_rows.append({
                "date": new_date,
                "debit_minor": new_debit_minor - old.debit_minor,
                "credit_minor": new_credit_minor - old.credit_minor
            })
            to_mod.append(ch)
        elif ch.op == "delete":
            if not ch.entry_id or ch.entry_id not in existing:
                raise HTTPException(400, "delete: entry_id invalide")
            old = existing[ch.entry_id]
            delta_rows.append({"date": old.date, "debit_minor": -old.debit_minor, "credit_minor": -old.credit_minor})
            to_del.append(ch)
        else:
            raise HTTPException(400, "op inconnue")

    ensure_dates_in_exercice(
        [r for r in ([{"date": ch.date} for ch in to_add if ch.date] + [{"date": (ch.date or existing[ch.entry_id].date)} for ch in to_mod])],
        ex.date_start, ex.date_end
    )
    ensure_batch_balanced_minor(delta_rows)

    added = modified = deleted = 0
    try:
        # Adds
        for ch in to_add:
            # Résoudre ou créer le compte. N'update JAMAIS acclib si existe déjà.
            acc = db.execute(
                select(Account).where(Account.client_id==client_id, Account.accnum==ch.accnum)
            ).scalar_one_or_none()
            if acc is None:
                acc = find_or_create_account(db, client_id, ch.accnum, (ch.acclib or ch.accnum))
            e = Entry(
                exercice_id=req.exercice_id,
                date=ch.date,
                jnl=req.journal,
                piece_ref=req.piece_ref,
                account_id=acc.id,
                lib=ch.lib,
                debit_minor=ch.debit_minor or 0,
                credit_minor=ch.credit_minor or 0,
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
                    select(Account).where(Account.client_id==client_id, Account.accnum==ch.accnum)
                ).scalar_one_or_none()
                if acc is None:
                    acc = find_or_create_account(db, client_id, ch.accnum, (getattr(ch, "acclib", None) or ch.accnum))
                e.account_id = acc.id
            if ch.lib is not None:
                e.lib = ch.lib
            if ch.debit_minor is not None:
                e.debit_minor = ch.debit_minor
            if ch.credit_minor is not None:
                e.credit_minor = ch.credit_minor
            modified += 1

        # Dels
        for ch in to_del:
            e = existing[ch.entry_id]
            db.delete(e)
            deleted += 1

        db.flush()

        he = HistoryEvent(
            exercice_id=req.exercice_id,
            description=req.description or "",
            counts_json=f"{{\"added\":{added},\"modified\":{modified},\"deleted\":{deleted}}}"
        )
        db.add(he)
        db.commit()

        is_new_piece = (len(existing) == 0 and added > 0)

        if is_new_piece:
            seq = db.execute(
                select(JournalSequence).where(
                    JournalSequence.exercice_id == req.exercice_id,
                    JournalSequence.jnl == req.journal
                )
            ).scalar_one_or_none()

            if seq is None:
                seq = JournalSequence(exercice_id=req.exercice_id, jnl=req.journal, last_number=0)
                db.add(seq)
                db.flush()
            else:
                start = seq.last_number + 1
                cand = f"{req.journal}-{start:05d}"
                if req.piece_ref == cand:
                    seq.last_number = start
            db.commit()

    except Exception:
        db.rollback()
        raise

    warnings = {"unbalanced_pieces": list_unbalanced_pieces(db, req.exercice_id, limit=50)}
    return {"added": added, "modified": modified, "deleted": deleted, "warnings": warnings}
