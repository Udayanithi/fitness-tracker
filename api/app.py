"""
api/app.py — FastAPI Application
Serves the REST API + static frontend from /frontend/index.html
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os

from api.routers import users, health, plans, progress, reminders
from app.database import init_db
from app.modules.reminders import start_scheduler
from config import APP_NAME, APP_VERSION

app = FastAPI(
    title       = APP_NAME,
    description = """
**AI Fitness Coach API** — FastAPI + SQLite + Groq (Llama 3.3)

## Quick Start
1. `POST /users/register` — Create account
2. `POST /health/{user_id}/analyze` — Run health analysis
3. `POST /plans/{user_id}/workout` — Generate AI workout plan
4. `POST /plans/{user_id}/diet` — Generate AI diet plan
5. `POST /progress/{user_id}` — Log progress
    """,
    version   = APP_VERSION,
    docs_url  = "/docs",
    redoc_url = "/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    init_db()
    start_scheduler()
    print(f"✓ {APP_NAME} v{APP_VERSION} ready")
    print(f"  Frontend → http://localhost:8000/app")
    print(f"  API Docs → http://localhost:8000/docs")

@app.exception_handler(Exception)
async def global_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": str(exc), "success": False})

@app.get("/", tags=["Health Check"])
def root():
    return {"app": APP_NAME, "version": APP_VERSION, "status": "running",
            "frontend": "/app", "docs": "/docs"}

# ── Serve frontend ────────────────────────────────────
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

@app.get("/app", response_class=HTMLResponse, include_in_schema=False)
def serve_frontend():
    """Serve the web frontend."""
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

# ── Routers ───────────────────────────────────────────
app.include_router(users.router)
app.include_router(health.router)
app.include_router(plans.router)
app.include_router(progress.router)
app.include_router(reminders.router)
