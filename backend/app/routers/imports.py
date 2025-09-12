from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from sqlalchemy.orm import Session
from sqlalchemy import select
from decimal import Decimal
from datetime import datetime
import csv, io, re
from ..database import get_db
from ..models import Entry, Exercice, HistoryEvent
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
    # 1) exercice & fichier
    try:
        ex = get_exercice(db, exercice_id)
    except ValueError as e:
        raise HTTPException(400, str(e))

    raw = await file.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")

    # 2) DictReader + autodetect delimiter
    if not text.strip():
        raise HTTPException(400, "Fichier vide")

    sample = text.splitlines()[0]
    try:
        dialect = csv.Sniffer().sniff(sample)
    except Exception:
        dialect = csv.excel
        dialect.delimiter = ";"  # par défaut FR
    print(dialect.delimiter)

    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    required = {"jnl", "accnum", "acclib", "date", "lib", "pieceRef", "debit", "credit"}
    missing = required - set([h.strip() for h in (reader.fieldnames or [])])
    if missing:
        raise HTTPException(400, f"Colonnes manquantes: {', '.join(sorted(missing))}")

    rows = []
    delta_rows = []

    # 3) parse + validations par ligne
    for i, row in enumerate(reader, start=2):  # start=2 (ligne 1 = header)
        try:
            print(row)
            print(row["debit"], row["credit"])
            jnl = (row["jnl"] or "").strip()
            accnum = (row["accnum"] or "").strip()
            acclib = (row["acclib"] or "").strip() or accnum
            date_obj = parse_date(row["date"])
            lib = (row["lib"] or "").strip()
            piece_ref = (row["pieceRef"] or "").strip()
            debit = parse_amount(row["debit"])
            credit = parse_amount(row["credit"])
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
                "accnum": accnum,
                "lib": lib,
                "debit": float(debit),
                "credit": float(credit),
                # NB: Entry.debit/credit sont mappés Numeric(14,2) mais typés float côté ORM.
            }
        )
        delta_rows.append({"date": date_obj, "debit": debit, "credit": credit})

    # 4) validations bloquantes (lot)
    try:
        ensure_dates_in_exercice(rows, ex.date_start, ex.date_end)
        ensure_batch_balanced(delta_rows)
    except ValidationError as ve:
        raise HTTPException(400, str(ve))

    # 5) find-or-create plans (sans écraser les libellés existants)
    #    NB: on relit acclib/jnl_lib depuis le fichier mais on ne met pas à jour s'ils existent déjà.
    #       Ici, pour éviter de reprocher "variable row" hors boucle, on reparcourt rows avec les infos utiles.
    #       Si tu veux optimiser, pré-collecte des sets {accnum->acclib} & {jnl}.
    seen_acc = {}
    seen_jnl = set()
    f = csv.DictReader(io.StringIO(text), dialect=dialect)  # relire pour avoir acclib exact sur chaque accnum
    for r in f:
        accnum = (r["accnum"] or "").strip()
        acclib = (r["acclib"] or "").strip() or accnum
        jnl = (r["jnl"] or "").strip()
        if accnum and accnum not in seen_acc:
            find_or_create_account(db, client_id, accnum, acclib)
            seen_acc[accnum] = True
        if jnl and jnl not in seen_jnl:
            find_or_create_journal(db, client_id, jnl, None)
            seen_jnl.add(jnl)

    # 6) insertion + historisation (transaction)
    try:
        for r in rows:
            db.add(Entry(**r))
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

    # 7) warnings non bloquants (exercice entier)
    warnings = {"unbalanced_pieces": list_unbalanced_pieces(db, exercice_id, limit=50)}

    return {"added": len(rows), "warnings": warnings}
