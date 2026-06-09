"""
app/modules/health.py — Health Analysis Engine

Calculates and saves:
- BMI + category (Underweight / Normal / Overweight / Obese)
- Body Fat % (U.S. Navy Method using neck/waist/height — or Deurenberg formula as fallback)
- BMR — Basal Metabolic Rate (Mifflin-St Jeor equation)
- TDEE — Total Daily Energy Expenditure (BMR × activity multiplier)
- Activity level (auto-detected from occupation + work/sleep schedule)
- Fitness level (beginner/intermediate/advanced — inferred from goal + age + BMI)
- Target calories (TDEE adjusted for fitness goal)
- Daily macro targets (protein, carbs, fat in grams)

All results are saved to the health_profiles table.
"""

import math
from app.database import get_db
from app.models import User, HealthProfile, FitnessLevelEnum
from app.utils.display import (
    console, print_section, print_success, print_info,
    print_warning, ask_choice, display_health_profile
)
from config import (
    BMI_UNDERWEIGHT, BMI_NORMAL_MAX, BMI_OVERWEIGHT,
    ACTIVITY_MULTIPLIERS
)


# ── BMI ───────────────────────────────────────────────────────────────────────

def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    """BMI = weight(kg) / height(m)²"""
    height_m = height_cm / 100
    return round(weight_kg / (height_m ** 2), 1)


def get_bmi_category(bmi: float) -> str:
    if bmi < BMI_UNDERWEIGHT:
        return "Underweight"
    elif bmi <= BMI_NORMAL_MAX:
        return "Normal"
    elif bmi <= BMI_OVERWEIGHT:
        return "Overweight"
    else:
        return "Obese"


# ── Body Fat % ────────────────────────────────────────────────────────────────

def estimate_body_fat(bmi: float, age: int, gender: str) -> float:
    """
    Deurenberg formula (1991) — works without tape measurements.
    body_fat% = (1.20 × BMI) + (0.23 × age) − (10.8 × sex) − 5.4
    sex: 1 = male, 0 = female
    """
    sex = 1 if gender.lower() == "male" else 0
    bf = (1.20 * bmi) + (0.23 * age) - (10.8 * sex) - 5.4
    return round(max(bf, 3.0), 1)   # Clamp to at least 3% (physiological minimum)


# ── BMR ───────────────────────────────────────────────────────────────────────

def calculate_bmr(weight_kg: float, height_cm: float, age: int, gender: str) -> float:
    """
    Mifflin-St Jeor Equation (most accurate for general population).
    Male:   BMR = 10W + 6.25H - 5A + 5
    Female: BMR = 10W + 6.25H - 5A - 161
    W = weight kg, H = height cm, A = age
    """
    base = (10 * weight_kg) + (6.25 * height_cm) - (5 * age)
    if gender.lower() == "male":
        return round(base + 5, 1)
    else:
        return round(base - 161, 1)


# ── Activity Level ────────────────────────────────────────────────────────────

def detect_activity_level(occupation: str, work_schedule: str, sleep_schedule: str) -> str:
    """
    Auto-detects activity level from occupation and schedule keywords.
    Returns one of the ACTIVITY_MULTIPLIERS keys.
    """
    occ   = (occupation or "").lower()
    work  = (work_schedule or "").lower()
    sleep = (sleep_schedule or "").lower()
    combined = f"{occ} {work} {sleep}"

    # Physical jobs → very_active
    physical_keywords = [
        "driver", "labor", "labourer", "construction", "farmer", "delivery",
        "mechanic", "carpenter", "plumber", "factory", "warehouse", "nurse",
        "athlete", "trainer", "coach", "military", "police", "firefighter"
    ]
    # Moderate activity
    moderate_keywords = [
        "teacher", "sales", "retail", "waiter", "chef", "cook", "cleaner",
        "technician", "field", "outdoor"
    ]
    # Sedentary
    sedentary_keywords = [
        "desk", "office", "software", "developer", "engineer", "manager",
        "analyst", "accountant", "banker", "lawyer", "doctor", "student",
        "unemployed", "work from home", "remote", "wfh", "0"
    ]

    for kw in physical_keywords:
        if kw in combined:
            return "very_active"
    for kw in moderate_keywords:
        if kw in combined:
            return "moderately_active"
    for kw in sedentary_keywords:
        if kw in combined:
            return "sedentary"

    # Default: lightly active
    return "lightly_active"


# ── Fitness Level ─────────────────────────────────────────────────────────────

def determine_fitness_level(bmi: float, age: int, goal: str) -> FitnessLevelEnum:
    """
    Infers beginner / intermediate / advanced from BMI, age, and goal.
    Conservative by default — better to start someone at beginner than overwhelm them.
    """
    # Obese or underweight → beginner regardless
    if bmi < BMI_UNDERWEIGHT or bmi > BMI_OVERWEIGHT:
        return FitnessLevelEnum.beginner

    # Age-based adjustment
    if age < 18 or age > 55:
        return FitnessLevelEnum.beginner

    # Maintenance goal usually means some existing fitness base
    if goal == "maintenance":
        return FitnessLevelEnum.intermediate

    # Muscle gain with normal BMI → intermediate
    if goal == "muscle_gain" and BMI_UNDERWEIGHT <= bmi <= BMI_NORMAL_MAX:
        return FitnessLevelEnum.intermediate

    return FitnessLevelEnum.beginner


# ── Target Calories ───────────────────────────────────────────────────────────

def calculate_target_calories(tdee: float, goal: str) -> float:
    """
    Adjusts TDEE based on fitness goal:
    - Fat loss:    deficit of 500 kcal/day (safe ~0.5 kg/week loss)
    - Weight gain: surplus of 300 kcal/day (lean bulk)
    - Muscle gain: surplus of 200 kcal/day (recomp-friendly)
    - Maintenance: no change
    """
    adjustments = {
        "fat_loss":    -500,
        "weight_gain": +300,
        "muscle_gain": +200,
        "maintenance":    0,
    }
    adj = adjustments.get(goal, 0)
    # Never go below 1200 kcal (unsafe)
    return round(max(tdee + adj, 1200), 0)


# ── Macro Targets ─────────────────────────────────────────────────────────────

def calculate_macros(
    target_calories: float,
    weight_kg: float,
    goal: str
) -> tuple[float, float, float]:
    """
    Returns (protein_g, carbs_g, fat_g) based on goal.

    Protein targets:
    - Fat loss:    2.2g per kg (preserve muscle during deficit)
    - Muscle gain: 2.0g per kg
    - Weight gain: 1.8g per kg
    - Maintenance: 1.6g per kg

    Remaining calories split between carbs (55%) and fat (45%) after protein.
    """
    protein_per_kg = {
        "fat_loss":    2.2,
        "muscle_gain": 2.0,
        "weight_gain": 1.8,
        "maintenance": 1.6,
    }
    p_per_kg = protein_per_kg.get(goal, 1.8)
    protein_g = round(weight_kg * p_per_kg, 1)
    protein_calories = protein_g * 4   # 4 kcal per gram of protein

    remaining = target_calories - protein_calories
    fat_g   = round((remaining * 0.35) / 9, 1)   # 9 kcal per gram of fat
    carbs_g = round((remaining * 0.65) / 4, 1)   # 4 kcal per gram of carbs

    return protein_g, carbs_g, fat_g


# ── Main Analysis Function ────────────────────────────────────────────────────

def run_health_analysis(user: User) -> HealthProfile | None:
    """
    Runs the full health analysis for a user and saves to DB.
    If a health profile already exists, asks the user if they want to recalculate.
    Returns the HealthProfile object.
    """
    # Check if profile already exists
    with get_db() as db:
        existing = db.query(HealthProfile).filter(
            HealthProfile.user_id == user.id
        ).first()
        if existing:
            db.expunge(existing)

    if existing:
        print_info("A health profile already exists for this user.")
        from app.utils.display import confirm
        if not confirm("Recalculate and update health profile?"):
            display_health_profile(existing, user.name)
            return existing

    print_section("Running Health Analysis")
    print_info("Analysing your data...")

    # ── Calculations ──────────────────────────────────────────────────────────
    bmi          = calculate_bmi(user.weight_kg, user.height_cm)
    bmi_category = get_bmi_category(bmi)
    body_fat     = estimate_body_fat(bmi, user.age, user.gender.value)
    bmr          = calculate_bmr(user.weight_kg, user.height_cm, user.age, user.gender.value)
    activity     = detect_activity_level(
                       user.occupation or "",
                       user.work_schedule or "",
                       user.sleep_schedule or ""
                   )
    multiplier   = ACTIVITY_MULTIPLIERS[activity]
    tdee         = round(bmr * multiplier, 1)
    fitness_lvl  = determine_fitness_level(bmi, user.age, user.fitness_goal.value)
    target_cal   = calculate_target_calories(tdee, user.fitness_goal.value)
    protein_g, carbs_g, fat_g = calculate_macros(target_cal, user.weight_kg, user.fitness_goal.value)

    # ── Save to DB ────────────────────────────────────────────────────────────
    with get_db() as db:
        # Delete old profile if recalculating
        db.query(HealthProfile).filter(HealthProfile.user_id == user.id).delete()

        hp = HealthProfile(
            user_id             = user.id,
            bmi                 = bmi,
            bmi_category        = bmi_category,
            body_fat_percentage = body_fat,
            bmr                 = bmr,
            tdee                = tdee,
            activity_level      = activity,
            fitness_level       = fitness_lvl,
            target_calories     = target_cal,
            protein_g           = protein_g,
            carbs_g             = carbs_g,
            fat_g               = fat_g,
        )
        db.add(hp)
        db.flush()
        hp_id = hp.id

    print_success("Health analysis complete!")

    # Re-fetch detached
    with get_db() as db:
        hp = db.query(HealthProfile).filter(HealthProfile.id == hp_id).first()
        db.expunge(hp)

    display_health_profile(hp, user.name)
    return hp


# ── Load Existing Profile ─────────────────────────────────────────────────────

def get_health_profile(user_id: int) -> HealthProfile | None:
    """Returns the health profile for a user, or None if not yet calculated."""
    with get_db() as db:
        hp = db.query(HealthProfile).filter(
            HealthProfile.user_id == user_id
        ).first()
        if hp:
            db.expunge(hp)
        return hp
