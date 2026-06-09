"""
api/schemas.py — Pydantic request/response models for all API endpoints
"""

from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime, date


# ── User ──────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    name:            str
    age:             int
    gender:          str
    address:         Optional[str] = None
    email:           str
    password:        str
    height_cm:       float
    weight_kg:       float
    occupation:      Optional[str] = None
    work_schedule:   Optional[str] = None
    sleep_schedule:  Optional[str] = None
    food_preference: str
    monthly_budget:  float
    fitness_goal:    str
    phone_number:    Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v

    @field_validator("age")
    @classmethod
    def age_range(cls, v):
        if not 5 <= v <= 120:
            raise ValueError("Age must be between 5 and 120")
        return v

    @field_validator("height_cm")
    @classmethod
    def height_range(cls, v):
        if not 50 <= v <= 300:
            raise ValueError("Height must be between 50 and 300 cm")
        return v

    @field_validator("weight_kg")
    @classmethod
    def weight_range(cls, v):
        if not 20 <= v <= 500:
            raise ValueError("Weight must be between 20 and 500 kg")
        return v

    @field_validator("monthly_budget")
    @classmethod
    def budget_min(cls, v):
        if v < 500:
            raise ValueError("Monthly budget must be at least 500")
        return v


class UserLogin(BaseModel):
    email:    str
    password: str


class UserUpdate(BaseModel):
    name:            Optional[str]   = None
    age:             Optional[int]   = None
    gender:          Optional[str]   = None
    address:         Optional[str]   = None
    phone_number:    Optional[str]   = None
    height_cm:       Optional[float] = None
    weight_kg:       Optional[float] = None
    occupation:      Optional[str]   = None
    work_schedule:   Optional[str]   = None
    sleep_schedule:  Optional[str]   = None
    food_preference: Optional[str]   = None
    monthly_budget:  Optional[float] = None
    fitness_goal:    Optional[str]   = None

    @field_validator("age")
    @classmethod
    def age_range(cls, v):
        if v is not None and not 5 <= v <= 120:
            raise ValueError("Age must be between 5 and 120")
        return v

    @field_validator("height_cm")
    @classmethod
    def height_range(cls, v):
        if v is not None and not 50 <= v <= 300:
            raise ValueError("Height must be between 50 and 300 cm")
        return v

    @field_validator("weight_kg")
    @classmethod
    def weight_range(cls, v):
        if v is not None and not 20 <= v <= 500:
            raise ValueError("Weight must be between 20 and 500 kg")
        return v

    @field_validator("monthly_budget")
    @classmethod
    def budget_min(cls, v):
        if v is not None and v < 500:
            raise ValueError("Monthly budget must be at least 500")
        return v


class UserResponse(BaseModel):
    id:              int
    name:            str
    age:             int
    gender:          str
    address:         Optional[str]
    email:           str
    height_cm:       float
    weight_kg:       float
    occupation:      Optional[str]
    work_schedule:   Optional[str]
    sleep_schedule:  Optional[str]
    food_preference: str
    monthly_budget:  float
    fitness_goal:    str
    phone_number:    Optional[str]
    created_at:      datetime
    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    users: list[UserResponse]
    total: int


# ── Health ────────────────────────────────────────────────────────────────────

class HealthProfileResponse(BaseModel):
    id:                   int
    user_id:              int
    bmi:                  Optional[float]
    bmi_category:         Optional[str]
    body_fat_percentage:  Optional[float]
    bmr:                  Optional[float]
    tdee:                 Optional[float]
    activity_level:       Optional[str]
    fitness_level:        Optional[str]
    target_calories:      Optional[float]
    protein_g:            Optional[float]
    carbs_g:              Optional[float]
    fat_g:                Optional[float]
    calculated_at:        Optional[datetime]
    model_config = {"from_attributes": True}


# ── Plans ─────────────────────────────────────────────────────────────────────

class WorkoutPlanResponse(BaseModel):
    id:            int
    user_id:       int
    plan_type:     Optional[str]
    fitness_level: Optional[str]
    plan_content:  str
    is_active:     bool
    created_at:    datetime
    model_config = {"from_attributes": True}


class DietPlanResponse(BaseModel):
    id:                  int
    user_id:             int
    plan_content:        str
    grocery_list:        Optional[str]
    estimated_cost_inr:  Optional[float]
    is_active:           bool
    created_at:          datetime
    model_config = {"from_attributes": True}


# ── Progress ──────────────────────────────────────────────────────────────────

class ProgressCreate(BaseModel):
    weight_kg:  float
    chest_cm:   Optional[float] = None
    waist_cm:   Optional[float] = None
    hips_cm:    Optional[float] = None
    arms_cm:    Optional[float] = None
    thighs_cm:  Optional[float] = None
    notes:      Optional[str]   = None

    @field_validator("weight_kg")
    @classmethod
    def weight_range(cls, v):
        if not 20 <= v <= 500:
            raise ValueError("Weight must be between 20 and 500 kg")
        return v


class ProgressResponse(BaseModel):
    id:          int
    user_id:     int
    entry_date:  date
    weight_kg:   float
    chest_cm:    Optional[float]
    waist_cm:    Optional[float]
    hips_cm:     Optional[float]
    arms_cm:     Optional[float]
    thighs_cm:   Optional[float]
    notes:       Optional[str]
    created_at:  datetime
    model_config = {"from_attributes": True}


class ProgressHistoryResponse(BaseModel):
    entries: list[ProgressResponse]
    total:   int


# ── Generic ───────────────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str
    success: bool = True


# ── Reminders ─────────────────────────────────────────────────────────────────

class ReminderCreate(BaseModel):
    reminder_type: str   # meal | workout | water | custom
    title:         str
    message:       Optional[str] = None
    time_str:      str           # HH:MM
    days_of_week:  str = "all"   # all | mon,tue,wed,thu,fri | sat,sun

    @field_validator("time_str")
    @classmethod
    def valid_time(cls, v):
        import re
        if not re.match(r"^\d{2}:\d{2}$", v):
            raise ValueError("time_str must be HH:MM format")
        h, m = int(v[:2]), int(v[3:])
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError("Invalid time value")
        return v

    @field_validator("reminder_type")
    @classmethod
    def valid_type(cls, v):
        if v not in ("meal", "workout", "water", "custom"):
            raise ValueError("reminder_type must be meal, workout, water, or custom")
        return v


class ReminderResponse(BaseModel):
    id:            int
    user_id:       int
    reminder_type: str
    title:         str
    message:       Optional[str]
    time_str:      str
    days_of_week:  str
    is_active:     bool
    created_at:    datetime
    model_config = {"from_attributes": True}


class ReminderListResponse(BaseModel):
    reminders: list[ReminderResponse]
    total:     int
