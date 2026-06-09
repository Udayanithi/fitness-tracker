"""
app/modules/ai_engine.py — AI Fitness Recommendation Engine
Uses Groq Python SDK for fast, free LLM responses.
"""

from groq import Groq
from app.database import get_db
from app.models import User, HealthProfile, WorkoutPlan
from app.utils.display import (
    print_section, print_success, print_error,
    print_info, print_warning, display_ai_output, confirm
)
from config import GROQ_API_KEY, GROQ_MODEL


# ── Groq Client ───────────────────────────────────────────────────────────────

def _call_groq(prompt: str) -> str:
    if not GROQ_API_KEY:
        raise ValueError(
            "GROQ_API_KEY is not set. Add it to your .env file.\n"
            "Get a free key at: https://console.groq.com"
        )
    client = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2048,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


# ── Prompt Builder ────────────────────────────────────────────────────────────

def _build_workout_prompt(user: User, hp: HealthProfile) -> str:
    goal_descriptions = {
        "fat_loss":    "Fat Loss — burn fat while preserving muscle",
        "muscle_gain": "Muscle Gain — build lean muscle mass",
        "weight_gain": "Weight Gain — increase overall body mass",
        "maintenance": "Maintenance — stay fit and healthy",
    }
    goal_label = goal_descriptions.get(user.fitness_goal.value, user.fitness_goal.value)

    return f"""You are an expert certified personal trainer and fitness coach.

Create a detailed, personalised weekly workout plan for this user:

USER PROFILE:
- Name: {user.name}
- Age: {user.age} | Gender: {user.gender.value}
- Height: {user.height_cm} cm | Weight: {user.weight_kg} kg
- Occupation: {user.occupation or 'Not specified'}
- Work Schedule: {user.work_schedule or 'Not specified'}
- Sleep Schedule: {user.sleep_schedule or 'Not specified'}

HEALTH METRICS:
- BMI: {hp.bmi} ({hp.bmi_category})
- Body Fat: {hp.body_fat_percentage}%
- BMR: {hp.bmr} kcal/day | TDEE: {hp.tdee} kcal/day
- Activity Level: {hp.activity_level.replace('_', ' ').title()}
- Fitness Level: {hp.fitness_level.value.title()}

FITNESS GOAL: {goal_label}
TARGET CALORIES: {hp.target_calories} kcal/day

INSTRUCTIONS:
1. Create a 7-day weekly workout schedule
2. Match intensity to fitness level ({hp.fitness_level.value})
3. Include: exercise name, sets x reps, rest time, and one coaching tip per exercise
4. Add warm-up (5 min) and cool-down (5 min) for each workout day
5. Schedule rest days appropriately (at least 2 per week)
6. Consider the user's occupation ({user.occupation}) and sleep schedule
7. For each workout day list: Day name, Muscle focus, Duration, and all exercises
8. End with 3-5 key tips specific to this user's goal and lifestyle

FORMAT: Use clear sections with headers. Be specific with numbers (sets, reps, rest seconds).
Make it practical and motivating. Write in a coaching tone.""".strip()


# ── Generate Workout Plan ─────────────────────────────────────────────────────

def generate_workout_plan(user: User, hp: HealthProfile) -> WorkoutPlan | None:
    existing = None
    with get_db() as db:
        existing = db.query(WorkoutPlan).filter(
            WorkoutPlan.user_id == user.id,
            WorkoutPlan.is_active == True
        ).first()
        if existing:
            db.expunge(existing)

    if existing:
        print_info("An active workout plan already exists.")
        if not confirm("Generate a new workout plan? (replaces current)"):
            display_ai_output("Your Workout Plan", existing.plan_content)
            return existing

    print_section("Generating AI Workout Plan")
    print_info(f"Using Groq + {GROQ_MODEL} — response in ~5 seconds...")

    try:
        prompt = _build_workout_prompt(user, hp)
        plan_text = _call_groq(prompt)
    except Exception as e:
        print_error(f"Groq error: {e}")
        return None

    with get_db() as db:
        db.query(WorkoutPlan).filter(
            WorkoutPlan.user_id == user.id
        ).update({"is_active": False})

    plan_id = None
    with get_db() as db:
        plan = WorkoutPlan(
            user_id       = user.id,
            plan_type     = user.fitness_goal,
            fitness_level = hp.fitness_level,
            plan_content  = plan_text,
            is_active     = True,
        )
        db.add(plan)
        db.flush()
        plan_id = plan.id

    print_success("Workout plan generated and saved!")

    with get_db() as db:
        plan = db.query(WorkoutPlan).filter(WorkoutPlan.id == plan_id).first()
        db.expunge(plan)

    display_ai_output(
        f"Workout Plan — {user.name} ({user.fitness_goal.value.replace('_', ' ').title()})",
        plan.plan_content
    )
    return plan


# ── View Saved Plan ───────────────────────────────────────────────────────────

def get_active_workout_plan(user_id: int) -> WorkoutPlan | None:
    with get_db() as db:
        plan = db.query(WorkoutPlan).filter(
            WorkoutPlan.user_id == user_id,
            WorkoutPlan.is_active == True
        ).first()
        if plan:
            db.expunge(plan)
        return plan


def view_workout_plan(user: User) -> None:
    plan = get_active_workout_plan(user.id)
    if plan:
        display_ai_output(f"Workout Plan — {user.name}", plan.plan_content)
    else:
        print_warning("No workout plan found. Generate one from the menu first.")
