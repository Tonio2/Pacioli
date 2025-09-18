from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from sqlalchemy.orm import Session
from sqlalchemy import select
from decimal import ROUND_HALF_UP, Decimal
from datetime import datetime
import csv, io, re
from ..database import get_db
from ..models import Entry, HistoryEvent, Account
from ..validators import ensure_batch_balanced, ensure_dates_in_exercice, ValidationError
from ..crud import find_or_create_account, find_or_create_journal, get_next_ref, list_unbalanced_pieces, get_exercice

router = APIRouter(prefix="/api/imports", tags=["imports"])

_amount_clean_re = re.compile(r"[\s\u00A0]\s*")

def to_minor(d: Decimal | int | str | float) -> int:
    d = Decimal(str(d)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return int((d * 100).to_integral_value())

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
    exercice_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    # 1) Exercice
    try:
        ex = get_exercice(db, exercice_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    client_id = ex.client_id

    # 2) Lecture fichier
    raw = await file.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    if not text.strip():
        raise HTTPException(400, "Fichier vide")

    # 3) Détection dialecte (échantillon un peu plus large que 1 ligne)
    sample = "\n".join(text.splitlines()[:10])
    try:
        dialect = csv.Sniffer().sniff(sample)
    except Exception:
        dialect = csv.excel
        dialect.delimiter = "\t"  # par défaut FR

    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    reader.fieldnames = [(h or "").strip() for h in (reader.fieldnames or [])]

    required = {
        "jnl", "accnum", "acclib", "date", "lib", "pieceRef",
        "debit", "credit", "pieceDate", "validDate", "montant", "iDevise"
    }
    missing = required - set(reader.fieldnames or [])
    if missing:
        raise HTTPException(400, f"Colonnes manquantes: {', '.join(sorted(missing))}")

    def cell(row, key):
        return (row.get(key) or "").strip()

    # 4) Un seul passage : parse + normalisation + collecte vues
    rows: list[dict] = []
    delta_rows: list[dict] = []
    seen_acc: dict[str, bool] = {}
    seen_jnl: set[str] = set()

    for i, row in enumerate(reader, start=2):
        try:
            jnl = cell(row, "jnl")
            accnum = cell(row, "accnum")
            acclib = cell(row, "acclib") or accnum

            date_obj = parse_date(cell(row, "date"))
            # logique hors-exercice: tu marquais JNL="DATE" et remplaçais la date
            if not (ex.date_start <= date_obj <= ex.date_end):
                date_obj = parse_date("1/1/2022")  # garde ta logique existante
                jnl = "DATE"

            lib = cell(row, "lib")
            piece_ref = cell(row, "pieceRef")

            debit = parse_amount(cell(row, "debit") or "0")
            credit = parse_amount(cell(row, "credit") or "0")

            piece_date_raw = cell(row, "pieceDate")
            valid_date_raw = cell(row, "validDate")
            piece_date = parse_date(piece_date_raw) if piece_date_raw else date_obj
            valid_date = parse_date(valid_date_raw) if valid_date_raw else date_obj
            if jnl == "AN":
                piece_date = ex.date_start
                valid_date = ex.date_start

            montant_raw = cell(row, "montant")
            montant = parse_amount(montant_raw) if montant_raw else None

            i_devise = cell(row, "iDevise") or None
        except Exception as e:
            raise HTTPException(400, f"Erreur parsing ligne {i}: {e}")

        if debit < 0 or credit < 0:
            raise HTTPException(400, f"Ligne {i}: montants négatifs interdits")

        if (debit != 0 and credit != 0) or (debit == 0 and credit == 0):
            raise HTTPException(400, f"Ligne {i}: chaque ligne doit avoir soit un débit soit un crédit (exclusif)")

        # Génération de réf pièce si manquante (avec le JNL normalisé!)
        if piece_ref == "":
            piece_ref = get_next_ref(db, exercice_id, jnl).get("next_ref", "NC")

        # Collecte vues (basée sur les valeurs normalisées !)
        if accnum:
            seen_acc.setdefault(accnum, True)
        if jnl:
            seen_jnl.add(jnl)

        # Stocke la ligne normalisée
        norm = {
            "exercice_id": exercice_id,
            "date": date_obj,
            "jnl": jnl,
            "piece_ref": piece_ref,
            "accnum": accnum,      # pour résolution account_id ensuite
            "acclib": acclib,      # pour création si besoin
            "lib": lib,
            "debit": debit,
            "credit": credit,
            "piece_date": piece_date,
            "valid_date": valid_date,
            "montant": montant,
            "i_devise": i_devise,
        }
        rows.append(norm)
        delta_rows.append({"date": date_obj, "debit": debit, "credit": credit})

    # 5) Validations (sur les données normalisées)
    try:
        ensure_dates_in_exercice(rows, ex.date_start, ex.date_end)
        ensure_batch_balanced(delta_rows)
    except ValidationError as ve:
        raise HTTPException(400, str(ve))

    # 6) Pré-création/synchro à partir des ensembles vus NORMALISÉS (plus de 2e lecture)
    try:
        # Comptes
        for accnum in seen_acc.keys():
            # find_or_create ne modifie pas un compte existant
            find_or_create_account(db, client_id, accnum, accnum)
        # Journaux
        for j in seen_jnl:
            find_or_create_journal(db, client_id, j, None)
        db.flush()  # assure les IDs générés si nécessaire avant insert
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Erreur lors de la pré-création comptes/journaux: {e}")

    # 7) Insertion des écritures (depuis EXACTEMENT rows)
    try:
        for r in rows:
            acc = db.execute(
                select(Account).where(
                    Account.client_id == client_id,
                    Account.accnum == r["accnum"]
                )
            ).scalar_one_or_none()
            if acc is None:
                acc = find_or_create_account(db, client_id, r["accnum"], r["acclib"] or r["accnum"])

            db.add(Entry(
                exercice_id=exercice_id,
                date=r["date"],
                jnl=r["jnl"],
                piece_ref=r["piece_ref"],
                account_id=acc.id,
                lib=r["lib"],
                debit_minor=to_minor(r["debit"]),
                credit_minor=to_minor(r["credit"]),
                piece_date=r["piece_date"],
                valid_date=r["valid_date"],
                montant_minor=to_minor(r["montant"]) if r["montant"] is not None else None,
                i_devise=r["i_devise"],
            ))

        he = HistoryEvent(
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
