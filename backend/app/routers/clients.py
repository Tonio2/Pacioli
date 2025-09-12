from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from ..database import get_db
from ..models import Client
from ..schemas import ClientCreate, ClientOut

router = APIRouter(prefix="/api/clients", tags=["clients"])

@router.get("", response_model=list[ClientOut])
def list_clients(db: Session = Depends(get_db)):
    return db.execute(select(Client).order_by(Client.name)).scalars().all()

@router.post("", response_model=ClientOut)
def create_client(payload: ClientCreate, db: Session = Depends(get_db)):
    exists = db.execute(select(Client).where(Client.name == payload.name)).scalar_one_or_none()
    if exists:
        raise HTTPException(400, "Client déjà existant")
    c = Client(name=payload.name)
    db.add(c); db.commit(); db.refresh(c)
    return c

@router.patch("/{id}", response_model=ClientOut)
def update_client(id: int, payload: ClientCreate, db: Session = Depends(get_db)):
    c = db.get(Client, id)
    if not c:
        raise HTTPException(404)
    c.name = payload.name
    db.commit(); db.refresh(c)
    return c

@router.delete("/{id}")
def delete_client(id: int, db: Session = Depends(get_db)):
    c = db.get(Client, id)
    if not c:
        raise HTTPException(404)
    db.delete(c); db.commit()
    return {"ok": True}
