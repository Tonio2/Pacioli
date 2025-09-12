from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Literal
import json
from ..database import get_db
from ..models import HistoryEvent

router = APIRouter(prefix="/api/history", tags=["history"])

def _parse_counts(s: str | None) -> dict:
    if not s:
        return {}
    try:
        return json.loads(s)
    except Exception:
        return {}

def _counts_human(d: dict) -> str:
    if not d:
        return "—"
    parts = []
    nature = ["Ajoutée", "Modifiée", "Supprimée"]
    for k in ("added", "modified", "deleted"):
        parts.append(d[k] if k in d else 0)
    ret = ""
    for i in range(3):
        ret += f"{nature[i]}{'s' if parts[i] > 1 else ''}: {parts[i]} | " if parts[i] else ""
    return ret[:-2] if len(ret) > 2 else ""

@router.get("")
def list_history(
    exercice_id: int = Query(...),
    order: Literal["asc", "desc"] = "asc",
    db: Session = Depends(get_db),
):
    q = select(HistoryEvent).where(
        HistoryEvent.exercice_id == exercice_id
    )
    q = q.order_by(HistoryEvent.created_at.asc() if order == "asc" else HistoryEvent.created_at.desc())
    rows = db.execute(q).scalars().all()
    out = []
    for r in rows:
        counts = _parse_counts(r.counts_json)
        out.append({
            "id": r.id,
            "created_at": r.created_at.strftime("%d/%m/%Y %H:%M"),
            "description": r.description or "",
            "counts": counts,
            "counts_human": _counts_human(counts),
        })
    return {"rows": out, "total": len(out)}

@router.patch("/{id}")
def update_history_description(id: int, description: str, db: Session = Depends(get_db)):
    he = db.get(HistoryEvent, id)
    if not he:
        raise HTTPException(404)
    he.description = description or ""
    db.commit()
    db.refresh(he)
    counts = _parse_counts(he.counts_json)
    return {
        "id": he.id,
        "created_at": he.created_at.strftime("%d/%m/%Y %H:%M"),
        "description": he.description or "",
        "counts": counts,
        "counts_human": _counts_human(counts),
    }

@router.get("/export")
def export_history_txt(
    exercice_id: int = Query(...),
    order: Literal["asc", "desc"] = "asc",
    db: Session = Depends(get_db),
):
    q = select(HistoryEvent).where(
        HistoryEvent.exercice_id == exercice_id
    )
    q = q.order_by(HistoryEvent.created_at.asc() if order == "asc" else HistoryEvent.created_at.desc())
    rows = db.execute(q).scalars().all()

    lines: list[str] = []
    for r in rows:
        counts = _parse_counts(r.counts_json)
        lines.append(f"- {r.created_at.strftime('%d/%m/%Y %H:%M')}")
        lines.append(f"- {_counts_human(counts)}")
        lines.append(f"- {r.description or ''}")
        lines.append("")  # ligne vide entre les événements

    content = "\n".join(lines) + ("\n" if lines else "")
    headers = {
        "Content-Type": "text/plain; charset=utf-8",
        "Content-Disposition": f'attachment; filename="history.txt"',
    }
    return Response(content=content, media_type="text/plain", headers=headers)
