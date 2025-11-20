"""
FastAPI Web Application for InstaAI Studio
Provides web UI and REST API access
"""
import os
import sys
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timedelta
import json
import secrets
import hashlib

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends, status, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from config import Config
from main import InstaAIStudio

# Initialize FastAPI app
app = FastAPI(
    title="InstaAI Studio",
    description="Create Instagram content with natural language",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBasic()

# Simple in-memory user database (replace with real database in production)
USERS = {
    "admin": {
        "password_hash": hashlib.sha256("admin123".encode()).hexdigest(),
        "role": "admin"
    }
}

# File upload directory
UPLOAD_DIR = Config.TEMP_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Initialize InstaAI Studio
instaai = InstaAIStudio()


# Pydantic models
class CreateContentRequest(BaseModel):
    commands: List[str]
    content_type: str = "reel"
    output_filename: Optional[str] = None


class PostContentRequest(BaseModel):
    media_filename: str
    post_type: str
    caption: str = ""
    hashtags: List[str] = []
    scheduled_time: Optional[str] = None


class ScheduleRequest(BaseModel):
    media_filename: str
    post_type: str
    scheduled_time: str
    caption: str = ""
    hashtags: List[str] = []


class UserCreate(BaseModel):
    username: str
    password: str


# Authentication
def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    """Verify user credentials"""
    username = credentials.username
    password = credentials.password

    if username not in USERS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    password_hash = hashlib.sha256(password.encode()).hexdigest()
    if USERS[username]["password_hash"] != password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    return username


# Serve static files
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# Routes
@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve main web UI"""
    html_file = Path(__file__).parent / "static" / "index.html"
    if html_file.exists():
        return FileResponse(html_file)
    return """
    <html>
        <head><title>InstaAI Studio</title></head>
        <body>
            <h1>InstaAI Studio API</h1>
            <p>Web UI coming soon. For now, visit <a href="/docs">/docs</a> for API documentation.</p>
        </body>
    </html>
    """


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/config")
async def get_config(username: str = Depends(verify_credentials)):
    """Get configuration status"""
    return {
        "ai_configured": bool(Config.ANTHROPIC_API_KEY or Config.OPENAI_API_KEY),
        "instagram_configured": bool(Config.INSTAGRAM_USERNAME and Config.INSTAGRAM_PASSWORD),
        "scheduler_enabled": Config.ENABLE_SCHEDULER,
        "max_video_duration": Config.MAX_VIDEO_DURATION,
        "instagram_specs": Config.INSTAGRAM_SPECS
    }


@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    username: str = Depends(verify_credentials)
):
    """Upload a video or image file"""
    try:
        # Generate unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{username}_{timestamp}_{file.filename}"
        file_path = UPLOAD_DIR / filename

        # Save file
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        return {
            "success": True,
            "filename": filename,
            "size": len(content),
            "path": str(file_path)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/create")
async def create_content(
    request: CreateContentRequest,
    background_tasks: BackgroundTasks,
    username: str = Depends(verify_credentials)
):
    """Create Instagram content from uploaded files"""
    try:
        # Get uploaded files for this user
        uploaded_files = list(UPLOAD_DIR.glob(f"{username}_*"))

        if not uploaded_files:
            raise HTTPException(status_code=400, detail="No uploaded files found")

        # Use most recent upload
        input_file = max(uploaded_files, key=lambda p: p.stat().st_mtime)

        # Generate output filename
        if request.output_filename:
            output_filename = request.output_filename
        else:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_filename = f"{username}_{request.content_type}_{timestamp}.mp4"

        output_path = Config.OUTPUT_DIR / output_filename

        # Create content
        result = instaai.create_content(
            input_files=[input_file],
            commands=request.commands,
            output_path=output_path,
            content_type=request.content_type
        )

        return {
            "success": True,
            "output_filename": output_filename,
            "output_path": str(result),
            "content_type": request.content_type,
            "commands_executed": len(request.commands)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/post")
async def post_content(
    request: PostContentRequest,
    username: str = Depends(verify_credentials)
):
    """Post content to Instagram"""
    try:
        # Find media file
        media_path = Config.OUTPUT_DIR / request.media_filename

        if not media_path.exists():
            raise HTTPException(status_code=404, detail="Media file not found")

        # Parse scheduled time if provided
        scheduled_time = None
        if request.scheduled_time:
            from dateutil import parser
            scheduled_time = parser.parse(request.scheduled_time)

        # Post content
        instaai.post_content(
            media_path=media_path,
            post_type=request.post_type,
            caption=request.caption,
            hashtags=request.hashtags if request.hashtags else None,
            scheduled_time=scheduled_time
        )

        if scheduled_time:
            return {
                "success": True,
                "message": f"Content scheduled for {scheduled_time}",
                "scheduled": True
            }
        else:
            return {
                "success": True,
                "message": "Content posted successfully",
                "scheduled": False
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/scheduled")
async def get_scheduled_posts(
    status: Optional[str] = None,
    username: str = Depends(verify_credentials)
):
    """Get scheduled posts"""
    try:
        if not instaai.scheduler:
            raise HTTPException(status_code=400, detail="Scheduler not enabled")

        posts = instaai.scheduler.get_scheduled_posts(status)
        return {"success": True, "posts": posts}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/scheduled/{job_id}")
async def cancel_scheduled_post(
    job_id: str,
    username: str = Depends(verify_credentials)
):
    """Cancel a scheduled post"""
    try:
        if not instaai.scheduler:
            raise HTTPException(status_code=400, detail="Scheduler not enabled")

        success = instaai.scheduler.cancel_job(job_id)

        if success:
            return {"success": True, "message": f"Job {job_id} cancelled"}
        else:
            raise HTTPException(status_code=400, detail="Failed to cancel job")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/account")
async def get_account_info(username: str = Depends(verify_credentials)):
    """Get Instagram account information"""
    try:
        if not instaai.instagram_poster:
            raise HTTPException(status_code=400, detail="Instagram not configured")

        info = instaai.instagram_poster.get_account_info()
        return {"success": True, "account": info}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/files")
async def list_files(username: str = Depends(verify_credentials)):
    """List user's uploaded and created files"""
    try:
        # Get uploaded files
        uploads = []
        for file in UPLOAD_DIR.glob(f"{username}_*"):
            uploads.append({
                "filename": file.name,
                "size": file.stat().st_size,
                "created": datetime.fromtimestamp(file.stat().st_mtime).isoformat(),
                "type": "upload"
            })

        # Get output files
        outputs = []
        for file in Config.OUTPUT_DIR.glob(f"{username}_*"):
            outputs.append({
                "filename": file.name,
                "size": file.stat().st_size,
                "created": datetime.fromtimestamp(file.stat().st_mtime).isoformat(),
                "type": "output"
            })

        return {
            "success": True,
            "uploads": uploads,
            "outputs": outputs
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/download/{filename}")
async def download_file(
    filename: str,
    username: str = Depends(verify_credentials)
):
    """Download a created file"""
    try:
        # Security: only allow downloading files created by this user
        if not filename.startswith(f"{username}_"):
            raise HTTPException(status_code=403, detail="Access denied")

        file_path = Config.OUTPUT_DIR / filename

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        return FileResponse(file_path, filename=filename)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/files/{filename}")
async def delete_file(
    filename: str,
    username: str = Depends(verify_credentials)
):
    """Delete an uploaded or output file"""
    try:
        # Security: only allow deleting own files
        if not filename.startswith(f"{username}_"):
            raise HTTPException(status_code=403, detail="Access denied")

        # Try upload directory first
        file_path = UPLOAD_DIR / filename
        if not file_path.exists():
            file_path = Config.OUTPUT_DIR / filename

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        file_path.unlink()

        return {"success": True, "message": f"File {filename} deleted"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Admin endpoints
@app.post("/api/admin/users")
async def create_user(
    user: UserCreate,
    username: str = Depends(verify_credentials)
):
    """Create a new user (admin only)"""
    if USERS.get(username, {}).get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    if user.username in USERS:
        raise HTTPException(status_code=400, detail="User already exists")

    USERS[user.username] = {
        "password_hash": hashlib.sha256(user.password.encode()).hexdigest(),
        "role": "user"
    }

    return {"success": True, "message": f"User {user.username} created"}


@app.get("/api/admin/stats")
async def get_stats(username: str = Depends(verify_credentials)):
    """Get system statistics (admin only)"""
    if USERS.get(username, {}).get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    total_uploads = len(list(UPLOAD_DIR.glob("*")))
    total_outputs = len(list(Config.OUTPUT_DIR.glob("*")))

    return {
        "success": True,
        "stats": {
            "total_users": len(USERS),
            "total_uploads": total_uploads,
            "total_outputs": total_outputs,
            "scheduler_enabled": Config.ENABLE_SCHEDULER
        }
    }


if __name__ == "__main__":
    print("Starting InstaAI Studio Web Server...")
    print(f"Default credentials: admin / admin123")
    print(f"Access at: http://localhost:5001")
    print(f"API docs at: http://localhost:5001/docs")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=5001,
        log_level="info"
    )
