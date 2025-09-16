# routers/fec.py
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import date
import io, zipfile, re
from collections import defaultdict

from ..helpers import fmt_cents_fec
from ..database import get_db
from ..models import Entry, Account, Journal, Exercice
from ..crud import get_exercice

router = APIRouter(prefix="/api", tags=["fec"])

NBSP = "\u00A0"
PIPE = "|"
LINESEP = "\n"

FEC_FIELDS = [
    "JournalCode","JournalLib","EcritureNum","EcritureDate",
    "CompteNum","CompteLib","CompAuxNum","CompAuxLib",
    "PieceRef","PieceDate","EcritureLib","Debit","Credit",
    "EcritureLet","DateLet","ValidDate","Montantdevise","Idevise"
]

# -------- utils format --------
def _yyyymmdd(d: date | None) -> str:
    return "" if d is None else d.strftime("%Y%m%d")



def _sanitize_text(v: str | None) -> str:
    if v is None:
        return ""
    # retirer insécables, pipes, retours…
    return (
        str(v)
        .replace(NBSP, " ")
        .replace("|", " ")
        .replace("\r", " ")
        .replace("\n", " ")
        .strip()
    )

def _is_eur(dev: str | None) -> bool:
    if not dev:
        return True
    u = dev.strip().upper()
    return u in ("EUR", "EURO", "")

_accnum_ok = re.compile(r"^\d{3}")

# --------- builder principal ----------
def _build_fec_zip(db: Session, exercice_id: int) -> bytes:
    ex: Exercice = get_exercice(db, exercice_id)
    client_id = ex.client_id

    # Récupération des écritures avec joins
    # Note: Entry -> Account (FK), Journal via (client_id, jnl)
    j_sub = select(Journal.jnl, Journal.jnl_lib).where(Journal.client_id==client_id).subquery()

    q = (
        select(
            Entry.id,
            Entry.date,
            Entry.jnl,
            Entry.piece_ref,
            Entry.account_id,
            Entry.lib,
            Entry.debit_minor,
            Entry.credit_minor,
            Entry.piece_date,
            Entry.valid_date,
            Entry.montant_minor,
            Entry.i_devise,
            Account.accnum,
            Account.acclib,
            j_sub.c.jnl_lib
        )
        .join(Account, Account.id==Entry.account_id)
        .join(j_sub, j_sub.c.jnl==Entry.jnl, isouter=True)
        .where(Entry.exercice_id == exercice_id)
        .order_by(Entry.id.asc())
    )

    rows = db.execute(q).all()
    if not rows:
        raise HTTPException(404, "Aucune écriture pour cet exercice")

    # --- Contrôles équilibre ---
    sum_ex_debit_minor = 0
    sum_ex_credit_minor = 0
    sum_by_piece = defaultdict(lambda: {"debit_minor": 0, "credit_minor": 0, "count": 0})

    for r in rows:
        debit_minor = r.debit_minor or 0
        credit_minor = r.credit_minor or 0
        sum_ex_debit_minor += debit_minor
        sum_ex_credit_minor += credit_minor
        key = (r.jnl, (r.piece_ref or "").strip())
        sum_by_piece[key]["debit_minor"] += debit_minor
        sum_by_piece[key]["credit_minor"] += credit_minor
        sum_by_piece[key]["count"] += 1

    unbalanced_pieces = []
    for (jnl, piece_ref), agg in sum_by_piece.items():
        if agg["debit_minor"] != agg["credit_minor"]:
            diff_minor = (agg["debit_minor"] - agg["credit_minor"])
            unbalanced_pieces.append((jnl, piece_ref, agg["count"], agg["debit_minor"], agg["credit_minor"], diff_minor))

    exercise_balanced = (sum_ex_debit_minor == sum_ex_credit_minor)

    # Préparation des enregistrements normalisés et warnings
    records = []
    warnings: list[str] = []

    if not exercise_balanced:
        warnings.append(
            f"Déséquilibre exercice: total débit={fmt_cents_fec(sum_ex_debit_minor)}, total crédit={fmt_cents_fec(sum_ex_credit_minor)}, "
            f"diff={fmt_cents_fec(sum_ex_debit_minor - sum_ex_credit_minor)}"
        )

    # Limiter l’énumération pour garder un rapport lisible (ex: 200 premières pièces déséquilibrées)
    MAX_LIST = 200
    if unbalanced_pieces:
        warnings.append(f"{len(unbalanced_pieces)} pièce(s) déséquilibrée(s) (débit≠crédit).")
        for i, (jnl, pref, cnt, d, c, diff) in enumerate(unbalanced_pieces[:MAX_LIST], start=1):
            warnings.append(f"  - {jnl}/{pref} (lignes={cnt}) : débit={fmt_cents_fec(d)} crédit={fmt_cents_fec(c)} diff={fmt_cents_fec(diff)}")
        if len(unbalanced_pieces) > MAX_LIST:
            warnings.append(f"  ... ({len(unbalanced_pieces)-MAX_LIST} autres non listées)")


    # Pré-calcul: date ouverture/clôture
    d_open = ex.date_start
    d_close = ex.date_end

    # 1) Normalisation ligne par ligne (sans EcritureNum pour l'instant)
    for r in rows:
        (
            _id, d_ecr, jnl, piece_ref, account_id, lib, debit_minor, credit_minor,
            piece_date, valid_date, montant_minor, idevise, accnum, acclib, jnl_lib
        ) = r

        # Règles AN / OD
        if jnl == "AN":
            d_ecr_use = d_open
            piece_date_use = d_open
            valid_date_use = d_open if valid_date is None else d_open  # règle demandée: on force ouverture
        else:
            d_ecr_use = d_ecr or d_close  # sécurité (ne devrait pas être None)
            if jnl == "OD":
                piece_date_use = piece_date or d_close
            else:
                piece_date_use = piece_date or d_ecr_use
            valid_date_use = valid_date  # peut être hors exercice (N+1)

        # Devise
        if _is_eur(idevise):
            montantdevise_txt = ""
            idevise_txt = ""
        else:
            idev = str(idevise).strip().upper()
            idevise_txt = idev
            if montant_minor is None:
                warnings.append(f"i_devise={idev} mais montant devise manquant pour pièce {jnl}/{piece_ref}")
                montantdevise_txt = ""
                idevise_txt = ""
            else:
                montantdevise_txt = fmt_cents_fec(montant_minor)

        # Sanitization / défauts
        journal_code = _sanitize_text(jnl)
        journal_lib  = _sanitize_text(jnl_lib or jnl)
        compte_num   = _sanitize_text(accnum or "")
        compte_lib   = _sanitize_text(acclib or "")
        comp_aux_num = ""
        comp_aux_lib = ""
        piece_ref_s  = _sanitize_text(piece_ref or "NC")
        ecr_lib      = _sanitize_text(lib or "NC")

        # Contrôles doux (warnings)
        if not _accnum_ok.match(compte_num):
            warnings.append(f"CompteNum non conforme (>=3 chiffres) pour pièce {jnl}/{piece_ref_s}: {compte_num}")
        if PIPE in ecr_lib:
            warnings.append(f"'|' détecté dans EcritureLib pour {jnl}/{piece_ref_s}")
        if piece_ref_s == "NC":
            warnings.append(f"PieceRef absente pour {jnl}; {compte_num}; {compte_lib}; {ecr_lib}; {fmt_cents_fec(debit_minor)}; {fmt_cents_fec(credit_minor)}")

        # Build enregistrement (sans EcritureNum)
        rec = {
            "JournalCode": journal_code,
            "JournalLib": journal_lib,
            # "EcritureNum":  plus tard
            "EcritureDate": _yyyymmdd(d_ecr_use),
            "CompteNum": compte_num,
            "CompteLib": compte_lib,
            "CompAuxNum": comp_aux_num,
            "CompAuxLib": comp_aux_lib,
            "PieceRef": piece_ref_s,
            "PieceDate": _yyyymmdd(piece_date_use),
            "EcritureLib": ecr_lib,
            "Debit": fmt_cents_fec(debit_minor),
            "Credit": fmt_cents_fec(credit_minor),
            "EcritureLet": "",
            "DateLet": "",
            "ValidDate": _yyyymmdd(valid_date_use),
            "Montantdevise": montantdevise_txt,
            "Idevise": idevise_txt,
            # auxiliaires pour tri/numérotation
            "_grp_key": (journal_code, piece_ref_s),
            "_valid_for_sort": _yyyymmdd(valid_date_use) or _yyyymmdd(d_ecr_use),
        }
        records.append(rec)

    if not records:
        raise HTTPException(404, "Aucun enregistrement exploitable")

    # 2) Numérotation globale 1..N par pièce (groupe (Jnl, PieceRef))
    # Ordre pour affecter le numéro: ValidDate (ou EcritureDate si absente), puis PieceRef, puis Journal
    # => un numéro par pièce, répliqué sur ses lignes
    min_valid_per_piece = defaultdict(lambda: "99999999")
    for rec in records:
        key = rec["_grp_key"]
        mv = rec["_valid_for_sort"] or "99999999"
        if mv < min_valid_per_piece[key]:
            min_valid_per_piece[key] = mv

    # liste unique des pièces ordonnée
    pieces_sorted = sorted(min_valid_per_piece.items(), key=lambda kv: (kv[1], kv[0][1], kv[0][0]))
    ecrnum_by_piece = {piece_key: i+1 for i, (piece_key, _) in enumerate(pieces_sorted)}

    for rec in records:
        rec["EcritureNum"] = str(ecrnum_by_piece[rec["_grp_key"]])

    # 3) Tri final (lisible / stable)
    records.sort(key=lambda r: (int(r["EcritureNum"]), r["JournalCode"], r["CompteNum"]))

    # 4) Génération du fichier FEC en mémoire
    fec_name = f"SIRENFEC{ex.date_end.strftime('%Y%m%d')}"
    fec_io = io.StringIO()
    fec_io.write(PIPE.join(FEC_FIELDS) + LINESEP)
    for rec in records:
        line = PIPE.join(rec[f] for f in FEC_FIELDS) + LINESEP
        fec_io.write(line)
    fec_data = fec_io.getvalue().encode("utf-8")

    # 5) Génération du fichier description
    desc_io = io.StringIO()
    desc_io.write("DESCRIPTION FEC\n")
    desc_io.write(f"Client: {ex.client.name if hasattr(ex, 'client') and ex.client else ''}\n")
    desc_io.write(f"Exercice: {ex.date_start} -> {ex.date_end}\n")
    desc_io.write("Format: fichier à plat, séparateur '|', encodage UTF-8\n")
    desc_io.write("Tri: numérotation globale 1..N par pièce, ordre d’affectation par ValidDate puis PieceRef puis Journal\n")
    desc_io.write("Champs:\n")
    for i, fld in enumerate(FEC_FIELDS, start=1):
        desc_io.write(f"  {i:02d}. {fld}\n")
    desc_io.write("\nRappels de conformité:\n")
    desc_io.write("- EcritureDate dans l’exercice ; PieceDate/ValidDate peuvent être hors exercice.\n")
    desc_io.write("- Montantdevise/Idevise uniquement si devise ≠ EUR, sinon à blanc.\n")
    desc_io.write("- CompteNum: au moins 3 premiers caractères numériques (PCG).\n")
    desc_io.write("- Sanitization: pas de '|' ni retours chariot dans les champs texte.\n")
    desc_io.write("\nAvertissements:\n")
    if warnings:
        for w in warnings:
            desc_io.write(f"- {w}\n")
    else:
        desc_io.write("- Aucun avertissement.\n")
    desc_data = desc_io.getvalue().encode("utf-8")

    # 6) ZIP
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{fec_name}", fec_data)
        zf.writestr(f"{fec_name}_description.txt", desc_data)
    return zbuf.getvalue()

@router.get("/exercices/{exercice_id}/fec", summary="Export FEC (ZIP: FEC + description)")
def export_fec(exercice_id: int, db: Session = Depends(get_db)):
    try:
        data = _build_fec_zip(db, exercice_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Erreur export FEC: {e}")
    ex = get_exercice(db, exercice_id)
    filename = f"SIRENFEC{ex.date_end.strftime('%Y%m%d')}.zip"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"'
    }
    return Response(content=data, media_type="application/zip", headers=headers)
