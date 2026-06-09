"""
app/modules/reminders.py — Reminder System (SMS + Email)

Features:
- Send reminders via Email (Gmail SMTP) and SMS (Twilio)
- Sends to ALL active users in the database at scheduled times
- Reminder types: meal, workout, water, custom
- Background scheduler runs every minute checking due reminders
- Fully configurable via .env

Requirements (add to .env):
    GMAIL_ADDRESS=your@gmail.com
    GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx   (Google App Password)
    TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxx
    TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxx
    TWILIO_FROM_NUMBER=+1xxxxxxxxxx
"""

import os
import smtplib
import threading
import time
from datetime import datetime, time as dtime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.database import get_db
from app.models import User, Reminder, ReminderTypeEnum


def _cli():
    """Lazy-load CLI utilities only when needed (not at API startup)."""
    from app.utils.display import (
        console, print_section, print_success, print_error,
        print_info, print_warning, ask, ask_choice, confirm,
        display_reminders_table
    )
    from app.utils.validators import validate_time_str
    from rich.prompt import Prompt
    from rich.console import Console
    import types
    m = types.SimpleNamespace(
        console=console, print_section=print_section,
        print_success=print_success, print_error=print_error,
        print_info=print_info, print_warning=print_warning,
        ask=ask, ask_choice=ask_choice, confirm=confirm,
        display_reminders_table=display_reminders_table,
        validate_time_str=validate_time_str, Prompt=Prompt,
    )
    return m


# ── Load credentials from .env ────────────────────────────────────────────────

GMAIL_ADDRESS      = os.getenv("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
TWILIO_SID         = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_TOKEN       = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM        = os.getenv("TWILIO_FROM_NUMBER", "")


# ── Email Sender ──────────────────────────────────────────────────────────────

def send_email(to_email: str, subject: str, body: str) -> bool:
    """
    Send an email via Gmail SMTP.
    Requires GMAIL_ADDRESS and GMAIL_APP_PASSWORD in .env.
    Returns True on success, False on failure.
    """
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        print("[Email] GMAIL_ADDRESS or GMAIL_APP_PASSWORD not configured in .env")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = GMAIL_ADDRESS
        msg["To"]      = to_email

        # Plain text version
        text_part = MIMEText(body, "plain")
        # HTML version with basic styling
        html_body = f"""
        <html><body style="font-family:Arial,sans-serif;padding:20px;background:#f4f4f4">
          <div style="background:white;padding:24px;border-radius:8px;max-width:500px;margin:auto">
            <h2 style="color:#4CAF50">🏋️ AI Fitness Coach</h2>
            <p style="font-size:16px;color:#333">{body.replace(chr(10), '<br>')}</p>
            <hr style="border:none;border-top:1px solid #eee">
            <p style="font-size:12px;color:#999">Stay consistent. Stay strong! 💪</p>
          </div>
        </body></html>
        """
        html_part = MIMEText(html_body, "html")
        msg.attach(text_part)
        msg.attach(html_part)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, to_email, msg.as_string())

        return True

    except smtplib.SMTPAuthenticationError:
        print("[Email] Authentication failed. Check your Gmail App Password in .env")
        return False
    except Exception as e:
        print(f"[Email] Failed to send: {e}")
        return False


# ── SMS Sender ────────────────────────────────────────────────────────────────

def send_sms(to_number: str, message: str) -> bool:
    """
    Send an SMS via Twilio.
    Requires TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER in .env.
    Returns True on success, False on failure.
    """
    if not all([TWILIO_SID, TWILIO_TOKEN, TWILIO_FROM]):
        print("[SMS] Twilio credentials not configured in .env")
        return False

    if not to_number:
        print("[SMS] User has no phone number registered.")
        return False

    try:
        from twilio.rest import Client
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        client.messages.create(
            body = message,
            from_ = TWILIO_FROM,
            to   = to_number,
        )
        return True
    except ImportError:
        print("[SMS] Twilio not installed. Run: pip install twilio")
        return False
    except Exception as e:
        print(f"[SMS] Failed to send to {to_number}: {e}")
        return False


# ── Send Reminder to All Users ────────────────────────────────────────────────

def _broadcast_reminder(reminder: Reminder) -> None:
    """
    Sends a reminder notification (email + SMS) only to the user who owns it.
    """
    with get_db() as db:
        user = db.query(User).filter(User.id == reminder.user_id, User.is_active == True).first()
        if user:
            db.expunge(user)

    if not user:
        return

    subject       = f"🏋️ Fitness Reminder: {reminder.title}"
    body          = reminder.message or reminder.title
    personal_body = f"Hi {user.name}! 👋\n\n{body}\n\nKeep going — you're doing great! 💪"

    sent = False

    # Email
    if user.email:
        if send_email(user.email, subject, personal_body):
            sent = True

    # SMS
    if user.phone_number:
        sms_text = f"[AI Fitness Coach] {reminder.title}: {body}"
        send_sms(user.phone_number, sms_text)

    if sent:
        _cli().console.print(f"\n[bold green]🔔 Reminder '{reminder.title}' sent to {user.name}![/bold green]")


# ── Scheduler ─────────────────────────────────────────────────────────────────

_scheduler_running = False


def _scheduler_loop() -> None:
    """
    Background thread: checks every 60 seconds if any reminder is due.
    A reminder fires when the current HH:MM matches reminder.time_str
    and the day-of-week matches (or reminder applies to 'all' days).
    """
    global _scheduler_running
    while _scheduler_running:
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        current_day  = now.strftime("%a").lower()   # mon, tue, wed...

        with get_db() as db:
            due = db.query(Reminder).filter(
                Reminder.is_active == True,
                Reminder.time_str  == current_time,
            ).all()
            db.expunge_all()

        for reminder in due:
            days = reminder.days_of_week.lower()
            if days == "all" or current_day in days:
                _broadcast_reminder(reminder)

        # Sleep until the next minute starts
        time.sleep(60 - now.second)


def start_scheduler() -> None:
    """Start the background reminder scheduler thread."""
    global _scheduler_running
    if _scheduler_running:
        return
    _scheduler_running = True
    thread = threading.Thread(target=_scheduler_loop, daemon=True)
    thread.start()
    print("🕐 Reminder scheduler started (checking every minute).")


def stop_scheduler() -> None:
    global _scheduler_running
    _scheduler_running = False


# ── CLI: Add Reminder ─────────────────────────────────────────────────────────

def _prompt_time() -> str:
    """Prompts for a valid HH:MM time."""
    cli = _cli()
    while True:
        t = cli.ask("Time (HH:MM, 24-hour format) — e.g. 08:00").strip()
        ok, msg = cli.validate_time_str(t)
        if ok:
            return t
        cli.print_error(msg)


def add_meal_reminders(user_id: int) -> None:
    cli = _cli()
    cli.print_section("Set Meal Reminders")
    meals = [
        ("Breakfast",        "Time to eat your breakfast! 🍳 Fuel up for the day."),
        ("Mid-Morning Snack","Snack time! Have a healthy bite 🍎"),
        ("Lunch",            "Lunch time! Don't skip your midday meal 🍱"),
        ("Evening Snack",    "Evening snack time! Keep your metabolism active 🥜"),
        ("Dinner",           "Time for dinner! Eat light and nutritious 🥗"),
    ]
    with get_db() as db:
        for meal_name, message in meals:
            if cli.confirm(f"Set reminder for {meal_name}?"):
                t = _prompt_time()
                db.add(Reminder(
                    user_id=user_id, reminder_type=ReminderTypeEnum.meal,
                    title=meal_name, message=message, time_str=t,
                    days_of_week="all", is_active=True,
                ))
    cli.print_success("Meal reminders saved!")


def add_workout_reminder(user_id: int) -> None:
    cli = _cli()
    cli.print_section("Set Workout Reminder")
    t = _prompt_time()
    days = cli.ask_choice("Which days?", ["all", "weekdays", "weekends"])
    days_map = {"all": "all", "weekdays": "mon,tue,wed,thu,fri", "weekends": "sat,sun"}
    with get_db() as db:
        db.add(Reminder(
            user_id=user_id, reminder_type=ReminderTypeEnum.workout,
            title="Workout Time!", time_str=t, days_of_week=days_map[days],
            message="Time to exercise! 💪 Your body will thank you later. Let's go!",
            is_active=True,
        ))
    cli.print_success("Workout reminder saved!")


def add_water_reminders(user_id: int) -> None:
    cli = _cli()
    cli.print_section("Set Water Reminders")
    interval = cli.ask_choice("Remind every how many hours?", ["1", "2", "3"])
    interval_h = int(interval)
    with get_db() as db:
        hour = 7
        while hour <= 22:
            db.add(Reminder(
                user_id=user_id, reminder_type=ReminderTypeEnum.water,
                title="Drink Water 💧", time_str=f"{hour:02d}:00",
                message="Stay hydrated! Drink a glass of water now. 🥤",
                days_of_week="all", is_active=True,
            ))
            hour += interval_h
    cli.print_success(f"Water reminders set every {interval_h} hour(s) from 7AM to 10PM!")


def add_custom_reminder(user_id: int) -> None:
    cli = _cli()
    cli.print_section("Add Custom Reminder")
    title   = cli.ask("Reminder title")
    message = cli.ask("Reminder message")
    t       = _prompt_time()
    days    = cli.ask_choice("Days?", ["all", "weekdays", "weekends"])
    days_map = {"all": "all", "weekdays": "mon,tue,wed,thu,fri", "weekends": "sat,sun"}
    with get_db() as db:
        db.add(Reminder(
            user_id=user_id, reminder_type=ReminderTypeEnum.custom,
            title=title, message=message, time_str=t,
            days_of_week=days_map[days], is_active=True,
        ))
    cli.print_success(f"Custom reminder '{title}' saved!")


def toggle_reminder(user_id: int) -> None:
    cli = _cli()
    with get_db() as db:
        reminders = db.query(Reminder).filter(Reminder.user_id == user_id).all()
        db.expunge_all()
    if not reminders:
        cli.print_warning("No reminders found."); return
    cli.display_reminders_table(reminders)
    rid = cli.Prompt.ask("Enter Reminder ID to toggle").strip()
    with get_db() as db:
        r = db.query(Reminder).filter(Reminder.id == int(rid), Reminder.user_id == user_id).first()
        if not r:
            cli.print_error(f"Reminder {rid} not found."); return
        r.is_active = not r.is_active
        status = "resumed ✓" if r.is_active else "paused ⏸"
    cli.print_success(f"Reminder {rid} {status}")


def delete_reminder(user_id: int) -> None:
    cli = _cli()
    with get_db() as db:
        reminders = db.query(Reminder).filter(Reminder.user_id == user_id).all()
        db.expunge_all()
    if not reminders:
        cli.print_warning("No reminders found."); return
    cli.display_reminders_table(reminders)
    rid = cli.Prompt.ask("Enter Reminder ID to delete").strip()
    if not cli.confirm(f"Delete reminder {rid}?"): return
    with get_db() as db:
        deleted = db.query(Reminder).filter(Reminder.id == int(rid), Reminder.user_id == user_id).delete()
    if deleted:
        cli.print_success(f"Reminder {rid} deleted.")
    else:
        cli.print_error(f"Reminder {rid} not found.")


def view_reminders(user_id: int) -> None:
    cli = _cli()
    with get_db() as db:
        reminders = db.query(Reminder).filter(Reminder.user_id == user_id).all()
        db.expunge_all()
    cli.display_reminders_table(reminders)


def reminder_menu(user) -> None:
    cli = _cli()
    while True:
        cli.print_section(f"Reminder Manager — {user.name}")
        options = {
            "1": "Set Meal Reminders", "2": "Set Workout Reminder",
            "3": "Set Water Reminders", "4": "Add Custom Reminder",
            "5": "View All Reminders",  "6": "Pause / Resume a Reminder",
            "7": "Delete a Reminder",   "0": "Back to Main Menu",
        }
        for k, v in options.items():
            cli.console.print(f"    [bold cyan]{k}[/bold cyan]  {v}")
        choice = cli.Prompt.ask("\n  Select option", choices=list(options.keys()))
        if   choice == "1": add_meal_reminders(user.id)
        elif choice == "2": add_workout_reminder(user.id)
        elif choice == "3": add_water_reminders(user.id)
        elif choice == "4": add_custom_reminder(user.id)
        elif choice == "5": view_reminders(user.id)
        elif choice == "6": toggle_reminder(user.id)
        elif choice == "7": delete_reminder(user.id)
        elif choice == "0": break


def send_test_notification(user) -> None:
    cli = _cli()
    cli.print_section("Send Test Notification")
    subject = "🏋️ AI Fitness Coach — Test Notification"
    body = (
        f"Hi {user.name}! 👋\n\n"
        "This is a test notification from your AI Fitness Coach.\n"
        "If you received this, your reminders are configured correctly! 🎉\n\n"
        "Stay fit and consistent! 💪"
    )
    if user.email:
        cli.print_info(f"Sending test email to {user.email}...")
        if send_email(user.email, subject, body):
            cli.print_success("Test email sent successfully!")
        else:
            cli.print_error("Email failed. Check GMAIL_ADDRESS and GMAIL_APP_PASSWORD in .env")
    else:
        cli.print_warning("No email on file.")
    if user.phone_number:
        cli.print_info(f"Sending test SMS to {user.phone_number}...")
        sms = f"[AI Fitness Coach] Hi {user.name}! Test SMS — your reminders are working! 💪"
        if send_sms(user.phone_number, sms):
            cli.print_success("Test SMS sent successfully!")
        else:
            cli.print_error("SMS failed. Check Twilio credentials in .env")
    else:
        cli.print_warning("No phone number on file.")
