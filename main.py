"""
main.py — CLI Entry Point for AI Fitness Coach
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import init_db
from app.utils.display import (
    console, print_header, print_success, print_warning,
    display_user_summary, display_health_profile
)
from app.modules.registration import register_user, load_user_by_email, list_all_users
from app.modules.health import run_health_analysis, get_health_profile
from app.modules.ai_engine import generate_workout_plan, view_workout_plan
from app.modules.diet import generate_diet_plan, view_diet_plan, view_grocery_list
from app.modules.progress import log_progress, view_progress_history, view_progress_report
from app.modules.reminders import reminder_menu, send_test_notification, start_scheduler
from config import APP_NAME, APP_VERSION

current_user   = None
current_health = None


def main_menu() -> str:
    console.print("\n[bold cyan]── Main Menu " + "─" * 30 + "[/bold cyan]")
    if current_user:
        console.print(f"  Logged in as: [bold green]{current_user.name}[/bold green]  |  Goal: [yellow]{current_user.fitness_goal.value.replace('_',' ').title()}[/yellow]\n")

    sections = [
        ("── Account", [
            ("1",  "Register New User"),
            ("2",  "Load Existing User"),
            ("3",  "List All Users"),
            ("4",  "View My Profile"),
        ]),
        ("── Health", [
            ("5",  "Run Health Analysis"),
            ("6",  "View Health Report"),
        ]),
        ("── AI Plans", [
            ("7",  "Generate Workout Plan  🤖"),
            ("8",  "View Workout Plan"),
            ("9",  "Generate Diet Plan    🥗"),
            ("10", "View Diet Plan"),
            ("11", "View Grocery List     🛒"),
        ]),
        ("── Progress", [
            ("12", "Log Today's Progress  📝"),
            ("13", "View Progress History 📋"),
            ("14", "View Progress Report  📊"),
        ]),
        ("── Reminders", [
            ("15", "Manage Reminders      🔔"),
            ("16", "Send Test Notification📧"),
        ]),
        ("── App", [
            ("0",  "Exit"),
        ]),
    ]

    for section_title, items in sections:
        console.print(f"  [dim]{section_title}[/dim]")
        for key, label in items:
            console.print(f"    [bold cyan]{key:>2}[/bold cyan]  {label}")
        console.print()

    from rich.prompt import Prompt
    all_keys = [k for _, items in sections for k, _ in items]
    return Prompt.ask("  Select option", choices=all_keys)


def require_login() -> bool:
    if not current_user:
        print_warning("Please register or load a user first (options 1 or 2).")
        return False
    return True


def require_health() -> bool:
    if not current_health:
        print_warning("Run Health Analysis first (option 5).")
        return False
    return True


def main():
    global current_user, current_health

    print_header(f"🏋️  {APP_NAME}", f"v{APP_VERSION} — Your Personal AI Fitness Coach")
    init_db()
    print_success("Database ready.\n")

    while True:
        choice = main_menu()

        if choice == "1":
            user = register_user()
            if user:
                current_user   = user
                current_health = get_health_profile(user.id)
                start_scheduler()

        elif choice == "2":
            user = load_user_by_email()
            if user:
                current_user   = user
                current_health = get_health_profile(user.id)
                start_scheduler()

        elif choice == "3":
            list_all_users()

        elif choice == "4":
            if require_login():
                display_user_summary(current_user)

        elif choice == "5":
            if require_login():
                current_health = run_health_analysis(current_user)

        elif choice == "6":
            if require_login():
                if current_health:
                    display_health_profile(current_health, current_user.name)
                else:
                    print_warning("No health analysis yet. Run option 5 first.")

        elif choice == "7":
            if require_login() and require_health():
                generate_workout_plan(current_user, current_health)

        elif choice == "8":
            if require_login():
                view_workout_plan(current_user)

        elif choice == "9":
            if require_login() and require_health():
                generate_diet_plan(current_user, current_health)

        elif choice == "10":
            if require_login():
                view_diet_plan(current_user)

        elif choice == "11":
            if require_login():
                view_grocery_list(current_user)

        elif choice == "12":
            if require_login():
                log_progress(current_user)

        elif choice == "13":
            if require_login():
                view_progress_history(current_user)

        elif choice == "14":
            if require_login():
                view_progress_report(current_user)

        elif choice == "15":
            if require_login():
                reminder_menu(current_user)

        elif choice == "16":
            if require_login():
                send_test_notification(current_user)

        elif choice == "0":
            console.print("\n[bold cyan]Goodbye! Stay fit 💪[/bold cyan]\n")
            break


if __name__ == "__main__":
    main()
