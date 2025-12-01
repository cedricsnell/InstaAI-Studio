# InstaAI Testing Guide

## Quick Start - Test the Backend API Right Now

### 1. Start the Backend
```bash
cd C:\CODING\Apps\InstaAI-Studio

# Install dependencies (if not already)
pip install -r requirements.txt

# Initialize database
python -c "from src.database import init_db; init_db()"

# Start server
python -m src.api.main
```

The server will start on `http://localhost:8000`

### 2. Open API Documentation

**Go to: http://localhost:8000/docs**

You'll see a beautiful interactive API interface (Swagger UI) where you can:
- ✅ Test all endpoints
- ✅ See request/response examples
- ✅ Execute API calls directly from your browser
- ✅ No coding required!

### 3. Test the Flow

#### Step 1: Register a User
1. Find **POST /api/auth/register**
2. Click "Try it out"
3. Edit the request body:
   ```json
   {
     "email": "test@example.com",
     "password": "password123",
     "full_name": "Test User"
   }
   ```
4. Click "Execute"
5. Copy the `access_token` from the response

#### Step 2: Authorize Requests
1. Click the 🔓 "Authorize" button at the top
2. Enter: `Bearer YOUR_ACCESS_TOKEN_HERE`
3. Click "Authorize"
4. Now all requests will include your token!

#### Step 3: Get Instagram OAuth URL
1. Find **GET /api/instagram/auth-url**
2. Click "Try it out" → "Execute"
3. Copy the `authorization_url` from response
4. This is the URL you'll give to Karley to authorize her Instagram

#### Step 4: Test Other Endpoints
- **GET /api/auth/me** - See your user info
- **GET /api/instagram/accounts** - List connected accounts
- **GET /api/insights/1** - Get insights (after connecting Instagram)

---

## Testing with Karley's Instagram Account

### Prerequisites:

**Karley's Instagram Account Must Be**:
- ✅ Business or Creator account (not Personal)
- ✅ Connected to a Facebook Page
- ✅ Has at least 100 followers (for full insights)

**Convert Personal → Business**:
```
1. Open Instagram app
2. Go to Settings → Account
3. Switch to Professional Account
4. Choose "Business"
5. Connect to Facebook Page (or create one)
```

### Setup Instagram App:

**Create Facebook App** (You do this once):
```
1. Go to: https://developers.facebook.com/apps/
2. Create App → Business
3. Add Product: "Instagram Graph API"
4. Basic Settings:
   - Copy App ID
   - Copy App Secret
   - Save App

5. Instagram Graph API → Settings:
   - Valid OAuth Redirect URIs:
     http://localhost:8000/auth/callback

6. Update .env file:
   INSTAGRAM_APP_ID=your_app_id
   INSTAGRAM_APP_SECRET=your_app_secret
   INSTAGRAM_REDIRECT_URI=http://localhost:8000/auth/callback
```

### Testing Flow:

**1. Get Authorization URL**
```bash
curl http://localhost:8000/api/instagram/auth-url \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**2. Karley Visits URL**
- Send her the `authorization_url`
- She logs into Instagram (Business account)
- Clicks "Authorize"
- Gets redirected to: `http://localhost:8000/auth/callback?code=AQD...`
- Copy the `code` parameter

**3. Exchange Code for Token**
```bash
curl -X POST http://localhost:8000/api/instagram/connect \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"authorization_code": "PASTE_CODE_HERE"}'
```

**4. Fetch Insights**
```bash
curl http://localhost:8000/api/insights/1 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Expected response:
```json
{
  "account_insights": {
    "account": {
      "username": "calmworkshop",
      "followers_count": 5000,
      "media_count": 150
    },
    "media": [
      {
        "media_type": "REELS",
        "caption": "5 ways to reduce stress...",
        "like_count": 250,
        "comments_count": 15,
        "reach": 10000,
        "engagement_rate": 2.65
      }
      // ... more posts
    ],
    "audience": {
      "gender_age": {
        "F.25-34": 450,
        "F.35-44": 300,
        "M.25-34": 150
      },
      "top_cities": ["New York", "Los Angeles", "Chicago"]
    }
  },
  "ai_recommendations": {
    "summary": "Your CALM Workshop content resonates strongly with women 25-44. Reels format shows 3x higher engagement than static images. Focus on Tuesday/Thursday posts at 9am and 6pm for maximum reach.",
    "ad_formats": [
      {
        "format": "REELS",
        "score": 92,
        "reasoning": "Your Reels average 2.8% engagement vs 0.9% for images. Video content showing quick wellness tips performs best."
      }
    ],
    "targeting": {
      "age_ranges": ["25-34", "35-44"],
      "genders": ["F"],
      "locations": ["New York, NY", "Los Angeles, CA"],
      "interests": ["wellness", "meditation", "self-care"],
      "reasoning": "85% of your engaged audience is women 25-44 interested in wellness"
    },
    "budget_allocation": {
      "instagram": 75,
      "facebook": 20,
      "google": 5,
      "reasoning": "Instagram shows highest engagement. Facebook extends reach to similar demographics."
    },
    "posting_schedule": {
      "best_days": ["Tuesday", "Thursday", "Saturday"],
      "best_times": ["9:00 AM", "6:00 PM"],
      "frequency": "4-5 times per week",
      "reasoning": "Your audience is most active weekday mornings and early evenings"
    },
    "roi_projection": {
      "estimated_reach": 50000,
      "estimated_clicks": 1000,
      "estimated_conversions": 50,
      "estimated_revenue": 4995,
      "confidence": "high"
    }
  }
}
```

---

## What to Expect

### ✅ Success Indicators:
- Instagram connection succeeds without errors
- Insights show real data from her account
- AI recommendations are specific to her content/audience
- Recommendations mention her specific audience (women 25-44, wellness)
- Cache works (second call returns instantly from database)

### ⚠️ Common Issues:

**1. "Only Business accounts are supported"**
- Solution: Convert to Business account in Instagram app

**2. "Failed to get insights"**
- Check: Is account connected to Facebook Page?
- Check: Does account have 100+ followers?
- Check: Is App ID/Secret correct in .env?

**3. "Authorization failed"**
- Check: Is redirect URI exactly matching in both .env and Facebook app?
- Check: Did you copy the full authorization code?

**4. "AI analysis failed"**
- Falls back to data-driven defaults
- Check: Is ANTHROPIC_API_KEY set in .env?
- Still works! Just uses statistical analysis instead of Claude

---

## Alternative: Simple Web Frontend

If you want a visual interface instead of API docs, I can create:

**Option A: Simple Test Page** (30 min):
```html
Simple HTML/JS page with:
- Login form
- "Connect Instagram" button
- Display insights in a table
- Show AI recommendations
```

**Option B: React Dashboard** (2 hours):
```
Prettier dashboard with:
- Charts for engagement
- Cards for recommendations
- Professional UI
```

**Option C: Full Mobile App** (4-6 hours):
```
React Native app like the plan:
- Onboarding flow
- Instagram connection
- Full insights dashboard
- Content preview
- Scheduling
```

Which would you prefer for tomorrow's testing?

---

## Next Steps

**Tonight**:
- ✅ Backend is ready
- ✅ API docs available at /docs
- ⏳ Need Instagram App credentials

**Tomorrow**:
1. Create Instagram Business App (15 min)
2. Add credentials to .env
3. Test OAuth flow with test account
4. Test with Karley's real account
5. Review AI recommendations
6. Decide on frontend approach

**Ready to test?**
```bash
cd C:\CODING\Apps\InstaAI-Studio
python -m src.api.main
# Open http://localhost:8000/docs
```
