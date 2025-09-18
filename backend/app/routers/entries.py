import re
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import String, cast, func, literal, select, and_, or_
from datetime import date
from typing import Optional, Tuple
import base64, json, csv, io

from ..helpers import fmt_cents_fr
from ..database import get_db
from ..models import Entry, Account
from ..schemas import EntriesPage, EntryOut, PageInfo

router = APIRouter(prefix="/api/entries", tags=["entries"])

def _parse_date(s: str) -> date:
    return date.fromisoformat(s)

# ---- tokens opaques (after/before) ----
def _encode_token(payload: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode()

def _decode_token(token: str) -> dict:
    return json.loads(base64.urlsafe_b64decode(token.encode()).decode())

def _filters_signature(
    exercice_id: int,
    journal: Optional[str],
    piece_ref: Optional[str],
    compte: Optional[str],
    min_date: Optional[str],
    max_date: Optional[str],
    amount_like: Optional[str],
    search: Optional[str],
) -> dict:
    # Normaliser pour comparaison stricte
    return {
        "exercice_id": int(exercice_id),
        "journal": journal or None,
        "piece_ref": piece_ref or None,
        "compte": compte or None,
        "min_date": min_date or None,
        "max_date": max_date or None,
        "amount_like": amount_like or None,
        "search": (search or None),
    }

# ---- tri autorisé (clé primaire de tri + tiebreaker id ASC) ----
def _parse_sort(sort: Optional[str]) -> Tuple[str, bool]:
    # retourne (clé, desc)
    s = (sort or "date,id").split(",")[0].strip()
    if not s:
        s = "date"
    desc = s.startswith("-")
    key = s[1:] if desc else s
    allowed = {"date", "id", "jnl", "piece_ref", "accnum", "debit", "credit"}
    if key not in allowed:
        key = "date"
        desc = False
    return key, desc

def _primary_expr(key: str):
    if key == "date":
        return Entry.date
    if key == "id":
        return Entry.id
    if key == "jnl":
        return Entry.jnl
    if key == "piece_ref":
        return Entry.piece_ref
    if key == "accnum":
        return Account.accnum
    if key == "debit":
        return Entry.debit_minor
    if key == "credit":
        return Entry.credit_minor
    return Entry.date

def _cursor_predicate(primary_col, desc: bool, after_cursor: Optional[dict], before_cursor: Optional[dict]):
    # Construit le WHERE (> cursor) ou (< cursor) en respectant l'ordre
    # Tie-breaker: Entry.id ASC en ordre normal
    if after_cursor:
        pv = after_cursor["pv"]
        pid = after_cursor["id"]
        op_main = primary_col < pv if desc else primary_col > pv
        op_eq = and_(primary_col == pv, Entry.id > pid)
        return or_(op_main, op_eq)
    if before_cursor:
        pv = before_cursor["pv"]
        pid = before_cursor["id"]
        op_main = primary_col > pv if desc else primary_col < pv
        op_eq = and_(primary_col == pv, Entry.id < pid)
        return or_(op_main, op_eq)
    return None

def _sanitize_amount_like(s: str) -> str:
    # enlève uniquement les espaces (on garde la virgule)
    return (s or "").replace(" ", "")

def _formatted_delta_expr():
    """
    Retourne une expression SQL (SQLite-compatible) qui produit une chaîne
    'euros,cents' à partir de ABS(debit_minor - credit_minor) (en cents).
    Ex: 735600 -> '7356,00', 5 -> '0,05', 3550 -> '35,50'
    """
    delta = func.abs(Entry.debit_minor - Entry.credit_minor)

    # Assure au moins 2 digits pour pouvoir prendre les cents
    # printf('%02d', N) existe en SQLite
    digits2 = func.printf('%02d', delta)  # '05', '3550', '735600', etc.

    # euros = tout sauf les 2 derniers digits ; si vide -> '0'
    euros_raw = func.substr(digits2, 1, func.length(digits2) - 2)
    euros = func.coalesce(func.nullif(euros_raw, ''), literal('0'))

    # cents = 2 derniers digits
    cents = func.substr(digits2, -2, 2)

    # euros || ',' || cents
    return func.concat(euros, literal(','), cents)

def _apply_filters(q, exercice_id, journal, piece_ref, compte, min_date, max_date, amount_like, search, join_account: bool):
    q = q.where(Entry.exercice_id == exercice_id)
    if journal:
        q = q.where(Entry.jnl == journal)
    if piece_ref:
        q = q.where(Entry.piece_ref.ilike(f"%{piece_ref}%"))
    if min_date:
        q = q.where(Entry.date >= _parse_date(min_date))
    if max_date:
        q = q.where(Entry.date <= _parse_date(max_date))
    if amount_like:
        needle = _sanitize_amount_like(amount_like)  # retire juste les espaces
        if needle:  # garde virgule si présente
            formatted = _formatted_delta_expr()
            q = q.where(formatted.ilike(f"%{needle}%"))
    if search:
        like = f"%{search}%"
        q = q.where(Entry.lib.ilike(like))
    if compte:
        q = q.where(Account.accnum.ilike(f"%{compte}%"))
    return q

@router.get("", response_model=EntriesPage)
def list_entries_keyset(
    exercice_id: int = Query(...),
    journal: Optional[str] = None,
    compte: Optional[str] = None,   # accnum
    piece_ref: Optional[str] = None,
    min_date: Optional[str] = None,
    max_date: Optional[str] = None,
    amount_like: Optional[str] = None,
    search: Optional[str] = None,
    sort: Optional[str] = "date,id",
    page_size: int = Query(100, ge=1, le=500),
    after: Optional[str] = None,
    before: Optional[str] = None,
    db: Session = Depends(get_db),
):
    if after and before:
        raise HTTPException(400, "after et before sont exclusifs")

    key, desc = _parse_sort(sort)
    join_account = bool(compte) or key == "accnum"

    # base select avec JOIN (si besoin) et colonnes nécessaires
    # on sélectionne Entry + accnum/acclib pour éviter N+1
    q = select(
        Entry,
        Account.accnum.label("accnum"),
        Account.acclib.label("acclib"),
    )
    if join_account:
        q = q.join(Account, Account.id == Entry.account_id)
    else:
        # pour récupérer quand même accnum/acclib sans forcer le JOIN dans SQLite, on joint quand même (léger)
        q = q.join(Account, Account.id == Entry.account_id)

    q = _apply_filters(q, exercice_id, journal, piece_ref, compte, min_date, max_date, amount_like, search, join_account)

    primary_col = _primary_expr(key)

    # Vérifier/valider token si présent
    filt_sig = _filters_signature(exercice_id, journal, piece_ref, compte, min_date, max_date, amount_like, search)
    after_cursor = before_cursor = None
    if after:
        c = _decode_token(after)
        if c.get("filt") != filt_sig or c.get("key") != key or c.get("desc") != desc:
            raise HTTPException(400, "token invalide (filtres/tri ont changé)")
        after_cursor = c["cur"]
    if before:
        c = _decode_token(before)
        if c.get("filt") != filt_sig or c.get("key") != key or c.get("desc") != desc:
            raise HTTPException(400, "token invalide (filtres/tri ont changé)")
        before_cursor = c["cur"]

    cur_pred = _cursor_predicate(primary_col, desc, after_cursor, before_cursor)
    if cur_pred is not None:
        q = q.where(cur_pred)

    # Ordre d'affichage normal
    order_cols = [primary_col.desc() if desc else primary_col.asc(), Entry.id.asc()]
    # Si on navigue "before", on inverse pour prendre la page précédente puis on renversera
    reversed_fetch = bool(before_cursor)
    if reversed_fetch:
        order_cols = [primary_col.asc() if desc else primary_col.desc(), Entry.id.desc()]
    q = q.order_by(*order_cols).limit(page_size + 1)

    rows = db.execute(q).all()  # liste de tuples (Entry, accnum, acclib)

    # Déterminer s'il y a une page suivante/précédente
    has_extra = len(rows) > page_size
    if has_extra:
        rows = rows[:page_size]

    # Si on a fetch en reverse, on remet l'ordre normal
    if reversed_fetch:
        rows = list(reversed(rows))

    # Construire payloads
    out_rows = []
    for e, accnum, acclib in rows:
        out_rows.append(EntryOut(
            id=e.id,
            date=e.date,
            jnl=e.jnl,
            piece_ref=e.piece_ref,
            account_id=e.account_id,
            accnum=accnum or "",
            acclib=acclib or "",
            lib=e.lib,
            debit_minor=e.debit_minor,
            credit_minor=e.credit_minor,
        ))

    # next/prev tokens
    def _pv_from_row(e: Entry, accnum_val: Optional[str]):
        if key == "date": return e.date.isoformat()
        if key == "id": return e.id
        if key == "jnl": return e.jnl
        if key == "piece_ref": return e.piece_ref
        if key == "accnum": return accnum_val or ""
        if key == "debit": return e.debit_minor or 0
        if key == "credit": return e.credit_minor or 0
        return e.date.isoformat()

    next_token = prev_token = None
    if out_rows:
        first_e, first_accnum = rows[0][0], rows[0][1]
        last_e, last_accnum = rows[-1][0], rows[-1][1]
        cur_first = {"pv": _pv_from_row(first_e, first_accnum), "id": first_e.id}
        cur_last = {"pv": _pv_from_row(last_e, last_accnum), "id": last_e.id}
        base_payload = {"v": 1, "key": key, "desc": desc, "filt": filt_sig}
        prev_token = _encode_token({**base_payload, "cur": cur_first})
        next_token = _encode_token({**base_payload, "cur": cur_last})

    has_prev = bool(before or after) if out_rows else False
    if reversed_fetch:
        # on venait de 'before' => has_prev dépend du "has_extra"
        has_prev = has_extra
    has_next = has_extra if not reversed_fetch else True  # en backward, il existe toujours une "page suivante" vers l'avant

    page_info = PageInfo(next=next_token, prev=prev_token, has_next=bool(has_next), has_prev=bool(has_prev))
    return {"rows": out_rows, "page_info": page_info}


# -------- SUGGEST piece_ref --------
@router.get("/suggest-piece")
def suggest_piece(
    exercice_id: int = Query(...),
    q: str = "",
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    q = (q or "").strip()
    stmt = select(Entry.piece_ref).where(Entry.exercice_id == exercice_id)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(Entry.piece_ref.ilike(like))
    stmt = stmt.group_by(Entry.piece_ref).order_by(Entry.piece_ref).limit(limit)
    items = [r[0] for r in db.execute(stmt).all() if r[0]]
    return {"items": items}


# -------- EXPORT CSV --------
@router.get("/export")
def export_entries_csv(
    exercice_id: int = Query(...),
    journal: Optional[str] = None,
    compte: Optional[str] = None,
    piece_ref: Optional[str] = None,
    min_date: Optional[str] = None,
    max_date: Optional[str] = None,
    amount_like: Optional[str] = None,
    search: Optional[str] = None,
    sort: Optional[str] = "date,id",
    db: Session = Depends(get_db),
):
    key, desc = _parse_sort(sort)
    # On joint Account pour accnum/acclib
    q = select(
        Entry.id,
        Entry.exercice_id,
        Entry.date,
        Entry.jnl,
        Entry.piece_ref,
        Entry.account_id,
        Account.accnum.label("accnum"),
        Account.acclib.label("acclib"),
        Entry.lib,
        Entry.debit_minor,
        Entry.credit_minor,
        Entry.piece_date,
        Entry.valid_date,
        Entry.montant_minor,
        Entry.i_devise,
    ).join(Account, Account.id == Entry.account_id)

    q = _apply_filters(q, exercice_id, journal, piece_ref, compte, min_date, max_date, amount_like, search, True)

    primary_col = _primary_expr(key)
    order_cols = [primary_col.desc() if desc else primary_col.asc(), Entry.id.asc()]
    q = q.order_by(*order_cols)

    rows = db.execute(q).all()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    writer.writerow([
        "id","exercice_id","date","jnl","piece_ref","account_id","accnum","acclib","lib",
        "debit","credit","piece_date","valid_date","montant","i_devise"
    ])
    for r in rows:
        (
            _id, _exo, _date, _jnl, _piece, _acc_id, _accnum, _acclib, _lib,
            _debit_minor, _credit_minor, _pdate, _vdate, _montant_minor, _idev
        ) = r
        writer.writerow([
            _id, _exo, (_date.isoformat() if _date else ""),
            _jnl or "", _piece or "", _acc_id, _accnum or "", _acclib or "", (_lib or "").replace("\n", " "),
            fmt_cents_fr(_debit_minor or 0), fmt_cents_fr(_credit_minor or 0),
            (_pdate.isoformat() if _pdate else ""), (_vdate.isoformat() if _vdate else ""),
            (fmt_cents_fr(_montant_minor) if _montant_minor is not None else ""),
            _idev or "",
        ])

    content = output.getvalue()
    headers = {
        "Content-Type": "text/csv; charset=utf-8",
        "Content-Disposition": f'attachment; filename="entries_{exercice_id}.csv"',
    }
    return Response(content=content, media_type="text/csv", headers=headers)
