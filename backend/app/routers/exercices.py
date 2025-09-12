from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select
from ..database import get_db
from ..models import Exercice
from ..schemas import ExerciceCreate, ExerciceOut

router = APIRouter(prefix="/api/exercices", tags=["exercices"])

@router.get("", response_model=list[ExerciceOut])
def list_exercices(client_id: int = Query(...), db: Session = Depends(get_db)):
    return db.execute(
        select(Exercice)
        .where(Exercice.client_id == client_id)
        .order_by(Exercice.date_start.desc())
    ).scalars().all()

@router.post("", response_model=ExerciceOut)
def create_exercice(payload: ExerciceCreate, db: Session = Depends(get_db)):
    e = Exercice(**payload.model_dump())
    db.add(e); db.commit(); db.refresh(e)
    return e

@router.patch("/{id}", response_model=ExerciceOut)
def update_exercice(id: int, payload: ExerciceCreate, db: Session = Depends(get_db)):
    e = db.get(Exercice, id)
    if not e:
        raise HTTPException(404)
    for k, v in payload.model_dump().items():
        setattr(e, k, v)
    db.commit(); db.refresh(e)
    return e

@router.delete("/{id}")
def delete_exercice(id: int, db: Session = Depends(get_db)):
    e = db.get(Exercice, id)
    if not e:
        raise HTTPException(404)
    db.delete(e); db.commit()
    return {"ok": True}
