"""
tests/test_api.py — Full API test suite

Covers:
- User registration, login, listing, weight update
- Health analysis (calculations verified)
- Workout + diet plan endpoints (mocked AI)
- Progress logging and reports
- Error cases (404, 409, 422)

Run with:
    pytest tests/ -v
    pytest tests/ -v --tb=short   (shorter tracebacks)
"""

import pytest
from unittest.mock import patch


# ══════════════════════════════════════════════════════
# USERS
# ══════════════════════════════════════════════════════

class TestUsers:

    def test_register_success(self, client):
        """POST /users/register — new user created."""
        import time
        payload = {
            "name": "Aadhi Test", "age": 22, "gender": "male",
            "email": f"aadhi_{int(time.time())}@pytest.com",
            "height_cm": 180.0, "weight_kg": 75.0,
            "food_preference": "veg", "monthly_budget": 8000.0,
            "fitness_goal": "fat_loss",
        }
        res = client.post("/users/register", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "Aadhi Test"
        assert data["id"] is not None

    def test_register_duplicate_email(self, client, registered_user):
        """POST /users/register — duplicate email returns 409."""
        payload = {
            "name": "Duplicate", "age": 22, "gender": "male",
            "email": registered_user["email"],  # same email
            "height_cm": 170.0, "weight_kg": 65.0,
            "food_preference": "veg", "monthly_budget": 3000.0,
            "fitness_goal": "fat_loss",
        }
        res = client.post("/users/register", json=payload)
        assert res.status_code == 409
        assert "already registered" in res.json()["detail"]

    def test_register_invalid_age(self, client):
        """POST /users/register — age out of range returns 422."""
        payload = {
            "name": "Young", "age": 2, "gender": "male",
            "email": "young@pytest.com",
            "height_cm": 170.0, "weight_kg": 65.0,
            "food_preference": "veg", "monthly_budget": 3000.0,
            "fitness_goal": "fat_loss",
        }
        res = client.post("/users/register", json=payload)
        assert res.status_code == 422

    def test_register_invalid_goal(self, client):
        """POST /users/register — invalid fitness_goal returns 422."""
        payload = {
            "name": "Bad Goal", "age": 25, "gender": "male",
            "email": "badgoal@pytest.com",
            "height_cm": 170.0, "weight_kg": 65.0,
            "food_preference": "veg", "monthly_budget": 3000.0,
            "fitness_goal": "fly_to_moon",   # invalid
        }
        res = client.post("/users/register", json=payload)
        assert res.status_code == 422

    def test_login_success(self, client, registered_user):
        """POST /users/login — valid email returns user."""
        res = client.post("/users/login", params={"email": registered_user["email"]})
        assert res.status_code == 200
        assert res.json()["id"] == registered_user["id"]

    def test_login_not_found(self, client):
        """POST /users/login — unknown email returns 404."""
        res = client.post("/users/login", params={"email": "nobody@doesnotexist.com"})
        assert res.status_code == 404

    def test_list_users(self, client):
        """GET /users/ — returns list with total."""
        res = client.get("/users/")
        assert res.status_code == 200
        data = res.json()
        assert "users" in data
        assert "total" in data
        assert data["total"] >= 1

    def test_get_user_by_id(self, client, registered_user):
        """GET /users/{id} — returns correct user."""
        res = client.get(f"/users/{registered_user['id']}")
        assert res.status_code == 200
        assert res.json()["email"] == registered_user["email"]

    def test_get_user_not_found(self, client):
        """GET /users/99999 — returns 404."""
        res = client.get("/users/99999")
        assert res.status_code == 404

    def test_update_weight(self, client, registered_user):
        """PUT /users/{id}/weight — updates weight."""
        res = client.put(f"/users/{registered_user['id']}/weight", params={"weight_kg": 70.5})
        assert res.status_code == 200
        assert res.json()["success"] is True

    def test_update_weight_invalid(self, client, registered_user):
        """PUT /users/{id}/weight — invalid weight returns 422."""
        res = client.put(f"/users/{registered_user['id']}/weight", params={"weight_kg": 5.0})
        assert res.status_code == 422


# ══════════════════════════════════════════════════════
# HEALTH ANALYSIS
# ══════════════════════════════════════════════════════

class TestHealth:

    def test_analyze_health(self, client, registered_user):
        """POST /health/{id}/analyze — calculates and saves health profile."""
        res = client.post(f"/health/{registered_user['id']}/analyze")
        assert res.status_code == 200
        data = res.json()
        assert data["bmi"] is not None
        assert data["bmr"] is not None
        assert data["tdee"] is not None
        assert data["target_calories"] is not None
        assert data["bmi_category"] in ["Underweight", "Normal", "Overweight", "Obese"]

    def test_bmi_value_correct(self, client, registered_user):
        """BMI calculation: 72kg / 1.75m² = 23.5 (approx)."""
        res = client.post(f"/health/{registered_user['id']}/analyze")
        data = res.json()
        # Weight 72, height 175 → BMI = 72 / (1.75)² ≈ 23.5
        assert 20 <= data["bmi"] <= 27, f"BMI {data['bmi']} out of expected range"

    def test_target_calories_muscle_gain(self, client, registered_user):
        """Muscle gain → target = TDEE + 200 kcal surplus."""
        res = client.post(f"/health/{registered_user['id']}/analyze")
        data = res.json()
        diff = data["target_calories"] - data["tdee"]
        assert 150 <= diff <= 250, f"Expected +200 surplus, got {diff}"

    def test_get_health_profile(self, client, registered_user):
        """GET /health/{id} — returns saved profile."""
        res = client.get(f"/health/{registered_user['id']}")
        assert res.status_code == 200
        assert res.json()["user_id"] == registered_user["id"]

    def test_get_health_not_found(self, client):
        """GET /health/99999 — returns 404."""
        res = client.get("/health/99999")
        assert res.status_code == 404

    def test_macros_present(self, client, registered_user):
        """Health profile contains all macro targets."""
        res = client.get(f"/health/{registered_user['id']}")
        data = res.json()
        assert data["protein_g"] > 0
        assert data["carbs_g"] > 0
        assert data["fat_g"] > 0


# ══════════════════════════════════════════════════════
# AI PLANS — Mocked (no real API call in tests)
# ══════════════════════════════════════════════════════

MOCK_WORKOUT = "## Day 1 — Push\nBench Press: 4×8\nShoulder Press: 3×10\n\n## Day 2 — Rest\n"
MOCK_DIET    = "## Monday\nBreakfast: Oats 80g, Eggs 3\nLunch: Rice 150g, Chicken 150g\n"
MOCK_GROCERY = "## Grocery List\n- Oats: 1kg — ₹80\n- Chicken: 2kg — ₹300\n"


class TestPlans:

    @patch("app.modules.ai_engine._call_groq", return_value=MOCK_WORKOUT)
    def test_generate_workout_plan(self, mock_groq, client, registered_user):
        """POST /plans/{id}/workout — generates and saves plan."""
        # Pre-delete existing plan to avoid CLI prompt
        from app.database import get_db
        from app.models import WorkoutPlan
        with get_db() as db:
            db.query(WorkoutPlan).filter(WorkoutPlan.user_id == registered_user["id"]).delete()
        res = client.post(f"/plans/{registered_user['id']}/workout")
        assert res.status_code == 200
        data = res.json()
        assert data["is_active"] is True
        assert data["user_id"] == registered_user["id"]

    @patch("app.modules.ai_engine._call_groq", return_value=MOCK_WORKOUT)
    def test_get_workout_plan(self, mock_groq, client, registered_user):
        """GET /plans/{id}/workout — retrieves saved plan."""
        res = client.get(f"/plans/{registered_user['id']}/workout")
        assert res.status_code == 200
        assert res.json()["plan_content"] is not None

    def test_get_workout_plan_missing_health(self, client):
        """POST /plans/99999/workout — user not found returns 404."""
        res = client.post("/plans/99999/workout")
        assert res.status_code == 404

    @patch("app.modules.diet._call_groq", side_effect=[MOCK_DIET, MOCK_GROCERY])
    def test_generate_diet_plan(self, mock_groq, client, registered_user):
        """POST /plans/{id}/diet — generates and saves diet plan."""
        from app.database import get_db
        from app.models import DietPlan
        with get_db() as db:
            db.query(DietPlan).filter(DietPlan.user_id == registered_user["id"]).delete()
        res = client.post(f"/plans/{registered_user['id']}/diet")
        assert res.status_code == 200
        data = res.json()
        assert data["plan_content"] is not None
        assert data["is_active"] is True

    @patch("app.modules.diet._call_groq", side_effect=[MOCK_DIET, MOCK_GROCERY])
    def test_get_diet_plan(self, mock_groq, client, registered_user):
        """GET /plans/{id}/diet — retrieves saved diet plan."""
        res = client.get(f"/plans/{registered_user['id']}/diet")
        assert res.status_code == 200

    def test_get_grocery_list(self, client, registered_user):
        """GET /plans/{id}/grocery — returns grocery list."""
        res = client.get(f"/plans/{registered_user['id']}/grocery")
        assert res.status_code in (200, 404)  # 404 if no diet plan yet


# ══════════════════════════════════════════════════════
# PROGRESS
# ══════════════════════════════════════════════════════

class TestProgress:

    def test_log_progress_entry(self, client, registered_user):
        """POST /progress/{id} — logs weight entry."""
        payload = {
            "weight_kg": 71.5,
            "chest_cm":  95.0,
            "waist_cm":  82.0,
            "notes":     "Feeling great!",
        }
        res = client.post(f"/progress/{registered_user['id']}", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["weight_kg"] == 71.5
        assert data["notes"] == "Feeling great!"

    def test_log_second_entry(self, client, registered_user):
        """Log a second entry so report can be generated."""
        payload = {"weight_kg": 70.8, "waist_cm": 81.0}
        res = client.post(f"/progress/{registered_user['id']}", json=payload)
        assert res.status_code == 201

    def test_log_invalid_weight(self, client, registered_user):
        """POST /progress — weight too low returns 422."""
        res = client.post(f"/progress/{registered_user['id']}", json={"weight_kg": 10.0})
        assert res.status_code == 422

    def test_get_progress_history(self, client, registered_user):
        """GET /progress/{id} — returns all entries."""
        res = client.get(f"/progress/{registered_user['id']}")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 1
        assert len(data["entries"]) >= 1

    def test_get_progress_report(self, client, registered_user):
        """GET /progress/{id}/report — returns comparison report."""
        res = client.get(f"/progress/{registered_user['id']}/report")
        assert res.status_code == 200
        data = res.json()
        assert "all_time" in data
        assert data["all_time"]["change"] is not None

    def test_progress_report_not_enough_data(self, client):
        """GET /progress/new_user/report — needs 2+ entries."""
        import time
        payload = {
            "name": "Fresh User", "age": 30, "gender": "female",
            "email": f"fresh_{int(time.time())}@pytest.com",
            "height_cm": 162.0, "weight_kg": 58.0,
            "food_preference": "veg", "monthly_budget": 3000.0,
            "fitness_goal": "maintenance",
        }
        reg = client.post("/users/register", json=payload)
        uid = reg.json()["id"]
        res = client.get(f"/progress/{uid}/report")
        assert res.status_code == 400


# ══════════════════════════════════════════════════════
# ROOT / HEALTH CHECK
# ══════════════════════════════════════════════════════

class TestHealthCheck:

    def test_root_endpoint(self, client):
        """GET / — API is running."""
        res = client.get("/")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "running"
        assert "docs" in data
