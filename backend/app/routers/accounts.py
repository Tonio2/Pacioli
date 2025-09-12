from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, select

from ..schemas import AccountOut
from ..database import get_db
from ..models import Account, Entry

router = APIRouter(prefix="/api/accounts", tags=["accounts"])

@router.get("", response_model=list[AccountOut])
def list_accounts(client_id: int, db: Session = Depends(get_db)):
    rows = db.execute(select(Account).where(Account.client_id==client_id).order_by(Account.accnum)).scalars().all()
    return rows

@router.post("", response_model=AccountOut)
def create_account(client_id: int, accnum: str, acclib: str, db: Session = Depends(get_db)):
    if db.execute(select(Account).where(Account.client_id==client_id, Account.accnum==accnum)).scalar_one_or_none():
        raise HTTPException(400, "Compte déjà existant")
    a = Account(client_id=client_id, accnum=accnum, acclib=acclib)
    db.add(a); db.commit(); db.refresh(a)
    return a

@router.patch("/{id}", response_model=AccountOut)
def update_account(id: int, acclib: str, db: Session = Depends(get_db)):
    a = db.get(Account, id)
    if not a:
        raise HTTPException(404)
    a.acclib = acclib
    db.commit()
    return a

@router.delete("/{id}")
def delete_account(id: int, db: Session = Depends(get_db)):
    a = db.get(Account, id)
    if not a:
        raise HTTPException(404)
    cnt = db.scalar(select(func.count()).where(Entry.account_id == id)) or 0
    if cnt:
        raise HTTPException(400, "Impossible de supprimer: des écritures existent sur ce compte")
    db.delete(a); db.commit()
    return {"ok": True}


@router.get("/lookup")
def lookup_account(client_id: int, accnum: str, db: Session = Depends(get_db)):
    accnum = (accnum or "").strip()
    if not accnum:
        return {"exists": False}
    acc = db.execute(
        select(Account).where(Account.client_id == client_id, Account.accnum == accnum)
    ).scalar_one_or_none()
    if acc:
        return {"exists": True, "account_id": acc.id, "acclib": acc.acclib}
    return {"exists": False}

@router.get("/suggest")
def suggest_accounts(client_id: int, q: str = "", limit: int = 10, db: Session = Depends(get_db)):
    q = (q or "").strip()
    stmt = select(Account).where(Account.client_id == client_id)
    if q:
        like = f"%{q}%"
        stmt = stmt.where((Account.accnum.ilike(like)) | (Account.acclib.ilike(like)))
    stmt = stmt.limit(min(limit, 50))
    items = db.execute(stmt).scalars().all()
    return {
        "items": [
            {"account_id": a.id, "accnum": a.accnum, "acclib": a.acclib}
            for a in items
        ]
    }
