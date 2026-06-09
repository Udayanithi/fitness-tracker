"""
app/modules/progress.py — Progress Tracking System

Features:
- Log weight and body measurements (chest, waist, hips, arms, thighs)
- View full history in a table
- Weekly and monthly progress comparisons
- Progress report with trends (gain/loss vs starting point)
- BMI recalculation based on latest weight
"""

from datetime import date, timedelta
from app.database import get_db
from app.models import User, ProgressEntry
from app.utils.display import (
    console, print_section, print_success, print_error,
    print_info, print_warning
)
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.prompt import Prompt, FloatPrompt


# ── Log Entry ─────────────────────────────────────────────────────────────────

def log_progress(user: User) -> ProgressEntry | None:
    """Prompts user to enter today's measurements and saves to DB."""
    print_section("Log Today's Progress")

    # Check if already logged today
    with get_db() as db:
        existing = db.query(ProgressEntry).filter(
            ProgressEntry.user_id == user.id,
            ProgressEntry.entry_date == date.today()
        ).first()
        if existing:
            db.expunge(existing)

    if existing:
        print_warning(f"You already logged progress today ({date.today()}).")
        overwrite = Prompt.ask("Overwrite today's entry?", choices=["y", "n"], default="n")
        if overwrite != "y":
            return None
        with get_db() as db:
            db.query(ProgressEntry).filter(
                ProgressEntry.user_id == user.id,
                ProgressEntry.entry_date == date.today()
            ).delete()

    console.print("\n[bold cyan]── Enter Your Measurements ─────────────────────[/bold cyan]")
    console.print("[dim]Press Enter to skip optional measurements[/dim]\n")

    # Weight (required)
    weight = FloatPrompt.ask("  Current Weight (kg)")

    # Optional measurements
    def optional_float(label: str) -> float | None:
        val = Prompt.ask(f"  {label} (cm) [optional]", default="")
        try:
            return float(val) if val.strip() else None
        except ValueError:
            return None

    chest  = optional_float("Chest")
    waist  = optional_float("Waist")
    hips   = optional_float("Hips")
    arms   = optional_float("Arms (bicep)")
    thighs = optional_float("Thighs")
    notes  = Prompt.ask("  Notes (optional)", default="")

    # Save entry
    with get_db() as db:
        entry = ProgressEntry(
            user_id    = user.id,
            entry_date = date.today(),
            weight_kg  = weight,
            chest_cm   = chest,
            waist_cm   = waist,
            hips_cm    = hips,
            arms_cm    = arms,
            thighs_cm  = thighs,
            notes      = notes or None,
        )
        db.add(entry)
        db.flush()
        entry_id = entry.id

    with get_db() as db:
        entry = db.query(ProgressEntry).filter(ProgressEntry.id == entry_id).first()
        db.expunge(entry)

    print_success(f"Progress logged for {date.today()} — Weight: {weight} kg ✓")
    return entry


# ── Fetch Helpers ─────────────────────────────────────────────────────────────

def _get_all_entries(user_id: int) -> list[ProgressEntry]:
    with get_db() as db:
        entries = db.query(ProgressEntry).filter(
            ProgressEntry.user_id == user_id
        ).order_by(ProgressEntry.entry_date.asc()).all()
        for e in entries:
            db.expunge(e)
        return entries


def _get_entries_since(user_id: int, since: date) -> list[ProgressEntry]:
    with get_db() as db:
        entries = db.query(ProgressEntry).filter(
            ProgressEntry.user_id == user_id,
            ProgressEntry.entry_date >= since
        ).order_by(ProgressEntry.entry_date.asc()).all()
        for e in entries:
            db.expunge(e)
        return entries


# ── View History ──────────────────────────────────────────────────────────────

def view_progress_history(user: User) -> None:
    """Displays full measurement history in a table."""
    entries = _get_all_entries(user.id)

    if not entries:
        print_warning("No progress entries yet. Log your first entry with option 12.")
        return

    print_section(f"Progress History — {user.name}")

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
    table.add_column("Date",       style="dim",         width=12)
    table.add_column("Weight",     justify="right",     width=10)
    table.add_column("Chest",      justify="right",     width=9)
    table.add_column("Waist",      justify="right",     width=9)
    table.add_column("Hips",       justify="right",     width=9)
    table.add_column("Arms",       justify="right",     width=9)
    table.add_column("Thighs",     justify="right",     width=9)
    table.add_column("Notes",      width=20)

    def fmt(val, unit=""):
        return f"{val}{unit}" if val else "—"

    for e in entries:
        table.add_row(
            str(e.entry_date),
            fmt(e.weight_kg, " kg"),
            fmt(e.chest_cm,  " cm"),
            fmt(e.waist_cm,  " cm"),
            fmt(e.hips_cm,   " cm"),
            fmt(e.arms_cm,   " cm"),
            fmt(e.thighs_cm, " cm"),
            e.notes or "—",
        )

    console.print(table)
    console.print(f"\n  [dim]Total entries: {len(entries)}[/dim]")


# ── Progress Report ───────────────────────────────────────────────────────────

def _trend(current: float | None, start: float | None, unit: str = "kg") -> str:
    """Returns a colored trend string like +2.5 kg ↑ or -1.0 cm ↓"""
    if current is None or start is None:
        return "[dim]—[/dim]"
    diff = round(current - start, 1)
    if diff > 0:
        return f"[red]+{diff} {unit} ↑[/red]"
    elif diff < 0:
        return f"[green]{diff} {unit} ↓[/green]"
    else:
        return f"[yellow]0 {unit} →[/yellow]"


def _bmi(weight_kg: float, height_cm: float) -> float:
    return round(weight_kg / ((height_cm / 100) ** 2), 1)


def view_progress_report(user: User) -> None:
    """Generates a full progress report: weekly, monthly, all-time."""
    all_entries = _get_all_entries(user.id)

    if not all_entries:
        print_warning("No progress entries yet. Log your first entry with option 12.")
        return

    if len(all_entries) < 2:
        print_warning("Log at least 2 entries to see a progress report.")
        return

    print_section(f"Progress Report — {user.name}")

    first   = all_entries[0]
    latest  = all_entries[-1]
    today   = date.today()

    weekly_entries  = _get_entries_since(user.id, today - timedelta(days=7))
    monthly_entries = _get_entries_since(user.id, today - timedelta(days=30))

    week_start  = weekly_entries[0]  if len(weekly_entries)  >= 2 else None
    month_start = monthly_entries[0] if len(monthly_entries) >= 2 else None

    # ── All-time summary ──────────────────────────────────────────────────────
    bmi_start  = _bmi(first.weight_kg,  user.height_cm)
    bmi_latest = _bmi(latest.weight_kg, user.height_cm)

    all_time = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    all_time.add_column("Metric",  style="bold")
    all_time.add_column("Start",   justify="right")
    all_time.add_column("Current", justify="right")
    all_time.add_column("Change",  justify="right")

    all_time.add_row("Weight",  f"{first.weight_kg} kg",  f"{latest.weight_kg} kg",  _trend(latest.weight_kg, first.weight_kg, "kg"))
    all_time.add_row("BMI",     str(bmi_start),            str(bmi_latest),            _trend(bmi_latest, bmi_start, ""))
    all_time.add_row("Chest",   f"{first.chest_cm or '—'} cm",  f"{latest.chest_cm or '—'} cm",  _trend(latest.chest_cm, first.chest_cm, "cm"))
    all_time.add_row("Waist",   f"{first.waist_cm or '—'} cm",  f"{latest.waist_cm or '—'} cm",  _trend(latest.waist_cm, first.waist_cm, "cm"))
    all_time.add_row("Hips",    f"{first.hips_cm or '—'} cm",   f"{latest.hips_cm or '—'} cm",   _trend(latest.hips_cm, first.hips_cm, "cm"))
    all_time.add_row("Arms",    f"{first.arms_cm or '—'} cm",   f"{latest.arms_cm or '—'} cm",   _trend(latest.arms_cm, first.arms_cm, "cm"))
    all_time.add_row("Thighs",  f"{first.thighs_cm or '—'} cm", f"{latest.thighs_cm or '—'} cm", _trend(latest.thighs_cm, first.thighs_cm, "cm"))

    days_tracked = (latest.entry_date - first.entry_date).days
    console.print(Panel(
        all_time,
        title=f"[bold]All-Time Progress  ({first.entry_date} → {latest.entry_date}, {days_tracked} days)[/bold]",
        border_style="cyan"
    ))

    # ── Weekly summary ────────────────────────────────────────────────────────
    if week_start:
        wt = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
        wt.add_column("Metric", style="bold")
        wt.add_column("7 Days Ago", justify="right")
        wt.add_column("Today",      justify="right")
        wt.add_column("Change",     justify="right")
        wt.add_row("Weight", f"{week_start.weight_kg} kg", f"{latest.weight_kg} kg",
                   _trend(latest.weight_kg, week_start.weight_kg, "kg"))
        wt.add_row("Waist",  f"{week_start.waist_cm or '—'} cm", f"{latest.waist_cm or '—'} cm",
                   _trend(latest.waist_cm, week_start.waist_cm, "cm"))
        console.print(Panel(wt, title="[bold]Weekly Progress (Last 7 Days)[/bold]", border_style="green"))
    else:
        print_info("Not enough data for weekly comparison yet (need entries spanning 7+ days).")

    # ── Monthly summary ───────────────────────────────────────────────────────
    if month_start and month_start.entry_date != first.entry_date:
        mt = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
        mt.add_column("Metric", style="bold")
        mt.add_column("30 Days Ago", justify="right")
        mt.add_column("Today",       justify="right")
        mt.add_column("Change",      justify="right")
        mt.add_row("Weight", f"{month_start.weight_kg} kg", f"{latest.weight_kg} kg",
                   _trend(latest.weight_kg, month_start.weight_kg, "kg"))
        mt.add_row("Waist",  f"{month_start.waist_cm or '—'} cm", f"{latest.waist_cm or '—'} cm",
                   _trend(latest.waist_cm, month_start.waist_cm, "cm"))
        console.print(Panel(mt, title="[bold]Monthly Progress (Last 30 Days)[/bold]", border_style="yellow"))

    # ── Goal alignment tip ────────────────────────────────────────────────────
    console.print()
    weight_change = round(latest.weight_kg - first.weight_kg, 1)
    goal = user.fitness_goal.value

    if goal == "fat_loss" and weight_change < 0:
        console.print(f"  ✅ [green]Great work! You've lost {abs(weight_change)} kg towards your fat loss goal.[/green]")
    elif goal == "fat_loss" and weight_change > 0:
        console.print(f"  ⚠️  [yellow]Weight increased by {weight_change} kg. Review your diet plan.[/yellow]")
    elif goal in ("muscle_gain", "weight_gain") and weight_change > 0:
        console.print(f"  ✅ [green]You've gained {weight_change} kg — on track for your {goal.replace('_',' ')} goal![/green]")
    elif goal in ("muscle_gain", "weight_gain") and weight_change < 0:
        console.print(f"  ⚠️  [yellow]Weight dropped by {abs(weight_change)} kg. Increase calorie intake.[/yellow]")
    else:
        console.print(f"  ℹ️  [cyan]Weight change: {weight_change:+} kg since you started.[/cyan]")
    console.print()
