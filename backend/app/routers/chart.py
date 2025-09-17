from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import select
from ..database import get_db
from ..models import Account, Journal
from ..schemas import AccountOut, JournalOut
import json

router = APIRouter(prefix="/api/chart", tags=["chart"])

@router.get("/accounts", response_model=list[AccountOut])
def list_accounts(client_id: int = Query(...), db: Session = Depends(get_db)):
    q = select(Account).where(Account.client_id == client_id).order_by(Account.accnum)
    return db.execute(q).scalars().all()

@router.patch("/accounts/{id}", response_model=AccountOut)
def update_account(id: int, acclib: str = Query(...), db: Session = Depends(get_db)):
    acc = db.get(Account, id)
    if not acc:
        raise HTTPException(404)
    acc.acclib = acclib
    db.commit()
    db.refresh(acc)
    return acc

@router.get("/journals", response_model=list[JournalOut])
def list_journals(client_id: int = Query(...), db: Session = Depends(get_db)):
    q = select(Journal).where(Journal.client_id == client_id).order_by(Journal.jnl)
    return db.execute(q).scalars().all()

@router.patch("/journals/{id}", response_model=JournalOut)
def update_journal(id: int, jnl_lib: str = Query(...), db: Session = Depends(get_db)):
    jnl = db.get(Journal, id)
    if not jnl:
        raise HTTPException(404)
    jnl.jnl_lib = jnl_lib
    db.commit()
    db.refresh(jnl)
    return jnl

@router.get("/export/accounts")
def export_accounts(client_id: int = Query(...), db: Session = Depends(get_db)):
    q = select(Account).where(Account.client_id == client_id).order_by(Account.accnum.asc())
    rows = db.execute(q).scalars().all()
    data = {r.accnum: r.acclib for r in rows}
    content = json.dumps(data, ensure_ascii=False, indent=2)
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Content-Disposition": 'attachment; filename="accounts.json"',
    }
    return Response(content=content, media_type="application/json", headers=headers)

@router.get("/export/journals")
def export_journals(client_id: int = Query(...), db: Session = Depends(get_db)):
    q = select(Journal).where(Journal.client_id == client_id)
    rows = db.execute(q).scalars().all()
    data = {r.jnl: r.jnl_lib for r in rows}
    content = json.dumps(data, ensure_ascii=False, indent=2)
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Content-Disposition": 'attachment; filename="journals.json"',
    }
    return Response(content=content, media_type="application/json", headers=headers)
