from sqlalchemy.orm import Session
from sqlalchemy import func, select
from .models import Entry, Account, Journal, Exercice

# Helpers

def find_or_create_account(db: Session, client_id: int, accnum: str, acclib: str | None):
    acc = db.execute(
        select(Account).where(Account.client_id==client_id, Account.accnum==accnum)
    ).scalar_one_or_none()
    if acc:
        return acc
    acc = Account(client_id=client_id, accnum=accnum, acclib=acclib or accnum)
    db.add(acc)
    db.flush()
    return acc


def find_or_create_journal(db: Session, client_id: int, jnl: str, jnl_lib: str | None):
    j = db.execute(select(Journal).where(Journal.client_id==client_id, Journal.jnl==jnl)).scalar_one_or_none()
    if j:
        return j
    j = Journal(client_id=client_id, jnl=jnl, jnl_lib=jnl_lib or jnl)
    db.add(j)
    db.flush()
    return j


def list_unbalanced_pieces(db: Session, exercice_id: int, limit: int = 100):
    q = (
        select(Entry.jnl, Entry.piece_ref,
               func.sum(Entry.debit_minor).label("td"),
               func.sum(Entry.credit_minor).label("tc"))
        .where(Entry.exercice_id == exercice_id)
        .group_by(Entry.jnl, Entry.piece_ref)
        .having(func.abs(func.sum(Entry.debit_minor - Entry.credit_minor)) != 0)
        .order_by(func.abs(func.sum(Entry.debit_minor - Entry.credit_minor)).desc())
        .limit(limit)
    )
    return [
        {"jnl": r.jnl, "piece_ref": r.piece_ref, "total_debit_minor": r.td or 0, "total_credit_minor": r.tc or 0}
        for r in db.execute(q)
    ]


def get_exercice(db: Session, exercice_id: int) -> Exercice:
    ex = db.get(Exercice, exercice_id)
    if not ex:
        raise ValueError("Exercice introuvable")
    return ex
