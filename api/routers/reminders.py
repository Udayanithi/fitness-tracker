"""api/routers/reminders.py — Reminder CRUD + test send endpoints"""

from fastapi import APIRouter, HTTPException
from typing import List
from api.schemas import (
    ReminderCreate, ReminderResponse, ReminderListResponse, MessageResponse
)
from app.database import get_db
from app.models import User, Reminder, ReminderTypeEnum
from app.modules.reminders import send_email, send_sms

router = APIRouter(prefix="/reminders", tags=["Reminders"])


def _get_user(user_id: int) -> User:
    with get_db() as db:
        u = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not u:
            raise HTTPException(404, f"User {user_id} not found.")
        db.expunge(u)
    return u


# ── Create reminder ──────────────────────────────────────────────────────────

@router.post("/{user_id}", response_model=ReminderResponse, status_code=201)
def create_reminder(user_id: int, data: ReminderCreate):
    """Create a new reminder for a user."""
    _get_user(user_id)
    with get_db() as db:
        r = Reminder(
            user_id       = user_id,
            reminder_type = ReminderTypeEnum(data.reminder_type),
            title         = data.title.strip(),
            message       = data.message,
            time_str      = data.time_str,
            days_of_week  = data.days_of_week,
            is_active     = True,
        )
        db.add(r)
        db.flush()
        rid = r.id

    with get_db() as db:
        r = db.query(Reminder).filter(Reminder.id == rid).first()
        db.expunge(r)
    return r


# ── List reminders ───────────────────────────────────────────────────────────

@router.get("/{user_id}", response_model=ReminderListResponse)
def list_reminders(user_id: int):
    """Get all reminders for a user."""
    _get_user(user_id)
    with get_db() as db:
        reminders = db.query(Reminder).filter(Reminder.user_id == user_id)\
                      .order_by(Reminder.time_str).all()
        db.expunge_all()
    return {"reminders": reminders, "total": len(reminders)}


# ── Toggle active ────────────────────────────────────────────────────────────

@router.put("/{user_id}/{reminder_id}/toggle", response_model=MessageResponse)
def toggle_reminder(user_id: int, reminder_id: int):
    """Pause or resume a reminder."""
    with get_db() as db:
        r = db.query(Reminder).filter(
            Reminder.id == reminder_id, Reminder.user_id == user_id
        ).first()
        if not r:
            raise HTTPException(404, "Reminder not found.")
        r.is_active = not r.is_active
        status = "resumed" if r.is_active else "paused"
    return {"message": f"Reminder '{r.title}' {status}.", "success": True}


# ── Delete reminder ──────────────────────────────────────────────────────────

@router.delete("/{user_id}/{reminder_id}", response_model=MessageResponse)
def delete_reminder(user_id: int, reminder_id: int):
    """Delete a reminder."""
    with get_db() as db:
        deleted = db.query(Reminder).filter(
            Reminder.id == reminder_id, Reminder.user_id == user_id
        ).delete()
    if not deleted:
        raise HTTPException(404, "Reminder not found.")
    return {"message": "Reminder deleted.", "success": True}


# ── Test notification ────────────────────────────────────────────────────────

@router.post("/{user_id}/test", response_model=MessageResponse)
def send_test_notification(user_id: int):
    """Send a test email + SMS to verify credentials."""
    user = _get_user(user_id)
    results = []

    subject = "🏋️ AI Fitness Coach — Test Notification"
    body = (
        f"Hi {user.name}! 👋\n\n"
        "This is a test notification from your AI Fitness Coach.\n"
        "If you received this, your reminders are configured correctly! 🎉\n\n"
        "Stay fit and consistent! 💪"
    )

    if user.email:
        ok = send_email(user.email, subject, body)
        results.append(f"Email {'✓ sent' if ok else '✗ failed'} to {user.email}")
    else:
        results.append("Email: no email on file")

    if user.phone_number:
        sms = f"[AI Fitness Coach] Hi {user.name}! Test SMS — reminders are working! 💪"
        ok = send_sms(user.phone_number, sms)
        results.append(f"SMS {'✓ sent' if ok else '✗ failed'} to {user.phone_number}")
    else:
        results.append("SMS: no phone number on file")

    return {"message": " | ".join(results), "success": True}
