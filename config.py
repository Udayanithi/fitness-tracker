"""
config.py — App-wide configuration
Loads environment variables and defines constants used across the project.
"""

import os
from dotenv import load_dotenv

# Load .env file into environment
load_dotenv()

# ── AI — Groq (free cloud API, ~5 second responses) ──────────────────────────
# Get a free key at: https://console.groq.com
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL   = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# ── Database ──────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:////tmp/fitness_coach.db"
)

# ── App Settings ──────────────────────────────────────────────────────────────
APP_NAME    = "AI Fitness Coach"
APP_VERSION = "1.0.0"
DEBUG       = os.getenv("DEBUG", "false").lower() == "true"

# ── BMI Thresholds ────────────────────────────────────────────────────────────
BMI_UNDERWEIGHT = 18.5
BMI_NORMAL_MAX  = 24.9
BMI_OVERWEIGHT  = 29.9
# >= 30 → Obese

# ── Activity Level Multipliers (Harris-Benedict) ──────────────────────────────
ACTIVITY_MULTIPLIERS = {
    "sedentary":        1.2,    # Desk job, no exercise
    "lightly_active":   1.375,  # Light exercise 1–3 days/week
    "moderately_active":1.55,   # Moderate exercise 3–5 days/week
    "very_active":      1.725,  # Hard exercise 6–7 days/week
    "extra_active":     1.9,    # Physical job + hard training
}

# ── Fitness Goals ─────────────────────────────────────────────────────────────
FITNESS_GOALS = ["fat_loss", "weight_gain", "muscle_gain", "maintenance"]

# ── Food Preferences ──────────────────────────────────────────────────────────
FOOD_PREFERENCES = ["veg", "non_veg", "vegan", "eggetarian"]
