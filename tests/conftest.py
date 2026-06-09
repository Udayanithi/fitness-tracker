"""
tests/conftest.py — Pytest configuration and fixtures

Sets up a fresh in-memory SQLite database for each test session
so tests never touch the real data/fitness_coach.db.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ── Use in-memory SQLite for tests ────────────────────
TEST_DB_URL = "sqlite:///./test_temp.db"

os.environ["DATABASE_URL_OVERRIDE"] = TEST_DB_URL

from app.database import Base
from api.app import app

# Override the engine for tests
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
Base.metadata.create_all(bind=test_engine)


@pytest.fixture(scope="session")
def client():
    """FastAPI test client — reused across the whole test session."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def registered_user(client):
    """Register a test user once and reuse across tests."""
    payload = {
        "name":           "Test User",
        "age":            25,
        "gender":         "male",
        "email":          "testuser@pytest.com",
        "height_cm":      175.0,
        "weight_kg":      72.0,
        "occupation":     "Software Engineer",
        "work_schedule":  "9am-6pm",
        "sleep_schedule": "11pm-7am",
        "food_preference":"non_veg",
        "monthly_budget": 5000.0,
        "fitness_goal":   "muscle_gain",
        "phone_number":   "+919876543210",
    }
    # Register (or re-login if already exists)
    res = client.post("/users/register", json=payload)
    if res.status_code == 409:
        # Already registered — login
        res = client.post("/users/login", params={"email": payload["email"]})
    assert res.status_code in (200, 201)
    return res.json()
