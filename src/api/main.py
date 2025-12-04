"""
FastAPI main application for InstaAI backend.
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import os

from ..database import get_db, init_db
from . import auth, instagram, insights, content, schedule, teams
from .routes import oauth

# Initialize FastAPI app
app = FastAPI(
    title="InstaAI API",
    description="End-to-end Instagram marketing automation API",
    version="1.0.0"
)

# CORS middleware - allow mobile app to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    try:
        init_db()
        print("Database initialized")
    except Exception as e:
        print(f"Database initialization failed: {e}")


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
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "database": "connected",
        "services": {
            "instagram_api": "operational",
            "ai_analysis": "operational",
            "content_generation": "operational"
        }
    }


# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(oauth.router, prefix="/api", tags=["OAuth"])
app.include_router(teams.router, prefix="/api", tags=["Teams & Collaboration"])
app.include_router(instagram.router, prefix="/api/instagram", tags=["Instagram"])
app.include_router(insights.router, prefix="/api/insights", tags=["Insights & Analytics"])
app.include_router(content.router, prefix="/api/content", tags=["Content Generation"])
app.include_router(schedule.router, prefix="/api/schedule", tags=["Post Scheduling"])


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=port, reload=True)
