from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..schemas import JournalOut
from ..database import get_db
from ..models import Journal

router = APIRouter(prefix="/api/journals", tags=["journals"])

@router.get("", response_model=list[JournalOut])
def list_journals(client_id: int, db: Session = Depends(get_db)):
    rows = db.execute(select(Journal).where(Journal.client_id==client_id).order_by(Journal.jnl)).scalars().all()
    return rows

@router.post("", response_model=JournalOut)
def create_journal(client_id: int, jnl: str, jnl_lib: str, db: Session = Depends(get_db)):
    if db.execute(select(Journal).where(Journal.client_id==client_id, Journal.jnl==jnl)).scalar_one_or_none():
        raise HTTPException(400, "Journal déjà existant")
    j = Journal(client_id=client_id, jnl=jnl, jnl_lib=jnl_lib)
    db.add(j); db.commit(); db.refresh(j)
    return j

@router.patch("/{id}", response_model=JournalOut)
def update_journal(id: int, jnl_lib: str, db: Session = Depends(get_db)):
    j = db.get(Journal, id)
    if not j:
        raise HTTPException(404)
    j.jnl_lib = jnl_lib
    db.commit()
    return j

@router.delete("/{id}")
def delete_journal(id: int, db: Session = Depends(get_db)):
    j = db.get(Journal, id)
    if not j:
        raise HTTPException(404)
    db.delete(j); db.commit()
    return {"ok": True}
