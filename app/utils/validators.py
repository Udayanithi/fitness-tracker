"""
app/utils/validators.py — Input validation helpers

All validation functions return (is_valid: bool, error_message: str).
Used by the registration module to validate CLI inputs before saving to DB.
"""

import re
from config import FITNESS_GOALS, FOOD_PREFERENCES


def validate_name(name: str) -> tuple[bool, str]:
    name = name.strip()
    if len(name) < 2:
        return False, "Name must be at least 2 characters."
    if not re.match(r"^[A-Za-z\s]+$", name):
        return False, "Name can only contain letters and spaces."
    return True, ""


def validate_age(age_str: str) -> tuple[bool, str]:
    try:
        age = int(age_str)
        if not (5 <= age <= 120):
            return False, "Age must be between 5 and 120."
        return True, ""
    except ValueError:
        return False, "Age must be a whole number."


def validate_gender(gender_str: str) -> tuple[bool, str]:
    valid = ["male", "female", "other"]
    if gender_str.lower() not in valid:
        return False, f"Gender must be one of: {', '.join(valid)}"
    return True, ""


def validate_email(email: str) -> tuple[bool, str]:
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w{2,}$"
    if not re.match(pattern, email.strip()):
        return False, "Please enter a valid email address."
    return True, ""


def validate_height(height_str: str) -> tuple[bool, str]:
    try:
        h = float(height_str)
        if not (50 <= h <= 300):
            return False, "Height must be between 50 cm and 300 cm."
        return True, ""
    except ValueError:
        return False, "Height must be a number (e.g. 170.5)."


def validate_weight(weight_str: str) -> tuple[bool, str]:
    try:
        w = float(weight_str)
        if not (20 <= w <= 500):
            return False, "Weight must be between 20 kg and 500 kg."
        return True, ""
    except ValueError:
        return False, "Weight must be a number (e.g. 65.5)."


def validate_budget(budget_str: str) -> tuple[bool, str]:
    try:
        b = float(budget_str)
        if b < 500:
            return False, "Monthly food budget must be at least ₹500."
        return True, ""
    except ValueError:
        return False, "Budget must be a number (e.g. 3000)."


def validate_food_preference(pref: str) -> tuple[bool, str]:
    if pref.lower() not in FOOD_PREFERENCES:
        return False, f"Food preference must be one of: {', '.join(FOOD_PREFERENCES)}"
    return True, ""


def validate_fitness_goal(goal: str) -> tuple[bool, str]:
    if goal.lower() not in FITNESS_GOALS:
        return False, f"Fitness goal must be one of: {', '.join(FITNESS_GOALS)}"
    return True, ""


def validate_time_str(time_str: str) -> tuple[bool, str]:
    """Validates HH:MM 24-hour format."""
    pattern = r"^([01]\d|2[0-3]):([0-5]\d)$"
    if not re.match(pattern, time_str.strip()):
        return False, "Time must be in HH:MM format (e.g. 07:30)."
    return True, ""


def validate_phone(phone: str) -> tuple[bool, str]:
    """Validates international phone number format."""
    phone = phone.strip()
    if not phone:
        return True, ""   # Optional field
    pattern = r"^\+?[1-9]\d{9,14}$"
    if not re.match(pattern, phone.replace(" ", "").replace("-", "")):
        return False, "Phone must be in format +919876543210 (10-15 digits)."
    return True, ""
