"""
app/models.py — SQLAlchemy ORM Models (Database Schema)

Tables defined here:
- User           → Core registration data
- HealthProfile  → Calculated health metrics (BMI, BMR, etc.)
- WorkoutPlan    → AI-generated workout plans per user
- DietPlan       → AI-generated diet plans per user
- ProgressEntry  → Weekly/monthly weight & measurement logs
- Reminder       → User-configured reminders
"""

from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Float, Boolean,
    DateTime, Date, ForeignKey, Text, Enum
)
from sqlalchemy.orm import relationship
import enum

from app.database import Base


# ── Enums ─────────────────────────────────────────────────────────────────────

class GenderEnum(str, enum.Enum):
    male   = "male"
    female = "female"
    other  = "other"

class FitnessGoalEnum(str, enum.Enum):
    fat_loss    = "fat_loss"
    weight_gain = "weight_gain"
    muscle_gain = "muscle_gain"
    maintenance = "maintenance"

class FoodPrefEnum(str, enum.Enum):
    veg        = "veg"
    non_veg    = "non_veg"
    vegan      = "vegan"
    eggetarian = "eggetarian"

class FitnessLevelEnum(str, enum.Enum):
    beginner     = "beginner"
    intermediate = "intermediate"
    advanced     = "advanced"

class ReminderTypeEnum(str, enum.Enum):
    meal    = "meal"
    workout = "workout"
    water   = "water"
    custom  = "custom"


# ── User ──────────────────────────────────────────────────────────────────────

class User(Base):
    """
    Stores registration details entered by the user.
    One user can have many health profiles, workout plans, etc.
    """
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, index=True)
    name            = Column(String(100), nullable=False)
    age             = Column(Integer, nullable=False)
    gender          = Column(Enum(GenderEnum), nullable=False)
    address         = Column(String(255))
    email           = Column(String(150), unique=True, nullable=False, index=True)
    height_cm       = Column(Float, nullable=False)   # centimetres
    weight_kg       = Column(Float, nullable=False)   # kilograms
    occupation      = Column(String(100))
    work_schedule   = Column(String(100))             # e.g. "9am-6pm weekdays"
    sleep_schedule  = Column(String(100))             # e.g. "11pm-7am"
    food_preference = Column(Enum(FoodPrefEnum), nullable=False)
    monthly_budget  = Column(Float, nullable=False)   # INR
    fitness_goal    = Column(Enum(FitnessGoalEnum), nullable=False)
    phone_number    = Column(String(20), nullable=True)  # e.g. +919876543210
    password_hash   = Column(String(255), nullable=True)  # bcrypt hash
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    health_profile  = relationship("HealthProfile", back_populates="user",
                                   uselist=False, cascade="all, delete-orphan")
    workout_plans   = relationship("WorkoutPlan",   back_populates="user",
                                   cascade="all, delete-orphan")
    diet_plans      = relationship("DietPlan",      back_populates="user",
                                   cascade="all, delete-orphan")
    progress        = relationship("ProgressEntry", back_populates="user",
                                   cascade="all, delete-orphan")
    reminders       = relationship("Reminder",      back_populates="user",
                                   cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User id={self.id} name={self.name} email={self.email}>"


# ── HealthProfile ─────────────────────────────────────────────────────────────

class HealthProfile(Base):
    """
    Stores calculated health metrics for a user.
    Recalculated whenever the user updates weight/height.
    """
    __tablename__ = "health_profiles"

    id                   = Column(Integer, primary_key=True, index=True)
    user_id              = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    bmi                  = Column(Float)
    bmi_category         = Column(String(20))   # Underweight / Normal / Overweight / Obese
    body_fat_percentage  = Column(Float)
    bmr                  = Column(Float)         # Basal Metabolic Rate (kcal/day)
    tdee                 = Column(Float)         # Total Daily Energy Expenditure
    activity_level       = Column(String(30))    # sedentary / lightly_active / etc.
    fitness_level        = Column(Enum(FitnessLevelEnum))
    target_calories      = Column(Float)         # Adjusted for fitness goal
    protein_g            = Column(Float)         # Daily protein target (grams)
    carbs_g              = Column(Float)         # Daily carbs target (grams)
    fat_g                = Column(Float)         # Daily fat target (grams)
    calculated_at        = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="health_profile")

    def __repr__(self):
        return f"<HealthProfile user_id={self.user_id} bmi={self.bmi} category={self.bmi_category}>"


# ── WorkoutPlan ───────────────────────────────────────────────────────────────

class WorkoutPlan(Base):
    """
    Stores AI-generated workout plans. A user can have multiple plans
    (e.g., one generated per month or after goal change).
    """
    __tablename__ = "workout_plans"

    id           = Column(Integer, primary_key=True, index=True)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_type    = Column(Enum(FitnessGoalEnum))   # fat_loss / muscle_gain / etc.
    fitness_level= Column(Enum(FitnessLevelEnum))
    plan_content = Column(Text, nullable=False)    # Full AI-generated plan (markdown)
    is_active    = Column(Boolean, default=True)
    created_at   = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="workout_plans")


# ── DietPlan ──────────────────────────────────────────────────────────────────

class DietPlan(Base):
    """
    Stores AI-generated diet plans including meal timings,
    macro breakdown, and grocery lists.
    """
    __tablename__ = "diet_plans"

    id                   = Column(Integer, primary_key=True, index=True)
    user_id              = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_content         = Column(Text, nullable=False)    # Full plan (markdown)
    grocery_list         = Column(Text)                    # Grocery shopping list
    estimated_cost_inr   = Column(Float)                   # Estimated monthly cost
    is_active            = Column(Boolean, default=True)
    created_at           = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="diet_plans")


# ── ProgressEntry ─────────────────────────────────────────────────────────────

class ProgressEntry(Base):
    """
    Stores periodic weight/measurement logs.
    Used for weekly and monthly progress comparisons.
    """
    __tablename__ = "progress_entries"

    id             = Column(Integer, primary_key=True, index=True)
    user_id        = Column(Integer, ForeignKey("users.id"), nullable=False)
    entry_date     = Column(Date, default=date.today, nullable=False)
    weight_kg      = Column(Float, nullable=False)
    chest_cm       = Column(Float)
    waist_cm       = Column(Float)
    hips_cm        = Column(Float)
    arms_cm        = Column(Float)
    thighs_cm      = Column(Float)
    notes          = Column(Text)
    created_at     = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="progress")

    def __repr__(self):
        return f"<ProgressEntry user_id={self.user_id} date={self.entry_date} weight={self.weight_kg}>"


# ── Reminder ──────────────────────────────────────────────────────────────────

class Reminder(Base):
    """
    Stores user-configured reminders for meals, workouts, and water intake.
    """
    __tablename__ = "reminders"

    id            = Column(Integer, primary_key=True, index=True)
    user_id       = Column(Integer, ForeignKey("users.id"), nullable=False)
    reminder_type = Column(Enum(ReminderTypeEnum), nullable=False)
    title         = Column(String(100), nullable=False)
    message       = Column(String(255))
    time_str      = Column(String(10), nullable=False)   # "HH:MM" 24-hour format
    days_of_week  = Column(String(20), default="all")    # "all" or "mon,tue,wed"
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="reminders")

    def __repr__(self):
        return f"<Reminder user_id={self.user_id} type={self.reminder_type} time={self.time_str}>"
