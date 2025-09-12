from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..crud import list_unbalanced_pieces

router = APIRouter(prefix="/api/checks", tags=["checks"])

@router.get("/exercice")
def checks_exercice(client_id: int = Query(...), exercice_id: int = Query(...), limit: int = 100, db: Session = Depends(get_db)):
    return {"unbalanced_pieces": list_unbalanced_pieces(db, exercice_id, limit=limit)}
