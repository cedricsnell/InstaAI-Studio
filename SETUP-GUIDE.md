# InstaAI Studio - Enterprise Setup Guide

Complete step-by-step instructions to configure your enterprise infrastructure.

---

## 📋 Prerequisites Checklist

- [x] Supabase account created
- [x] Upstash Redis account created
- [x] Cloudflare account created (R2 enabled)
- [x] Railway account created
- [ ] Instagram/Facebook Developer App created
- [ ] Anthropic API key (or OpenAI)

---

## 1️⃣ Supabase Database Setup

### Step 1: Create a New Project

1. Go to https://app.supabase.com
2. Click **"New Project"**
3. Fill in:
   - **Name**: `instaai-production` (or your choice)
   - **Database Password**: Generate a strong password (save this!)
   - **Region**: Choose closest to your users
   - **Pricing Plan**: Free (or Pro for production)
4. Click **"Create new project"**
5. Wait 2-3 minutes for provisioning

### Step 2: Get Your Connection Credentials

1. In your Supabase project, go to **Settings** (⚙️) → **Database**
2. Scroll to **"Connection string"** section
3. Copy the **URI** format connection string
4. Replace `[YOUR-PASSWORD]` with your actual database password

**Example:**
```
postgresql://postgres.xxxxxxxxxxxx:YOUR_PASSWORD@aws-0-us-west-1.pooler.supabase.com:5432/postgres
```

### Step 3: Get API Keys

1. Go to **Settings** → **API**
2. Copy these values:
   - **Project URL**: `https://xxxxxxxxxxxx.supabase.co`
   - **anon public key**: `eyJhbG...` (safe for client-side)
   - **service_role secret**: `eyJhbG...` (KEEP SECRET - server only)

### Step 4: Create Storage Bucket (Optional - if using Supabase Storage)

1. Go to **Storage** in sidebar
2. Click **"New bucket"**
3. Name: `instaai-media`
4. Set to **Public** (for public URLs)
5. Click **"Create bucket"**

---

## 2️⃣ Upstash Redis Setup

### Step 1: Create a Database

1. Go to https://console.upstash.com/redis
2. Click **"Create Database"**
3. Fill in:
   - **Name**: `instaai-cache`
   - **Type**: Regional (cheaper) or Global (faster)
   - **Region**: Same as your Supabase (or closest)
   - **Eviction**: Check "Enable Eviction" (recommended)
4. Click **"Create"**

### Step 2: Get Connection Details

1. Click on your new database
2. Scroll to **"REST API"** section
3. Copy these values:
   - **UPSTASH_REDIS_REST_URL**: `https://xxxxxxx.upstash.io`
   - **UPSTASH_REDIS_REST_TOKEN**: `AXXXxxxxxxxx`

4. Also get the **Redis URL**:
   - Scroll to **"Connect your database"**
   - Copy the **Redis URL** (starts with `rediss://`)
   - Format: `rediss://default:YOUR_PASSWORD@xxx.upstash.io:6379`

---

## 3️⃣ Cloudflare R2 Setup

### Step 1: Enable R2

1. Go to https://dash.cloudflare.com
2. Select your account
3. In sidebar, click **R2** (under "Storage")
4. Click **"Purchase R2 Plan"** (or enable if on paid plan)
5. Accept terms

### Step 2: Create a Bucket

1. Click **"Create bucket"**
2. **Bucket name**: `instaai-storage` (must be globally unique)
3. **Location**: Automatic (or choose specific region)
4. Click **"Create bucket"**

### Step 3: Get API Credentials

1. Go back to **R2** main page
2. Click **"Manage R2 API Tokens"**
3. Click **"Create API token"**
4. Fill in:
   - **Token name**: `instaai-api-token`
   - **Permissions**:
     - ✅ Object Read & Write
     - ✅ Admin Read & Write (or just your bucket)
   - **TTL**: No expiration (or set as needed)
5. Click **"Create API Token"**

6. **SAVE THESE IMMEDIATELY** (shown only once):
   ```
   Access Key ID: xxxxxxxxxxxxxxxxxxxxx
   Secret Access Key: yyyyyyyyyyyyyyyyyyyyyyyyyy
   ```

7. Your **Account ID** is in the URL or in the R2 overview page

### Step 4: Set Up Public Access (Optional)

1. Click on your bucket (`instaai-storage`)
2. Go to **Settings** → **Public access**
3. Click **"Allow Access"** to enable public reads
4. Your public URL will be: `https://pub-xxxxxxx.r2.dev`

**OR** set up custom domain:
1. Go to **Settings** → **Domain**
2. Click **"Connect domain"**
3. Enter: `storage.yourdomain.com`
4. Add DNS record as instructed
5. Enable

---

## 4️⃣ Railway Setup

### Step 1: Connect GitHub

1. Go to https://railway.app
2. Click **"Start a New Project"**
3. Select **"Deploy from GitHub repo"**
4. Authorize Railway to access your GitHub
5. Select repository: `cedricsnell/InstaAI-Studio`

### Step 2: Configure Service

1. Railway will detect it's a Python app
2. Click **"Add variables"**
3. **DON'T add variables yet** - we'll do this in Step 5

### Step 3: Set Build Command (if needed)

1. Go to **Settings** → **Build**
2. **Build Command**: `pip install -r requirements.txt`
3. **Start Command**: `uvicorn src.api.main:app --host 0.0.0.0 --port $PORT`

---

## 5️⃣ Instagram/Facebook Developer App

### Step 1: Create Facebook App

1. Go to https://developers.facebook.com/apps
2. Click **"Create App"**
3. Select **"Business"** as app type
4. Fill in:
   - **App name**: `InstaAI Studio`
   - **Contact email**: Your email
5. Click **"Create App"**

### Step 2: Add Instagram Product

1. In your app dashboard, find **"Instagram"**
2. Click **"Set Up"**
3. Complete the setup wizard

### Step 3: Get App Credentials

1. Go to **Settings** → **Basic**
2. Copy:
   - **App ID**: `1234567890123456`
   - **App Secret**: Click "Show", then copy

### Step 4: Configure Instagram Settings

1. Go to **Instagram** → **Basic Display**
2. Click **"Create New App"** (if needed)
3. Set **Valid OAuth Redirect URIs**:
   ```
   http://localhost:8000/api/oauth/callback
   https://YOUR-RAILWAY-URL.railway.app/api/oauth/callback
   ```
4. Save changes

### Step 5: Go Live (When Ready)

1. App is in "Development Mode" by default
2. When ready for production:
   - Complete **App Review**
   - Request **instagram_basic**, **instagram_content_publish** permissions
   - Switch to "Live Mode"

---

## 6️⃣ AI Services Setup

### Anthropic Claude (Recommended)

1. Go to https://console.anthropic.com
2. Go to **API Keys**
3. Click **"Create Key"**
4. Copy: `sk-ant-api03-xxxxxxxxxxxxx`

### OpenAI (Alternative)

1. Go to https://platform.openai.com/api-keys
2. Click **"Create new secret key"**
3. Copy: `sk-xxxxxxxxxxxxxxxxxxxxxxxx`

---

## 7️⃣ Monitoring Services (Optional but Recommended)

### Sentry (Error Tracking)

1. Go to https://sentry.io
2. Create new project
3. Select **Python** → **FastAPI**
4. Copy your **DSN**: `https://xxxxx@o123456.ingest.sentry.io/7654321`

### Grafana Cloud (Metrics - Optional)

1. Go to https://grafana.com
2. Sign up for free account
3. Create new stack
4. Get API key from **Configuration** → **API Keys**

---

## 8️⃣ Configure Environment Variables

### Create Your .env File

```bash
cd /c/CODING/Apps/InstaAI-Studio
cp .env.enterprise .env
```

### Edit .env with Your Values

Open `.env` in your editor and replace these values:

```bash
# Application
ENVIRONMENT=production
API_BASE_URL=https://YOUR-RAILWAY-URL.railway.app
FRONTEND_URL=https://YOUR-NETLIFY-URL.netlify.app
SECRET_KEY=YOUR-RANDOM-64-CHAR-STRING  # Generate with: openssl rand -hex 32

# Database (From Step 1)
DATABASE_URL=postgresql://postgres.xxxx:PASSWORD@aws-0-us-west-1.pooler.supabase.com:5432/postgres
SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Redis (From Step 2)
REDIS_URL=rediss://default:PASSWORD@xxx.upstash.io:6379
UPSTASH_REDIS_REST_URL=https://xxx.upstash.io
UPSTASH_REDIS_REST_TOKEN=AXXXxxxxxxxx

# Storage (From Step 3)
STORAGE_PROVIDER=r2
R2_ACCOUNT_ID=your-cloudflare-account-id
R2_ACCESS_KEY_ID=xxxxxxxxxxxxxxxxxxxxx
R2_SECRET_ACCESS_KEY=yyyyyyyyyyyyyyyyyyyyyyyyyy
R2_BUCKET_NAME=instaai-storage
R2_PUBLIC_URL=https://pub-xxxxxxx.r2.dev

# Celery
CELERY_BROKER_URL=${REDIS_URL}
CELERY_RESULT_BACKEND=${REDIS_URL}

# Instagram (From Step 5)
INSTAGRAM_APP_ID=1234567890123456
INSTAGRAM_APP_SECRET=your-app-secret-here
INSTAGRAM_REDIRECT_URI=https://YOUR-RAILWAY-URL.railway.app/api/oauth/callback

# AI (From Step 6)
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
AI_PROVIDER=anthropic

# Monitoring (From Step 7 - Optional)
SENTRY_DSN=https://xxxxx@o123456.ingest.sentry.io/7654321
```

---

## 9️⃣ Initialize Database

### Run Migrations

```bash
cd /c/CODING/Apps/InstaAI-Studio

# Install dependencies
pip install -r requirements.txt

# Initialize Alembic (first time only)
alembic init alembic

# Create initial migration
alembic revision --autogenerate -m "Initial enterprise schema"

# Apply migrations
alembic upgrade head
```

### Verify Database

1. Go to your Supabase project
2. Click **Table Editor**
3. You should see all tables created:
   - users
   - instagram_accounts
   - instagram_posts
   - generated_content
   - post_schedule
   - analytics_cache
   - api_rate_limits
   - audit_logs
   - webhook_logs
   - content_templates

---

## 🔟 Deploy to Railway

### Step 1: Add Environment Variables

1. Go to your Railway project
2. Click **Variables**
3. Click **RAW Editor**
4. Paste your entire `.env` file content
5. Click **Update Variables**

### Step 2: Deploy

1. Railway auto-deploys on push to main
2. Or click **Deploy** → **Deploy Now**
3. Wait for build to complete (3-5 minutes)
4. Check **Deployments** for status

### Step 3: Get Your API URL

1. Go to **Settings** → **Networking**
2. Click **Generate Domain**
3. Your API URL: `https://YOUR-APP.railway.app`
4. Update this in your frontend `.env`:
   ```
   REACT_APP_API_URL=https://YOUR-APP.railway.app
   ```

---

## 1️⃣1️⃣ Test Your Setup

### Test Database Connection

```bash
cd /c/CODING/Apps/InstaAI-Studio
python -c "from src.database.database import engine; print('✅ Database connected!' if engine else '❌ Failed')"
```

### Test Redis Connection

```bash
python -c "import redis; r = redis.from_url('YOUR_REDIS_URL'); r.ping(); print('✅ Redis connected!')"
```

### Test Storage

```bash
python -c "from src.storage.cloud_storage import get_storage; s = get_storage(); print(f'✅ Storage initialized: {s.provider}')"
```

### Test API Locally

```bash
# Start the API
uvicorn src.api.main:app --reload

# In another terminal, test health endpoint
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-12-02T...",
  "database": "connected",
  "services": {
    "instagram_api": "operational",
    "ai_analysis": "operational",
    "content_generation": "operational"
  }
}
```

---

## 🎉 You're Done!

Your enterprise infrastructure is now configured! Here's what you have:

✅ **Supabase PostgreSQL** - Scalable database with connection pooling
✅ **Upstash Redis** - Serverless caching layer
✅ **Cloudflare R2** - Zero-egress object storage
✅ **Railway** - Auto-deploying backend API
✅ **Instagram API** - Connected for OAuth and posting
✅ **AI Services** - Ready for content generation
✅ **Monitoring** - Error tracking and metrics

---

## 📚 Next Steps

1. **Test Instagram OAuth flow**:
   - Visit: `https://YOUR-RAILWAY-URL.railway.app`
   - Click "Connect Instagram"
   - Authorize app
   - Verify account connected in database

2. **Create test content**:
   - Use AI to generate reel ideas
   - Schedule a test post
   - Verify storage upload works

3. **Monitor errors**:
   - Check Sentry dashboard for any issues
   - Review Railway logs

4. **Optimize performance**:
   - Enable caching for analytics
   - Set up CDN for media files
   - Configure rate limiting

---

## 🆘 Troubleshooting

### "Database connection failed"
- Check `DATABASE_URL` format is correct
- Verify password doesn't have special characters (or URL encode them)
- Ensure Supabase project is not paused (free tier pauses after inactivity)

### "Redis connection timeout"
- Verify `REDIS_URL` starts with `rediss://` (with two 's')
- Check Upstash database is in same region
- Firewall might be blocking port 6379

### "R2 upload failed"
- Verify Access Key ID and Secret are correct
- Check bucket name matches exactly
- Ensure bucket has public access enabled (for public URLs)

### "Railway deployment failed"
- Check build logs for Python version issues
- Verify `requirements.txt` has all dependencies
- Make sure environment variables are set

### "Instagram OAuth error"
- Verify redirect URI matches exactly (http vs https, trailing slash)
- Check App ID and Secret are correct
- Ensure app is in correct mode (Development vs Live)

---

## 📞 Support

- Supabase: https://supabase.com/docs
- Upstash: https://docs.upstash.com
- Cloudflare R2: https://developers.cloudflare.com/r2
- Railway: https://docs.railway.app
- Instagram API: https://developers.facebook.com/docs/instagram-api

---

**Your infrastructure is ready to scale from 0 to 10,000+ users!** 🚀
