"""api/routers/progress.py — Progress tracking endpoints"""

from fastapi import APIRouter, HTTPException
from api.schemas import ProgressCreate, ProgressResponse, ProgressHistoryResponse
from app.database import get_db
from app.models import User, ProgressEntry
from datetime import date, timedelta

router = APIRouter(prefix="/progress", tags=["Progress Tracking"])


def _get_user(user_id: int) -> User:
    with get_db() as db:
        u = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not u:
            raise HTTPException(404, f"User {user_id} not found.")
        db.expunge(u)
    return u


@router.post("/{user_id}", response_model=ProgressResponse, status_code=201)
def log_progress_entry(user_id: int, data: ProgressCreate):
    """Log a new weight/measurement entry."""
    _get_user(user_id)
    with get_db() as db:
        entry = ProgressEntry(
            user_id=user_id, weight_kg=data.weight_kg,
            chest_cm=data.chest_cm, waist_cm=data.waist_cm,
            hips_cm=data.hips_cm, arms_cm=data.arms_cm,
            thighs_cm=data.thighs_cm, notes=data.notes,
        )
        db.add(entry)
        db.flush()
        eid = entry.id
    with get_db() as db:
        e = db.query(ProgressEntry).filter(ProgressEntry.id == eid).first()
        db.expunge(e)
    return e


@router.get("/{user_id}", response_model=ProgressHistoryResponse)
def get_history(user_id: int):
    """Get all progress entries."""
    _get_user(user_id)
    with get_db() as db:
        entries = db.query(ProgressEntry).filter(
            ProgressEntry.user_id == user_id
        ).order_by(ProgressEntry.entry_date.desc()).all()
        db.expunge_all()
    return {"entries": entries, "total": len(entries)}


@router.get("/{user_id}/report")
def get_report(user_id: int):
    """Progress report — all-time, weekly, monthly comparisons."""
    user = _get_user(user_id)
    with get_db() as db:
        entries = db.query(ProgressEntry).filter(
            ProgressEntry.user_id == user_id
        ).order_by(ProgressEntry.entry_date.asc()).all()
        db.expunge_all()

    if len(entries) < 2:
        raise HTTPException(400, "Need at least 2 entries to generate a report.")

    first, latest = entries[0], entries[-1]
    today = date.today()

    def change(a, b):
        if a is None or b is None:
            return None
        d = round(b - a, 1)
        return {"start": a, "current": b, "change": d, "direction": "↑" if d > 0 else "↓"}

    weekly  = [e for e in entries if e.entry_date >= today - timedelta(days=7)]
    monthly = [e for e in entries if e.entry_date >= today - timedelta(days=30)]

    return {
        "user_id":       user_id,
        "total_entries": len(entries),
        "goal":          user.fitness_goal.value,
        "first_entry":   str(first.entry_date),
        "latest_entry":  str(latest.entry_date),
        "all_time":      change(first.weight_kg, latest.weight_kg),
        "weekly":        change(weekly[0].weight_kg, weekly[-1].weight_kg) if len(weekly) > 1 else None,
        "monthly":       change(monthly[0].weight_kg, monthly[-1].weight_kg) if len(monthly) > 1 else None,
    }
