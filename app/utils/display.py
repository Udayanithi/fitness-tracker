"""
app/utils/display.py — CLI display helpers using the Rich library

Rich gives us beautiful terminal output: colored tables, panels,
progress bars, and formatted text. This module centralizes all
display logic so other modules stay clean.
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.prompt import Prompt, Confirm

console = Console()


# ── Generic Helpers ───────────────────────────────────────────────────────────

def print_header(title: str, subtitle: str = ""):
    """Prints a styled app header panel."""
    content = f"[bold cyan]{title}[/bold cyan]"
    if subtitle:
        content += f"\n[dim]{subtitle}[/dim]"
    console.print(Panel(content, box=box.DOUBLE, border_style="cyan", expand=False))


def print_success(msg: str):
    console.print(f"[bold green]✓[/bold green] {msg}")


def print_error(msg: str):
    console.print(f"[bold red]✗[/bold red] {msg}")


def print_warning(msg: str):
    console.print(f"[bold yellow]⚠[/bold yellow] {msg}")


def print_info(msg: str):
    console.print(f"[bold blue]ℹ[/bold blue] {msg}")


def print_section(title: str):
    """Prints a section divider."""
    console.print(f"\n[bold magenta]── {title} {'─' * (40 - len(title))}[/bold magenta]")


def ask(prompt: str, default: str = "") -> str:
    """Prompts the user for input with optional default."""
    if default:
        return Prompt.ask(f"[cyan]{prompt}[/cyan]", default=default)
    return Prompt.ask(f"[cyan]{prompt}[/cyan]")


def ask_choice(prompt: str, choices: list[str]) -> str:
    """Prompts user to pick from a list of choices."""
    choices_str = " / ".join(f"[bold]{c}[/bold]" for c in choices)
    console.print(f"[cyan]{prompt}[/cyan] ({choices_str})")
    while True:
        value = Prompt.ask("  →").strip().lower()
        if value in [c.lower() for c in choices]:
            return value
        print_error(f"Please enter one of: {', '.join(choices)}")


def confirm(prompt: str) -> bool:
    return Confirm.ask(f"[cyan]{prompt}[/cyan]")


# ── Specific Display Functions ────────────────────────────────────────────────

def display_user_summary(user) -> None:
    """Displays a summary table of a registered user."""
    table = Table(title=f"User Profile — {user.name}", box=box.ROUNDED,
                  border_style="cyan", show_header=False)
    table.add_column("Field",  style="dim", width=22)
    table.add_column("Value",  style="bold")

    rows = [
        ("Name",           user.name),
        ("Age",            str(user.age)),
        ("Gender",         user.gender.value),
        ("Email",          user.email),
        ("Height",         f"{user.height_cm} cm"),
        ("Weight",         f"{user.weight_kg} kg"),
        ("Occupation",     user.occupation or "—"),
        ("Work Schedule",  user.work_schedule or "—"),
        ("Sleep Schedule", user.sleep_schedule or "—"),
        ("Food Preference",user.food_preference.value),
        ("Monthly Budget", f"₹{user.monthly_budget:.0f}"),
        ("Fitness Goal",   user.fitness_goal.value.replace("_", " ").title()),
        ("Phone",          getattr(user, "phone_number", None) or "—"),
    ]
    for field, value in rows:
        table.add_row(field, value)

    console.print(table)


def display_health_profile(hp, user_name: str) -> None:
    """Displays calculated health metrics in a table."""
    table = Table(title=f"Health Analysis — {user_name}", box=box.ROUNDED,
                  border_style="green", show_header=False)
    table.add_column("Metric",  style="dim", width=28)
    table.add_column("Value",   style="bold")

    # Color-code BMI category
    bmi_color = {
        "Underweight": "blue",
        "Normal": "green",
        "Overweight": "yellow",
        "Obese": "red",
    }.get(hp.bmi_category, "white")

    rows = [
        ("BMI",                    f"{hp.bmi:.1f}"),
        ("BMI Category",           f"[{bmi_color}]{hp.bmi_category}[/{bmi_color}]"),
        ("Body Fat %",             f"{hp.body_fat_percentage:.1f}%"),
        ("BMR (Base Calories)",    f"{hp.bmr:.0f} kcal/day"),
        ("TDEE (Total Calories)",  f"{hp.tdee:.0f} kcal/day"),
        ("Activity Level",         hp.activity_level.replace("_", " ").title()),
        ("Fitness Level",          hp.fitness_level.value.title()),
        ("Target Calories",        f"[bold cyan]{hp.target_calories:.0f} kcal/day[/bold cyan]"),
        ("Daily Protein Target",   f"{hp.protein_g:.0f} g"),
        ("Daily Carbs Target",     f"{hp.carbs_g:.0f} g"),
        ("Daily Fat Target",       f"{hp.fat_g:.0f} g"),
    ]
    for field, value in rows:
        table.add_row(field, value)

    console.print(table)


def display_progress_table(entries: list) -> None:
    """Displays a progress tracking table."""
    if not entries:
        print_warning("No progress entries found.")
        return

    table = Table(title="Progress Tracker", box=box.SIMPLE_HEAVY, border_style="magenta")
    table.add_column("Date",       style="dim")
    table.add_column("Weight (kg)",style="bold cyan")
    table.add_column("Chest (cm)", style="green")
    table.add_column("Waist (cm)", style="green")
    table.add_column("Hips (cm)",  style="green")
    table.add_column("Arms (cm)",  style="green")
    table.add_column("Notes",      style="dim")

    for e in entries:
        table.add_row(
            str(e.entry_date),
            str(e.weight_kg),
            str(e.chest_cm  or "—"),
            str(e.waist_cm  or "—"),
            str(e.hips_cm   or "—"),
            str(e.arms_cm   or "—"),
            e.notes or "—",
        )
    console.print(table)


def display_ai_output(title: str, content: str) -> None:
    """Displays AI-generated content in a styled panel."""
    console.print(Panel(
        content,
        title=f"[bold cyan]{title}[/bold cyan]",
        border_style="cyan",
        box=box.ROUNDED,
        padding=(1, 2),
    ))


def display_reminders_table(reminders: list) -> None:
    """Displays all reminders in a table."""
    if not reminders:
        print_warning("No reminders set.")
        return

    table = Table(title="Your Reminders", box=box.SIMPLE_HEAVY, border_style="yellow")
    table.add_column("ID",     style="dim",       width=4)
    table.add_column("Type",   style="bold yellow")
    table.add_column("Title",  style="bold")
    table.add_column("Time",   style="cyan")
    table.add_column("Days",   style="dim")
    table.add_column("Active", style="green")

    for r in reminders:
        table.add_row(
            str(r.id),
            r.reminder_type.value.title(),
            r.title,
            r.time_str,
            r.days_of_week,
            "✓" if r.is_active else "✗",
        )
    console.print(table)
