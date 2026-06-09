"""api/routers/users.py — User endpoints"""

from fastapi import APIRouter, HTTPException, status
from passlib.context import CryptContext
from api.schemas import UserCreate, UserLogin, UserUpdate, UserResponse, UserListResponse, MessageResponse
from app.database import get_db
from app.models import User, GenderEnum, FoodPrefEnum, FitnessGoalEnum

router = APIRouter(prefix="/users", tags=["Users"])

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _hash(password: str) -> str:
    return pwd_ctx.hash(password)


def _verify(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)


def _fetch_user(user_id: int) -> User:
    with get_db() as db:
        u = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not u:
            raise HTTPException(404, f"User {user_id} not found.")
        db.expunge(u)
    return u


@router.post("/register", response_model=UserResponse, status_code=201)
def register_user(data: UserCreate):
    with get_db() as db:
        if db.query(User).filter(User.email == data.email.lower()).first():
            raise HTTPException(409, f"Email '{data.email}' already registered.")
    try:
        gender       = GenderEnum(data.gender)
        food_pref    = FoodPrefEnum(data.food_preference)
        fitness_goal = FitnessGoalEnum(data.fitness_goal)
    except ValueError as e:
        raise HTTPException(422, str(e))

    with get_db() as db:
        u = User(
            name=data.name.strip(), age=data.age, gender=gender,
            address=data.address, email=data.email.lower().strip(),
            password_hash=_hash(data.password),
            height_cm=data.height_cm, weight_kg=data.weight_kg,
            occupation=data.occupation, work_schedule=data.work_schedule,
            sleep_schedule=data.sleep_schedule, food_preference=food_pref,
            monthly_budget=data.monthly_budget, fitness_goal=fitness_goal,
            phone_number=data.phone_number,
        )
        db.add(u)
        db.flush()
        uid = u.id

    return _fetch_user(uid)


@router.post("/login", response_model=UserResponse)
def login_user(data: UserLogin):
    """Login with email + password."""
    with get_db() as db:
        u = db.query(User).filter(User.email == data.email.lower(), User.is_active == True).first()
        if not u:
            raise HTTPException(401, "Invalid email or password.")
        # Support legacy accounts that have no password hash yet
        if u.password_hash and not _verify(data.password, u.password_hash):
            raise HTTPException(401, "Invalid email or password.")
        db.expunge(u)
    return u


@router.get("/", response_model=UserListResponse)
def list_users():
    with get_db() as db:
        users = db.query(User).filter(User.is_active == True).all()
        db.expunge_all()
    return {"users": users, "total": len(users)}


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int):
    return _fetch_user(user_id)


@router.put("/{user_id}", response_model=UserResponse)
def update_user(user_id: int, data: UserUpdate):
    """Update editable profile fields for a user."""
    update_data = data.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(400, "No fields provided to update.")

    # Validate enum fields if provided
    try:
        if "gender" in update_data:
            update_data["gender"] = GenderEnum(update_data["gender"])
        if "food_preference" in update_data:
            update_data["food_preference"] = FoodPrefEnum(update_data["food_preference"])
        if "fitness_goal" in update_data:
            update_data["fitness_goal"] = FitnessGoalEnum(update_data["fitness_goal"])
    except ValueError as e:
        raise HTTPException(422, str(e))

    with get_db() as db:
        u = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not u:
            raise HTTPException(404, f"User {user_id} not found.")
        for field, value in update_data.items():
            setattr(u, field, value)
        db.flush()

    return _fetch_user(user_id)


@router.put("/{user_id}/weight", response_model=MessageResponse)
def update_weight(user_id: int, weight_kg: float):
    if not 20 <= weight_kg <= 500:
        raise HTTPException(422, "Weight must be 20–500 kg.")
    with get_db() as db:
        u = db.query(User).filter(User.id == user_id).first()
        if not u:
            raise HTTPException(404, f"User {user_id} not found.")
        u.weight_kg = weight_kg
    return {"message": f"Weight updated to {weight_kg} kg.", "success": True}
