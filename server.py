"""
server.py — Start the AI Fitness Coach API + Frontend

Usage:
    python server.py

URLs:
    Frontend  → http://localhost:8000/app
    API Docs  → http://localhost:8000/docs
    ReDoc     → http://localhost:8000/redoc
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn

if __name__ == "__main__":
    print("\n🏋️  AI Fitness Coach starting...\n")
    print("  🌐  Frontend  → http://localhost:8000/app")
    print("  📖  API Docs  → http://localhost:8000/docs")
    print("  📘  ReDoc     → http://localhost:8000/redoc\n")
    uvicorn.run("api.app:app", host="0.0.0.0", port=8000, reload=True, log_level="warning")
