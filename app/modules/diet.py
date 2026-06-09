"""
app/modules/diet.py — AI Diet Planner

Uses Groq API to generate:
- Personalised 7-day meal plans (breakfast, lunch, dinner, snacks)
- Meal timings based on user's sleep/work schedule
- Full macro breakdown per meal (protein, carbs, fat, calories)
- Budget-aware planning (within monthly food budget)
- Food preference aware (veg / non-veg / vegan / eggetarian)
- Weekly grocery shopping list with estimated costs
- Monthly expense estimate

All plans saved to the diet_plans table.
"""

from groq import Groq
from app.database import get_db
from app.models import User, HealthProfile, DietPlan
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
        max_tokens=3000,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


# ── Prompt Builders ───────────────────────────────────────────────────────────

def _build_diet_prompt(user: User, hp: HealthProfile) -> str:
    food_pref_labels = {
        "veg":         "Vegetarian — no meat or fish",
        "non_veg":     "Non-Vegetarian — includes meat, fish, eggs",
        "vegan":       "Vegan — no animal products at all",
        "eggetarian":  "Eggetarian — vegetarian but includes eggs",
    }
    food_label = food_pref_labels.get(user.food_preference.value, user.food_preference.value)

    goal_descriptions = {
        "fat_loss":    "Fat Loss — calorie deficit, high protein, low carbs",
        "muscle_gain": "Muscle Gain — calorie surplus, very high protein",
        "weight_gain": "Weight Gain — high calorie, balanced macros",
        "maintenance": "Maintenance — balanced diet at maintenance calories",
    }
    goal_label = goal_descriptions.get(user.fitness_goal.value, user.fitness_goal.value)

    weekly_budget = round(user.monthly_budget / 4.3, 0)

    return f"""You are an expert nutritionist and diet coach specialising in Indian cuisine.

Create a detailed, personalised 7-day meal plan for this user:

USER PROFILE:
- Name: {user.name}
- Age: {user.age} | Gender: {user.gender.value}
- Weight: {user.weight_kg} kg | Height: {user.height_cm} cm
- Occupation: {user.occupation or 'Not specified'}
- Work Schedule: {user.work_schedule or 'Not specified'}
- Sleep Schedule: {user.sleep_schedule or 'Not specified'}

HEALTH METRICS:
- BMI: {hp.bmi} ({hp.bmi_category})
- Activity Level: {hp.activity_level.replace('_', ' ').title()}
- Daily Calorie Target: {hp.target_calories} kcal
- Daily Protein Target: {hp.protein_g} g
- Daily Carbs Target: {hp.carbs_g} g
- Daily Fat Target: {hp.fat_g} g

DIET REQUIREMENTS:
- Food Preference: {food_label}
- Fitness Goal: {goal_label}
- Monthly Food Budget: ₹{user.monthly_budget:,.0f}
- Weekly Budget: ₹{weekly_budget:,.0f}

INSTRUCTIONS:
1. Create a full 7-day meal plan (Monday to Sunday)
2. Each day must have: Breakfast, Mid-Morning Snack, Lunch, Evening Snack, Dinner
3. Set meal timings based on the user's work schedule ({user.work_schedule}) and sleep schedule ({user.sleep_schedule})
4. For each meal provide:
   - Meal name and description
   - Exact portion sizes (in grams or cups)
   - Calories, Protein (g), Carbs (g), Fat (g)
   - Preparation time
5. All meals must strictly follow the food preference: {food_label}
6. Keep total daily cost within ₹{round(weekly_budget/7)} per day
7. Use commonly available Indian ingredients
8. After the 7-day plan, provide:
   - Complete weekly grocery shopping list with quantities and estimated costs in ₹
   - Total estimated weekly cost
   - Total estimated monthly cost
   - 3-5 diet tips specific to this user's goal and lifestyle

FORMAT: Use clear day-by-day sections with headers. Be specific with quantities.
Make meals practical, tasty, and easy to prepare. Use Indian food where possible.""".strip()


def _build_grocery_prompt(diet_plan_text: str, budget: float) -> str:
    return f"""Based on this 7-day meal plan, extract and create a clean, organised grocery shopping list.

MEAL PLAN:
{diet_plan_text[:2000]}

Create a grocery list organised by category:
- Proteins (meat/fish/eggs/legumes/dairy)
- Vegetables
- Fruits
- Grains & Cereals
- Oils, Spices & Condiments
- Dairy & Eggs (if applicable)

For each item: ingredient name, weekly quantity needed, estimated cost in ₹.
End with total estimated weekly cost and monthly cost (weekly × 4.3).
Keep total within ₹{budget:.0f}/month budget.

Be concise and practical. Indian market prices.""".strip()


# ── Generate Diet Plan ────────────────────────────────────────────────────────

def generate_diet_plan(user: User, hp: HealthProfile) -> DietPlan | None:
    """Generates a personalised diet plan via Groq and saves to DB."""

    # Check for existing active plan
    existing = None
    with get_db() as db:
        existing = db.query(DietPlan).filter(
            DietPlan.user_id == user.id,
            DietPlan.is_active == True
        ).first()
        if existing:
            db.expunge(existing)

    if existing:
        print_info("An active diet plan already exists.")
        if not confirm("Generate a new diet plan? (replaces current)"):
            display_ai_output("Your Diet Plan", existing.plan_content)
            return existing

    print_section("Generating AI Diet Plan")
    print_info(f"Using Groq + {GROQ_MODEL}")
    print_info("Step 1/2 — Building your 7-day meal plan...")

    try:
        diet_prompt = _build_diet_prompt(user, hp)
        plan_text = _call_groq(diet_prompt)
    except Exception as e:
        print_error(f"Groq error (diet plan): {e}")
        return None

    print_info("Step 2/2 — Building your grocery list...")

    try:
        grocery_prompt = _build_grocery_prompt(plan_text, user.monthly_budget)
        grocery_text = _call_groq(grocery_prompt)
    except Exception as e:
        print_warning(f"Grocery list generation failed: {e}")
        grocery_text = "Grocery list unavailable — regenerate to retry."

    # Deactivate old plans
    with get_db() as db:
        db.query(DietPlan).filter(
            DietPlan.user_id == user.id
        ).update({"is_active": False})

    # Save new plan
    plan_id = None
    with get_db() as db:
        plan = DietPlan(
            user_id           = user.id,
            plan_content      = plan_text,
            grocery_list      = grocery_text,
            estimated_cost_inr= user.monthly_budget,
            is_active         = True,
        )
        db.add(plan)
        db.flush()
        plan_id = plan.id

    print_success("Diet plan generated and saved!")

    with get_db() as db:
        plan = db.query(DietPlan).filter(DietPlan.id == plan_id).first()
        db.expunge(plan)

    display_ai_output(
        f"Diet Plan — {user.name} ({user.fitness_goal.value.replace('_', ' ').title()})",
        plan.plan_content
    )
    return plan


# ── View Plans ────────────────────────────────────────────────────────────────

def get_active_diet_plan(user_id: int) -> DietPlan | None:
    with get_db() as db:
        plan = db.query(DietPlan).filter(
            DietPlan.user_id == user_id,
            DietPlan.is_active == True
        ).first()
        if plan:
            db.expunge(plan)
        return plan


def view_diet_plan(user: User) -> None:
    plan = get_active_diet_plan(user.id)
    if plan:
        display_ai_output(f"Diet Plan — {user.name}", plan.plan_content)
    else:
        print_warning("No diet plan found. Generate one from the menu first.")


def view_grocery_list(user: User) -> None:
    plan = get_active_diet_plan(user.id)
    if plan and plan.grocery_list:
        display_ai_output(f"Grocery List — {user.name}", plan.grocery_list)
    elif plan:
        print_warning("No grocery list found. Regenerate your diet plan.")
    else:
        print_warning("No diet plan found. Generate one from the menu first.")
