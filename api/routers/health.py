"""api/routers/health.py — Health analysis endpoints"""

from fastapi import APIRouter, HTTPException
from api.schemas import HealthProfileResponse
from app.database import get_db
from app.models import User
from app.modules.health import run_health_analysis, get_health_profile

router = APIRouter(prefix="/health", tags=["Health Analysis"])


def _get_user(user_id: int) -> User:
    with get_db() as db:
        u = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not u:
            raise HTTPException(404, f"User {user_id} not found.")
        db.expunge(u)
    return u


@router.post("/{user_id}/analyze", response_model=HealthProfileResponse)
def analyze_health(user_id: int):
    """Run full health analysis — BMI, BMR, TDEE, macros. Always recalculates."""
    user = _get_user(user_id)
    # Delete existing profile so run_health_analysis skips the CLI "recalculate?" prompt
    from app.database import get_db as _db
    from app.models import HealthProfile
    with _db() as db:
        db.query(HealthProfile).filter(HealthProfile.user_id == user_id).delete()
    hp = run_health_analysis(user)
    if not hp:
        raise HTTPException(500, "Health analysis failed.")
    return hp


@router.get("/{user_id}", response_model=HealthProfileResponse)
def get_health(user_id: int):
    """Get saved health profile."""
    _get_user(user_id)
    hp = get_health_profile(user_id)
    if not hp:
        raise HTTPException(404, f"No health profile for user {user_id}. Run POST /health/{user_id}/analyze first.")
    return hp
