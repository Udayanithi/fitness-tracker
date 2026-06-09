"""
app/modules/registration.py — User Registration Module

Responsibilities:
- Collect all user details via CLI prompts
- Validate every input before saving
- Check for duplicate email in DB
- Save new user to the database
- Allow viewing existing users and loading a user by email
"""

from app.database import get_db
from app.models import User, GenderEnum, FoodPrefEnum, FitnessGoalEnum
from app.utils import validators as v
from app.utils.display import (
    console, print_header, print_success, print_error,
    print_section, print_info, print_warning,
    ask, ask_choice, confirm, display_user_summary
)


# ── Internal helper: prompt with re-ask on validation failure ─────────────────

def _prompt(label: str, validator, default: str = "") -> str:
    """
    Repeatedly prompts the user until the input passes validation.
    Returns the cleaned, valid value.
    """
    while True:
        value = ask(label, default=default).strip()
        ok, msg = validator(value)
        if ok:
            return value
        print_error(msg)


# ── Registration Flow ─────────────────────────────────────────────────────────

def register_user() -> User | None:
    """
    Full CLI registration flow.
    Returns the saved User object, or None if the user cancelled.
    """
    print_header("📋 New User Registration", "Fill in your details to get started")

    # ── Personal Details ──────────────────────────────────────────────────────
    print_section("Personal Details")

    name   = _prompt("Full Name",        v.validate_name)
    age    = _prompt("Age",              v.validate_age)
    gender = ask_choice("Gender",        ["male", "female", "other"])
    address = ask("Address (optional)")
    email  = _prompt("Email Address",    v.validate_email)

    # Check duplicate email before continuing
    with get_db() as db:
        existing = db.query(User).filter(User.email == email.lower()).first()
        if existing:
            print_error(f"An account with email '{email}' already exists.")
            print_info("Use 'Load User' from the main menu to log in.")
            return None

    # ── Physical Details ──────────────────────────────────────────────────────
    print_section("Physical Details")

    height = _prompt("Height (cm) — e.g. 170",   v.validate_height)
    weight = _prompt("Current Weight (kg) — e.g. 65.5", v.validate_weight)

    # ── Lifestyle ─────────────────────────────────────────────────────────────
    print_section("Lifestyle Information")

    occupation     = ask("Occupation (e.g. Software Engineer)")
    work_schedule  = ask("Work Schedule (e.g. 9am–6pm weekdays)")
    sleep_schedule = ask("Sleep Schedule (e.g. 11pm–7am)")

    # ── Food & Fitness ────────────────────────────────────────────────────────
    print_section("Food & Fitness Preferences")

    food_pref = ask_choice(
        "Food Preference",
        ["veg", "non_veg", "vegan", "eggetarian"]
    )
    budget = _prompt(
        "Monthly Food Budget (₹) — e.g. 3000",
        v.validate_budget
    )
    fitness_goal = ask_choice(
        "Fitness Goal",
        ["fat_loss", "weight_gain", "muscle_gain", "maintenance"]
    )
    phone_number = ask("Phone Number (for reminders) — e.g. +919876543210 (optional)")

    # ── Confirmation ──────────────────────────────────────────────────────────
    print_section("Review Your Details")
    console.print(f"""
  [bold]Name:[/bold]           {name}
  [bold]Age / Gender:[/bold]   {age} / {gender}
  [bold]Email:[/bold]          {email}
  [bold]Height / Weight:[/bold]{height} cm / {weight} kg
  [bold]Occupation:[/bold]     {occupation or '—'}
  [bold]Food Preference:[/bold]{food_pref}
  [bold]Monthly Budget:[/bold] ₹{budget}
  [bold]Fitness Goal:[/bold]   {fitness_goal.replace('_', ' ').title()}
  [bold]Phone:[/bold]          {phone_number or '—'}
""")

    if not confirm("Save this profile?"):
        print_warning("Registration cancelled.")
        return None

    # ── Save to Database ──────────────────────────────────────────────────────
    user = User(
        name            = name.strip(),
        age             = int(age),
        gender          = GenderEnum(gender),
        address         = address.strip() or None,
        email           = email.lower().strip(),
        height_cm       = float(height),
        weight_kg       = float(weight),
        occupation      = occupation.strip() or None,
        work_schedule   = work_schedule.strip() or None,
        sleep_schedule  = sleep_schedule.strip() or None,
        food_preference = FoodPrefEnum(food_pref),
        monthly_budget  = float(budget),
        fitness_goal    = FitnessGoalEnum(fitness_goal),
        phone_number    = phone_number.strip() or None,
    )

    with get_db() as db:
        db.add(user)
        db.flush()          # Assigns user.id before commit
        user_id = user.id
        user_name = user.name

    print_success(f"Profile saved! Welcome, {user_name} (ID: {user_id}) 🎉")

    # Re-fetch and expunge so the object is usable outside any session
    with get_db() as db:
        saved_user = db.query(User).filter(User.id == user_id).first()
        db.expunge(saved_user)
    return saved_user


# ── Load Existing User ────────────────────────────────────────────────────────

def load_user_by_email() -> User | None:
    """
    Prompts for email and returns the matching User, or None if not found.
    """
    print_section("Load Existing Profile")
    email = ask("Enter your registered email").strip().lower()

    with get_db() as db:
        user = db.query(User).filter(
            User.email == email,
            User.is_active == True
        ).first()

        if not user:
            print_error(f"No active account found for '{email}'.")
            return None

        # Detach from session so it's usable after context manager closes
        db.expunge(user)

    print_success(f"Welcome back, {user.name}!")
    display_user_summary(user)
    return user


def load_user_by_id(user_id: int) -> User | None:
    """Returns a User by ID, or None."""
    with get_db() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            db.expunge(user)
        return user


# ── List All Users ────────────────────────────────────────────────────────────

def list_all_users() -> None:
    """Displays a summary table of all registered users."""
    from rich.table import Table
    from rich import box
    from app.utils.display import console

    with get_db() as db:
        users = db.query(User).filter(User.is_active == True).all()
        db.expunge_all()

    if not users:
        print_warning("No users registered yet.")
        return

    table = Table(title="Registered Users", box=box.ROUNDED, border_style="cyan")
    table.add_column("ID",     style="dim",        width=4)
    table.add_column("Name",   style="bold")
    table.add_column("Age",    style="cyan",        width=5)
    table.add_column("Gender", style="dim",         width=8)
    table.add_column("Goal",   style="bold yellow")
    table.add_column("Email",  style="dim")

    for u in users:
        table.add_row(
            str(u.id),
            u.name,
            str(u.age),
            u.gender.value,
            u.fitness_goal.value.replace("_", " ").title(),
            u.email,
        )

    console.print(table)


# ── Update Weight ─────────────────────────────────────────────────────────────

def update_user_weight(user_id: int) -> float | None:
    """
    Prompts for a new weight and updates the user record.
    Returns the new weight, or None if cancelled.
    """
    new_weight = _prompt("New Weight (kg)", v.validate_weight)

    if not confirm(f"Update weight to {new_weight} kg?"):
        return None

    with get_db() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            print_error("User not found.")
            return None
        user.weight_kg = float(new_weight)

    print_success(f"Weight updated to {new_weight} kg.")
    return float(new_weight)
