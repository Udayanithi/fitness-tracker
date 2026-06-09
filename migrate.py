"""
migrate.py — Run this ONCE to add phone_number column to existing database.

Usage:
    python migrate.py

Safe to run multiple times — skips if column already exists.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import engine
from sqlalchemy import text, inspect

def run_migrations():
    print("Running database migrations...")

    with engine.connect() as conn:
        # Check if phone_number column already exists
        existing_cols = [c["name"] for c in inspect(engine).get_columns("users")]

        if "phone_number" not in existing_cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN phone_number VARCHAR(20)"))
            conn.commit()
            print("✓ Added 'phone_number' column to users table.")
        else:
            print("✓ 'phone_number' column already exists — skipping.")

    print("All migrations complete!")

if __name__ == "__main__":
    run_migrations()
