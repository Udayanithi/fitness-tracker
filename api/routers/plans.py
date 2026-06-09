"""api/routers/plans.py — AI workout and diet plan endpoints"""

from fastapi import APIRouter, HTTPException
from api.schemas import WorkoutPlanResponse, DietPlanResponse, MessageResponse
from app.database import get_db
from app.models import User
from app.modules.health import get_health_profile
from app.modules.ai_engine import generate_workout_plan, get_active_workout_plan
from app.modules.diet import generate_diet_plan, get_active_diet_plan

router = APIRouter(prefix="/plans", tags=["AI Plans"])


def _get_user(user_id: int) -> User:
    with get_db() as db:
        u = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not u:
            raise HTTPException(404, f"User {user_id} not found.")
        db.expunge(u)
    return u


def _get_hp(user_id: int):
    hp = get_health_profile(user_id)
    if not hp:
        raise HTTPException(404, f"Run POST /health/{user_id}/analyze first.")
    return hp


@router.post("/{user_id}/workout", response_model=WorkoutPlanResponse)
def create_workout_plan(user_id: int):
    """Generate AI workout plan via Groq + Llama."""
    plan = generate_workout_plan(_get_user(user_id), _get_hp(user_id))
    if not plan:
        raise HTTPException(500, "Failed to generate workout plan. Check GROQ_API_KEY.")
    return plan


@router.get("/{user_id}/workout", response_model=WorkoutPlanResponse)
def get_workout_plan(user_id: int):
    _get_user(user_id)
    plan = get_active_workout_plan(user_id)
    if not plan:
        raise HTTPException(404, "No workout plan found. POST /plans/{user_id}/workout first.")
    return plan


@router.post("/{user_id}/diet", response_model=DietPlanResponse)
def create_diet_plan(user_id: int):
    """Generate AI diet plan via Groq + Llama."""
    plan = generate_diet_plan(_get_user(user_id), _get_hp(user_id))
    if not plan:
        raise HTTPException(500, "Failed to generate diet plan. Check GROQ_API_KEY.")
    return plan


@router.get("/{user_id}/diet", response_model=DietPlanResponse)
def get_diet_plan(user_id: int):
    _get_user(user_id)
    plan = get_active_diet_plan(user_id)
    if not plan:
        raise HTTPException(404, "No diet plan found. POST /plans/{user_id}/diet first.")
    return plan


@router.get("/{user_id}/grocery", response_model=MessageResponse)
def get_grocery_list(user_id: int):
    _get_user(user_id)
    plan = get_active_diet_plan(user_id)
    if not plan or not plan.grocery_list:
        raise HTTPException(404, "No grocery list found. Generate a diet plan first.")
    return {"message": plan.grocery_list, "success": True}
