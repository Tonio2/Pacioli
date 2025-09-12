from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from ..database import get_db
from ..models import Account

router = APIRouter(prefix="/api/accounts", tags=["accounts"])

@router.get("")
def list_accounts(client_id: int, db: Session = Depends(get_db)):
    rows = db.execute(select(Account).where(Account.client_id==client_id).order_by(Account.accnum)).scalars().all()
    return [{"id": a.id, "accnum": a.accnum, "acclib": a.acclib} for a in rows]

@router.post("")
def create_account(client_id: int, accnum: str, acclib: str, db: Session = Depends(get_db)):
    if db.execute(select(Account).where(Account.client_id==client_id, Account.accnum==accnum)).scalar_one_or_none():
        raise HTTPException(400, "Compte déjà existant")
    a = Account(client_id=client_id, accnum=accnum, acclib=acclib)
    db.add(a); db.commit(); db.refresh(a)
    return {"id": a.id, "accnum": a.accnum, "acclib": a.acclib}

@router.patch("/{id}")
def update_account(id: int, acclib: str, db: Session = Depends(get_db)):
    a = db.get(Account, id)
    if not a:
        raise HTTPException(404)
    a.acclib = acclib
    db.commit()
    return {"id": a.id, "accnum": a.accnum, "acclib": a.acclib}

@router.delete("/{id}")
def delete_account(id: int, db: Session = Depends(get_db)):
    a = db.get(Account, id)
    if not a:
        raise HTTPException(404)
    db.delete(a); db.commit()
    return {"ok": True}
