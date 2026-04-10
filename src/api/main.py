"""
FastAPI main application for InstaAI backend.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import os

from ..database import get_db, init_db
from . import auth, instagram, insights, content, schedule, teams, billing
from .routes import oauth, instagram_callback


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup."""
    try:
        init_db()
        print("Database initialized")
    except Exception as e:
        print(f"Database initialization failed: {e}")
    yield


# Initialize FastAPI app
app = FastAPI(
    title="InstaAI API",
    description="End-to-end Instagram marketing automation API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware - allow frontend and mobile app to connect
allowed_origins = [
    "https://instaaistudio.netlify.app",  # Production Netlify frontend
    "http://localhost:3000",  # Local development
    "http://localhost:5173",  # Vite dev server
    "http://localhost:8080",  # Alternative dev server
]

# Add any additional origins from environment variable
frontend_url = os.getenv("FRONTEND_URL")
if frontend_url and frontend_url not in allowed_origins:
    allowed_origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "message": "InstaAI API is running",
        "version": "1.0.0",
        "status": "healthy"
    }


@app.get("/health")
async def health_check():
    """Detailed health check."""
    from sqlalchemy import text

    # Check database
    db_status = "error"
    try:
        db = next(get_db())
        db.execute(text("SELECT 1"))
        db.close()
        db_status = "connected"
    except Exception:
        pass

    # Check Redis (if configured)
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        redis_status = "error"
        try:
            import redis as redis_lib
            r = redis_lib.from_url(redis_url, socket_connect_timeout=2)
            r.ping()
            redis_status = "connected"
        except Exception:
            pass
    else:
        redis_status = "unconfigured"

    overall = "healthy" if db_status == "connected" else "degraded"

    return {
        "status": overall,
        "timestamp": datetime.utcnow().isoformat(),
        "database": db_status,
        "redis": redis_status,
        "services": {
            "instagram_api": "operational",
            "ai_analysis": "operational",
            "content_generation": "operational"
        }
    }


# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(oauth.router, prefix="/api", tags=["OAuth"])
app.include_router(instagram_callback.router, prefix="/auth", tags=["Instagram OAuth Callback"])
app.include_router(teams.router, prefix="/api", tags=["Teams & Collaboration"])
app.include_router(instagram.router, prefix="/api/instagram", tags=["Instagram"])
app.include_router(insights.router, prefix="/api/insights", tags=["Insights & Analytics"])
app.include_router(content.router, prefix="/api/content", tags=["Content Generation"])
app.include_router(schedule.router, prefix="/api/schedule", tags=["Post Scheduling"])
app.include_router(billing.router, prefix="/api/billing", tags=["Billing & Subscriptions"])


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=port, reload=True)
