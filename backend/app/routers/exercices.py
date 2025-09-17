from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, select

from ..crud import find_or_create_account
from ..database import get_db
from ..models import Account, Entry, Exercice, HistoryEvent, JournalSequence
from ..schemas import ANRequest, ANResponse, ExerciceCreate, ExerciceOut

router = APIRouter(prefix="/api/exercices", tags=["exercices"])

@router.get("", response_model=list[ExerciceOut])
def list_exercices(client_id: int = Query(...), db: Session = Depends(get_db)):
    return db.execute(
        select(Exercice)
        .where(Exercice.client_id == client_id)
        .order_by(Exercice.date_start.desc())
    ).scalars().all()

@router.post("", response_model=ExerciceOut)
def create_exercice(payload: ExerciceCreate, db: Session = Depends(get_db)):
    e = Exercice(**payload.model_dump())
    db.add(e); db.commit(); db.refresh(e)
    return e

@router.patch("/{id}", response_model=ExerciceOut)
def update_exercice(id: int, payload: ExerciceCreate, db: Session = Depends(get_db)):
    e = db.get(Exercice, id)
    if not e:
        raise HTTPException(404)
    for k, v in payload.model_dump().items():
        setattr(e, k, v)
    db.commit(); db.refresh(e)
    return e

@router.delete("/{id}")
def delete_exercice(id: int, db: Session = Depends(get_db)):
    e = db.get(Exercice, id)
    if not e:
        raise HTTPException(404)
    db.delete(e); db.commit()
    return {"ok": True}


@router.post("/closing/an", response_model=ANResponse)
def generate_a_n(req: ANRequest, db: Session = Depends(get_db)):
    # 1) Charger exercices + contrôles
    source = db.get(Exercice, req.source_exercice_id)
    target = db.get(Exercice, req.target_exercice_id)
    if not source or not target:
        raise HTTPException(400, "Exercice source ou cible introuvable")
    if source.client_id != target.client_id:
        raise HTTPException(400, "Les exercices doivent appartenir au même client")
    if target.status != "OPEN":
        raise HTTPException(409, "L'exercice cible doit être OPEN")
    journal = (req.journal or "AN").strip()
    if not journal:
        raise HTTPException(400, "Journal invalide")

    piece_ref = f"{journal}-00001"
    date_an = target.date_start

    # 2) Gérer overwrite / existence de la pièce AN-00001
    existing_count = db.execute(
        select(func.count(Entry.id)).where(
            Entry.exercice_id == target.id,
            Entry.jnl == journal,
            Entry.piece_ref == piece_ref,
        )
    ).scalar_one()
    if existing_count > 0:
        if not req.overwrite:
            raise HTTPException(409, f"Des à-nouveaux existent déjà ({piece_ref}). Utilisez overwrite=true.")
        # delete existants
        db.execute(
            Entry.__table__.delete().where(
                Entry.exercice_id == target.id,
                Entry.jnl == journal,
                Entry.piece_ref == piece_ref,
            )
        )
        db.flush()

    # 3) Construire la balance 1–5 du source
    sub = (
        select(
            Entry.account_id.label("account_id"),
            func.sum(Entry.debit_minor).label("debit_minor"),
            func.sum(Entry.credit_minor).label("credit_minor"),
        )
        .where(Entry.exercice_id == source.id)
        .group_by(Entry.account_id)
        .subquery()
    )

    rows = db.execute(
        select(
            Account.id.label("account_id"),
            Account.accnum.label("accnum"),
            func.coalesce(sub.c.debit_minor, 0).label("debit_minor"),
            func.coalesce(sub.c.credit_minor, 0).label("credit_minor"),
        )
        .join(Account, Account.id == sub.c.account_id)
        .where(
            Account.client_id == source.client_id,
            or_(
                Account.accnum.like("1%"),
                Account.accnum.like("2%"),
                Account.accnum.like("3%"),
                Account.accnum.like("4%"),
                Account.accnum.like("5%"),
            ),
        )
        .order_by(Account.accnum.asc())
    ).all()

    # 4) Préparer les lignes AN pour les comptes 1–5
    to_insert: list[Entry] = []
    total_debit = 0
    total_credit = 0
    lib = "A NOUVEAUX"

    for r in rows:
        solde = int((r.debit_minor or 0) - (r.credit_minor or 0))
        if solde == 0:
            continue
        debit = credit = 0
        if solde > 0: debit = solde
        else: credit = -solde
        e = Entry(
            exercice_id=target.id,
            date=date_an,
            jnl=journal,
            piece_ref=piece_ref,
            account_id=r.account_id,
            lib=lib,
            debit_minor=debit,
            credit_minor=credit,
            piece_date=date_an,
            valid_date=date_an,
        )
        total_debit += debit
        total_credit += credit
        to_insert.append(e)

    if len(to_insert) == 0:
        raise HTTPException(422, "Aucun solde de bilan (classes 1–5) à reprendre pour l'exercice source")

    # 5) Contrepartie 120 pour équilibrer (si nécessaire)
    diff = total_debit - total_credit
    result_account_used: str | None = None
    if diff != 0:
        # trouver ou créer 120000
        acc_120 = db.execute(
            select(Account).where(
                Account.client_id == source.client_id,
                Account.accnum == "120000",
            )
        ).scalar_one_or_none()
        if acc_120 is None:
            # crée le compte sans modifier acclib si déjà existe (mais ici None)
            acc_120 = find_or_create_account(db, source.client_id, "120000", "COMPTE DE RESULTAT")
            db.flush()
        result_account_used = acc_120.accnum

        debit = credit = 0
        if diff > 0: credit = diff
        else: debit = -diff
        to_insert.append(
            Entry(
                exercice_id=target.id,
                date=date_an,
                jnl=journal,
                piece_ref=piece_ref,
                account_id=acc_120.id,
                lib=lib,
                debit_minor=debit,
                credit_minor=credit,
                piece_date=date_an,
                valid_date=date_an,
            )
        )
        total_credit += credit
        total_debit += debit

    # Sécurité : totals doivent matcher
    print(total_credit, total_debit)
    assert total_debit == total_credit, "Pièce AN non équilibrée (bug interne)"

    # 6) Insertion + HistoryEvent + JournalSequence
    try:
        for e in to_insert:
            db.add(e)
        db.flush()

        # Historisation sur exercice cible
        he = HistoryEvent(
            exercice_id=target.id,
            description=f"AN {source.label} → {target.label} (jnl {journal}, pièce {piece_ref})",
            counts_json=f"{{\"added\":{len(to_insert)},\"modified\":{0},\"deleted\":{0}}}"
        )
        db.add(he)
        db.flush()

        # Séquence : fixer à 1 minimum
        seq = db.execute(
            select(JournalSequence).where(
                JournalSequence.exercice_id == target.id,
                JournalSequence.jnl == journal,
            )
        ).scalar_one_or_none()
        if seq is None:
            seq = JournalSequence(exercice_id=target.id, jnl=journal, last_number=1)
            db.add(seq)
        else:
            if seq.last_number < 1:
                seq.last_number = 1

        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "created": {
            "piece_ref": piece_ref,
            "lines": len(to_insert),
            "total_debit_minor": total_debit,
            "total_credit_minor": total_credit,
            "result_account": result_account_used,
        }
    }
