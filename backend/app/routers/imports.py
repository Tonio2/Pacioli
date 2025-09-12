from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from sqlalchemy.orm import Session
from sqlalchemy import select
from decimal import Decimal
from datetime import datetime
import csv, io, re
from ..database import get_db
from ..models import Entry, Exercice, HistoryEvent, Account
from ..validators import ensure_batch_balanced, ensure_dates_in_exercice, ValidationError
from ..crud import find_or_create_account, find_or_create_journal, list_unbalanced_pieces, get_exercice

router = APIRouter(prefix="/api/imports", tags=["imports"])

_amount_clean_re = re.compile(r"[\s\u00A0]\s*")

def parse_amount(s: str) -> Decimal:
    s = s.strip()
    s = _amount_clean_re.sub("", s)
    s = s.replace("\u00A0", "").replace(" ", "")
    s = s.replace(",", ".")
    return Decimal(s)

def parse_date(s: str):
    s = s.strip()
    if "/" in s:
        return datetime.strptime(s, "%d/%m/%Y").date()
    return datetime.strptime(s, "%Y-%m-%d").date()

@router.post("/csv")
async def import_csv(
    client_id: int = Form(...),
    exercice_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    try:
        ex = get_exercice(db, exercice_id)
    except ValueError as e:
        raise HTTPException(400, str(e))

    raw = await file.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")

    if not text.strip():
        raise HTTPException(400, "Fichier vide")

    sample = text.splitlines()[0]
    try:
        dialect = csv.Sniffer().sniff(sample)
    except Exception:
        dialect = csv.excel
        dialect.delimiter = ";"

    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    required = {"jnl", "accnum", "acclib", "date", "lib", "pieceRef", "debit", "credit", "pieceDate", "validDate", "montant", "iDevise"}
    missing = required - set([h.strip() for h in (reader.fieldnames or [])])
    if missing:
        raise HTTPException(400, f"Colonnes manquantes: {', '.join(sorted(missing))}")

    rows = []
    delta_rows = []

    for i, row in enumerate(reader, start=2):
        try:
            jnl = (row["jnl"] or "").strip()
            accnum = (row["accnum"] or "").strip()
            acclib = (row["acclib"] or "").strip() or accnum
            date_obj = parse_date(row["date"])
            lib = (row["lib"] or "").strip()
            piece_ref = (row["pieceRef"] or "").strip()
            debit = parse_amount(row["debit"])
            credit = parse_amount(row["credit"])
            piece_date = parse_date(row["pieceDate"]) if row["pieceDate"] else date_obj
            valid_date = parse_date(row["validDate"]) if row["validDate"] else date_obj
            if jnl == "AN":
                piece_date = ex.date_start
                valid_date = ex.date_start
            montant = parse_amount(row["montant"]) if row["montant"] else None
            i_devise = row["iDevise"] or None
        except Exception as e:
            raise HTTPException(400, f"Erreur parsing ligne {i}: {e}")

        if (debit > 0 and credit > 0) or (debit == 0 and credit == 0):
            raise HTTPException(400, f"Ligne {i}: chaque ligne doit avoir soit un débit soit un crédit (exclusif)")

        rows.append(
            {
                "client_id": client_id,
                "exercice_id": exercice_id,
                "date": date_obj,
                "jnl": jnl,
                "piece_ref": piece_ref,
                "accnum": accnum,   # temporaire pour résolution
                "acclib": acclib,   # temporaire pour création si besoin
                "lib": lib,
                "debit": debit,
                "credit": credit,
                "piece_date": piece_date,
                "valid_date": valid_date,
                "montant": montant,
                "i_devise": i_devise
            }
        )
        delta_rows.append({"date": date_obj, "debit": debit, "credit": credit})

    try:
        ensure_dates_in_exercice(rows, ex.date_start, ex.date_end)
        ensure_batch_balanced(delta_rows)
    except ValidationError as ve:
        raise HTTPException(400, str(ve))

    # Pré-création/synchro journaux & comptes (sans MAJ acclib si existent)
    seen_acc = {}
    seen_jnl = set()
    f = csv.DictReader(io.StringIO(text), dialect=dialect)
    for r in f:
        accnum = (r["accnum"] or "").strip()
        acclib = (r["acclib"] or "").strip() or accnum
        jnl = (r["jnl"] or "").strip()
        if accnum and accnum not in seen_acc:
            # find_or_create ne modifie pas un compte existant
            find_or_create_account(db, client_id, accnum, acclib)
            seen_acc[accnum] = True
        if jnl and jnl not in seen_jnl:
            find_or_create_journal(db, client_id, jnl, None)
            seen_jnl.add(jnl)

    # Insertion
    try:
        for r in rows:
            acc = db.execute(
                select(Account).where(Account.client_id==client_id, Account.accnum==r["accnum"])
            ).scalar_one_or_none()
            if acc is None:
                acc = find_or_create_account(db, client_id, r["accnum"], r["acclib"] or r["accnum"])
            db.add(Entry(
                client_id=client_id,
                exercice_id=exercice_id,
                date=r["date"],
                jnl=r["jnl"],
                piece_ref=r["piece_ref"],
                account_id=acc.id,
                lib=r["lib"],
                debit=r["debit"],
                credit=r["credit"],
                piece_date=r["piece_date"],
                valid_date=r["valid_date"],
                montant=r["montant"],
                i_devise=r["i_devise"]
            ))
        he = HistoryEvent(
            client_id=client_id,
            exercice_id=exercice_id,
            description=f"Importer {len(rows)} écritures",
            counts_json=f'{{"added":{len(rows)}}}',
        )
        db.add(he)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Erreur lors de l'insertion: {e}")

    warnings = {"unbalanced_pieces": list_unbalanced_pieces(db, exercice_id, limit=50)}
    return {"added": len(rows), "warnings": warnings}
