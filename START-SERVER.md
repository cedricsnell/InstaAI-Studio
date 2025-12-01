# InstaAI Studio - Server Start Guide

## ⚠️ IMPORTANT: Which Server to Start?

InstaAI Studio has **TWO different servers**:

### 1. **Analytics API Server** (MAIN - Use This!)
**Location:** `src/api/main.py`
**Port:** 8000
**Purpose:** Instagram Analytics, AI Insights, OAuth, Content Generation

**Start Command:**
```bash
cd C:\CODING\Apps\InstaAI-Studio
py -m src.api.main
```

**Access:**
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

**Features:**
- ✓ Instagram Graph API integration
- ✓ AI-powered insights and recommendations
- ✓ OAuth flow for Instagram Business accounts
- ✓ Analytics caching (6 hours)
- ✓ Content generation endpoints
- ✓ Post scheduling

---

### 2. **Legacy Web UI Server** (OLD - Don't Use)
**Location:** `src/web/app.py`
**Port:** 5001
**Purpose:** Old content creation web interface (pre-analytics)

**This is NOT the analytics version!**

---

## Quick Start (Analytics API)

```bash
# 1. Navigate to project
cd C:\CODING\Apps\InstaAI-Studio

# 2. Activate virtual environment (if using one)
# venv\Scripts\activate

# 3. Start server
py -m src.api.main
```

## Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login (get JWT token)
- `GET /api/auth/me` - Get current user

### Instagram (Coming Soon)
- `GET /api/instagram/auth-url` - Get OAuth URL
- `POST /api/instagram/connect` - Connect Instagram account
- `GET /api/instagram/accounts` - List connected accounts

### Insights (Coming Soon)
- `GET /api/insights/{account_id}` - Get insights + AI recommendations
- `POST /api/insights/{account_id}/analyze` - Custom analysis

## Environment Setup

Make sure `.env` file has:
```
DATABASE_URL=sqlite:///./data/instaai.db
ANTHROPIC_API_KEY=your_key_here
INSTAGRAM_APP_ID=your_app_id
INSTAGRAM_APP_SECRET=your_app_secret
INSTAGRAM_REDIRECT_URI=your_redirect_uri
SECRET_KEY=your_secret_key
```

## Troubleshooting

### Missing Dependencies
```bash
py -m pip install -r requirements.txt
py -m pip install "pydantic[email]"
```

### Database Not Initialized
The server auto-initializes the database on startup.
Manual: `py -c "from src.database import init_db; init_db()"`

### Port Already in Use
```bash
# Kill process on port 8000
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```
