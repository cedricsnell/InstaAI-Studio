# InstaAI Studio - Enterprise Architecture (No AWS)

## Architecture Overview

```
┌─────────────────┐
│  Mobile App     │
│ (React Native)  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│           Cloudflare CDN + WAF                  │
│  (DDoS protection, SSL, Rate limiting)          │
└────────┬────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│        FastAPI Backend (Railway/Render)         │
│  ┌──────────────────────────────────────────┐   │
│  │  API Routes                              │   │
│  │  - Auth, Instagram, Content, Schedule    │   │
│  └──────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────┐   │
│  │  Business Logic Layer                    │   │
│  │  - Services, Managers, Processors        │   │
│  └──────────────────────────────────────────┘   │
└────┬─────────┬─────────┬─────────┬──────────────┘
     │         │         │         │
     ▼         ▼         ▼         ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────────┐
│Supabase│ │Upstash │ │Cloudfl.│ │ Celery     │
│Postgres│ │ Redis  │ │   R2   │ │ Workers    │
│        │ │        │ │Storage │ │            │
└────────┘ └────────┘ └────────┘ └────────────┘
     │                      │         │
     │                      │         ▼
     │                      │    ┌────────────┐
     │                      │    │   Redis    │
     │                      │    │   Broker   │
     │                      │    └────────────┘
     ▼                      ▼
┌────────────┐        ┌──────────────┐
│ Monitoring │        │  Cloudinary  │
│  - Sentry  │        │ Media Process│
│  - Grafana │        └──────────────┘
└────────────┘
```

## Technology Stack

### 1. Database Layer
**Primary Database: Supabase (PostgreSQL)**
- **Why**: Managed PostgreSQL with auto-scaling, built-in auth, real-time subscriptions
- **Free Tier**: 500MB database, 2GB bandwidth
- **Paid Tier**: $25/month for 8GB database, 50GB bandwidth
- **Features**:
  - Automatic backups
  - Connection pooling (PgBouncer)
  - Row-level security (RLS)
  - Real-time subscriptions via WebSockets
  - PostGIS for location data (future feature)
  - Full-text search built-in

**Alternative**: PlanetScale (MySQL) - $29/month

### 2. Caching Layer
**Redis: Upstash Redis**
- **Why**: Serverless Redis with per-request pricing
- **Free Tier**: 10,000 commands/day
- **Paid**: Pay-per-request ($0.20 per 100k requests)
- **Features**:
  - Global replication
  - Durable storage
  - REST API support
  - Low latency edge caching

**Use Cases**:
- Session storage
- Instagram API response caching (rate limit management)
- Real-time analytics aggregation
- Job queue for Celery
- Feature flags
- Rate limiting

### 3. Object Storage
**Cloudflare R2**
- **Why**: S3-compatible, zero egress fees, cheaper than AWS
- **Pricing**: $0.015/GB storage, $0 egress
- **Features**:
  - S3-compatible API (minimal code changes)
  - Global CDN distribution
  - No bandwidth charges
  - Automatic HTTPS
  - Custom domains

**Alternative**: Supabase Storage (integrated with Supabase)
- 1GB free tier
- Integrated with Postgres (file metadata)
- Automatic image optimization

**Storage Structure**:
```
r2://instaai-storage/
├── users/{user_id}/
│   ├── uploads/           # User-uploaded media
│   ├── generated/         # AI-generated content
│   └── thumbnails/        # Optimized thumbnails
├── instagram/{account_id}/
│   ├── synced_media/      # Downloaded Instagram posts
│   └── profile_images/    # Profile pictures
└── system/
    ├── temp/              # Temporary files (auto-delete after 24h)
    └── backups/           # Database backups
```

### 4. Media Processing
**Cloudinary**
- **Why**: Best-in-class image/video optimization and transformations
- **Free Tier**: 25GB storage, 25GB bandwidth
- **Features**:
  - Automatic format optimization (WebP, AVIF)
  - Video transcoding
  - AI-powered cropping and tagging
  - Responsive image generation
  - Video thumbnail extraction
  - Watermarking

**Alternative**: ImageKit.io ($0/month for 20GB bandwidth)

### 5. Backend Hosting
**Railway**
- **Why**: Simple deployment, automatic scaling, generous free tier
- **Free Tier**: $5 credit/month (enough for development)
- **Paid**: Pay-per-use (~$20-50/month for production)
- **Features**:
  - One-click deployment from GitHub
  - Automatic HTTPS
  - Environment variable management
  - Database provisioning
  - Metrics and logs
  - Horizontal scaling

**Alternative**: Render.com
- Free tier for web services
- $7/month for starter tier
- Auto-deploy from GitHub

### 6. Background Jobs
**Celery + Redis (Upstash)**
- **Task Queue**: Celery with Upstash Redis as broker
- **Workers**: Deployed on Railway as separate service
- **Monitoring**: Flower dashboard

**Job Types**:
1. **Scheduled Tasks** (Celery Beat):
   - Sync Instagram posts every 6 hours
   - Refresh access tokens before expiry
   - Generate analytics reports daily
   - Clean up temp files
   - Send scheduled posts

2. **Async Tasks**:
   - AI content generation (can take 30-60s)
   - Video processing and rendering
   - Bulk media downloads
   - Email notifications
   - Webhook processing

### 7. Monitoring & Logging
**Sentry** (Error Tracking)
- Free tier: 5k errors/month
- Real-time error alerts
- Performance monitoring
- Release tracking

**Grafana Cloud** (Metrics)
- Free tier: 10k series
- Custom dashboards
- Alerting
- Logs aggregation

**LogTail** (Logging)
- Structured logging
- Real-time log streaming
- Search and filtering

### 8. CDN & Security
**Cloudflare**
- **Free Tier Includes**:
  - Global CDN
  - DDoS protection
  - SSL/TLS certificates
  - Web Application Firewall (WAF)
  - Rate limiting
  - Bot protection
  - Analytics

## Database Schema (Enhanced)

### Core Tables

```sql
-- Users with enhanced fields
users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255),
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,

    -- OAuth
    google_id VARCHAR(255) UNIQUE,
    facebook_id VARCHAR(255) UNIQUE,
    oauth_provider VARCHAR(50),

    -- Subscription
    subscription_tier VARCHAR(50) DEFAULT 'free',
    subscription_status VARCHAR(50) DEFAULT 'active',
    subscription_expires_at TIMESTAMP,
    stripe_customer_id VARCHAR(255),

    -- Usage tracking
    content_generated_count INT DEFAULT 0,
    posts_scheduled_count INT DEFAULT 0,
    monthly_quota_remaining INT DEFAULT 10,
    quota_reset_date DATE,

    -- Metadata
    timezone VARCHAR(100) DEFAULT 'UTC',
    language VARCHAR(10) DEFAULT 'en',
    onboarding_completed BOOLEAN DEFAULT false,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Instagram accounts
instagram_accounts (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,

    instagram_user_id VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(255) NOT NULL,
    account_type VARCHAR(50),

    -- OAuth tokens (encrypted)
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_expires_at TIMESTAMP NOT NULL,

    -- Account metrics
    profile_picture_url TEXT,
    followers_count INT DEFAULT 0,
    following_count INT DEFAULT 0,
    media_count INT DEFAULT 0,
    biography TEXT,
    website VARCHAR(500),

    -- Sync status
    is_active BOOLEAN DEFAULT true,
    last_synced_at TIMESTAMP,
    sync_error TEXT,
    next_sync_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    INDEX idx_user_id (user_id),
    INDEX idx_instagram_user_id (instagram_user_id),
    INDEX idx_next_sync (next_sync_at)
);

-- Instagram posts (synced from API)
instagram_posts (
    id SERIAL PRIMARY KEY,
    instagram_account_id INT REFERENCES instagram_accounts(id) ON DELETE CASCADE,

    media_id VARCHAR(255) UNIQUE NOT NULL,
    media_type VARCHAR(50),
    media_url TEXT,
    thumbnail_url TEXT,
    permalink TEXT,
    caption TEXT,
    timestamp TIMESTAMP NOT NULL,

    -- Engagement (updated periodically)
    likes_count INT DEFAULT 0,
    comments_count INT DEFAULT 0,
    saves_count INT DEFAULT 0,
    shares_count INT DEFAULT 0,
    reach INT DEFAULT 0,
    impressions INT DEFAULT 0,
    engagement_rate DECIMAL(5,2) DEFAULT 0.00,

    -- AI Analysis
    ai_tags JSONB,
    ai_sentiment VARCHAR(50),
    ai_content_themes JSONB,
    performance_score DECIMAL(5,2),

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    INDEX idx_account_id (instagram_account_id),
    INDEX idx_media_id (media_id),
    INDEX idx_timestamp (timestamp DESC),
    INDEX idx_engagement_rate (engagement_rate DESC)
);

-- AI-generated content
generated_content (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    instagram_account_id INT REFERENCES instagram_accounts(id) ON DELETE SET NULL,

    content_type VARCHAR(50) NOT NULL,
    title VARCHAR(500),
    description TEXT,

    -- Files (Cloudflare R2 URLs)
    file_url TEXT,
    thumbnail_url TEXT,
    cloudflare_key VARCHAR(500),

    -- AI generation metadata
    source_post_ids JSONB,
    ai_prompt TEXT,
    ai_model VARCHAR(100),
    generation_config JSONB,
    processing_time_seconds INT,

    -- Content details
    suggested_caption TEXT,
    suggested_hashtags JSONB,
    best_posting_time TIMESTAMP,
    target_audience VARCHAR(100),

    -- Status
    status VARCHAR(50) DEFAULT 'pending',
    status_message TEXT,

    -- Performance prediction
    predicted_engagement_rate DECIMAL(5,2),
    predicted_reach INT,
    confidence_score DECIMAL(5,2),

    -- Actual performance (after publishing)
    actual_engagement_rate DECIMAL(5,2),
    actual_reach INT,
    published_post_id INT REFERENCES instagram_posts(id),

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    approved_at TIMESTAMP,
    published_at TIMESTAMP,

    INDEX idx_user_id (user_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at DESC)
);

-- Post scheduling
post_schedule (
    id SERIAL PRIMARY KEY,
    instagram_account_id INT REFERENCES instagram_accounts(id) ON DELETE CASCADE,
    generated_content_id INT REFERENCES generated_content(id) ON DELETE SET NULL,

    scheduled_time TIMESTAMP NOT NULL,
    timezone VARCHAR(100) DEFAULT 'UTC',
    post_type VARCHAR(50) NOT NULL,

    -- Content
    media_url TEXT,
    caption TEXT,
    hashtags JSONB,
    location_id VARCHAR(255),
    collaborators JSONB,

    -- Status
    status VARCHAR(50) DEFAULT 'scheduled',
    status_message TEXT,
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 3,

    -- Result
    instagram_post_id VARCHAR(255),
    posted_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    INDEX idx_scheduled_time (scheduled_time),
    INDEX idx_status (status),
    INDEX idx_account_id (instagram_account_id)
);

-- Analytics cache
analytics_cache (
    id SERIAL PRIMARY KEY,
    instagram_account_id INT REFERENCES instagram_accounts(id) ON DELETE CASCADE,

    metric_type VARCHAR(100) NOT NULL,
    metric_period VARCHAR(50) NOT NULL,

    data JSONB NOT NULL,

    cached_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,

    INDEX idx_account_metric (instagram_account_id, metric_type, metric_period),
    INDEX idx_expires_at (expires_at)
);

-- API rate limits tracking
api_rate_limits (
    id SERIAL PRIMARY KEY,
    instagram_account_id INT REFERENCES instagram_accounts(id) ON DELETE CASCADE,

    endpoint VARCHAR(255) NOT NULL,
    requests_count INT DEFAULT 0,
    window_start TIMESTAMP NOT NULL,
    window_end TIMESTAMP NOT NULL,

    UNIQUE(instagram_account_id, endpoint, window_start)
);

-- Audit logs
audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE SET NULL,

    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id INT,

    old_values JSONB,
    new_values JSONB,

    ip_address INET,
    user_agent TEXT,

    created_at TIMESTAMP DEFAULT NOW(),

    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at DESC),
    INDEX idx_action (action)
);
```

## Environment Variables

```bash
# Database (Supabase)
DATABASE_URL=postgresql://user:pass@db.supabase.co:5432/postgres
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=your_anon_key
SUPABASE_SERVICE_KEY=your_service_key

# Redis (Upstash)
REDIS_URL=rediss://:password@global.upstash.io:6379
UPSTASH_REDIS_REST_URL=https://xxx.upstash.io
UPSTASH_REDIS_REST_TOKEN=your_token

# Object Storage (Cloudflare R2)
R2_ACCOUNT_ID=your_account_id
R2_ACCESS_KEY_ID=your_access_key
R2_SECRET_ACCESS_KEY=your_secret_key
R2_BUCKET_NAME=instaai-storage
R2_PUBLIC_URL=https://storage.instaai.com

# Media Processing (Cloudinary)
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret

# Background Jobs (Celery)
CELERY_BROKER_URL=${REDIS_URL}
CELERY_RESULT_BACKEND=${REDIS_URL}
CELERY_TASK_ALWAYS_EAGER=false

# Monitoring
SENTRY_DSN=https://xxx@sentry.io/xxx
GRAFANA_API_KEY=your_api_key

# Instagram API
INSTAGRAM_CLIENT_ID=your_client_id
INSTAGRAM_CLIENT_SECRET=your_client_secret
INSTAGRAM_REDIRECT_URI=https://api.instaai.com/callback

# AI Services
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-ant-xxx

# Application
SECRET_KEY=your_secret_key_for_jwt
API_BASE_URL=https://api.instaai.com
FRONTEND_URL=https://app.instaai.com
ENVIRONMENT=production
LOG_LEVEL=INFO
```

## Deployment Architecture

### Railway Services

```yaml
# railway.json
{
  "services": [
    {
      "name": "api",
      "source": {
        "type": "dockerfile",
        "dockerfile": "Dockerfile"
      },
      "deploy": {
        "startCommand": "uvicorn src.api.main:app --host 0.0.0.0 --port $PORT",
        "healthcheckPath": "/health",
        "restartPolicyType": "ON_FAILURE"
      },
      "env": {
        "PORT": "8000",
        "WORKERS": "4"
      }
    },
    {
      "name": "celery-worker",
      "source": {
        "type": "dockerfile",
        "dockerfile": "Dockerfile.worker"
      },
      "deploy": {
        "startCommand": "celery -A src.tasks.celery_app worker --loglevel=info",
        "replicas": 2
      }
    },
    {
      "name": "celery-beat",
      "source": {
        "type": "dockerfile",
        "dockerfile": "Dockerfile.worker"
      },
      "deploy": {
        "startCommand": "celery -A src.tasks.celery_app beat --loglevel=info",
        "replicas": 1
      }
    }
  ]
}
```

## Cost Estimation (Monthly)

### Development/MVP ($0-30/month)
- Supabase: Free tier
- Upstash Redis: Free tier (10k requests/day)
- Cloudflare R2: ~$0 (minimal storage)
- Railway: $5 credit (free)
- Cloudinary: Free tier
- **Total: $0-5/month**

### Production (100 users) ($50-100/month)
- Supabase Pro: $25
- Upstash: $10 (100k requests/day)
- Cloudflare R2: $5 (storage + requests)
- Railway: $20-40 (2 services)
- Cloudinary: Free tier
- Sentry: Free tier
- **Total: $60-80/month**

### Production (1000 users) ($200-300/month)
- Supabase Pro: $25
- Upstash: $30 (1M requests/day)
- Cloudflare R2: $20
- Railway: $100-150 (scaled services)
- Cloudinary Pro: $89
- Sentry Pro: $26
- **Total: $290-340/month**

### Production (10k users) ($800-1200/month)
- Supabase Team: $599
- Upstash Pro: $150
- Cloudflare R2: $100
- Railway: $300-500
- Cloudinary Advanced: $224
- Sentry Business: $80
- **Total: $1,453-1,653/month**

## Migration from AWS (if needed)

Since you don't want AWS, here's how our stack compares:

| AWS Service | Replacement | Why Better |
|------------|-------------|------------|
| RDS | Supabase | Easier setup, built-in auth, real-time features |
| ElastiCache | Upstash | Serverless, pay-per-use, no cluster management |
| S3 | Cloudflare R2 | Zero egress fees, 90% cheaper |
| Lambda | Railway/Render | Simpler deployment, no cold starts |
| CloudWatch | Sentry + Grafana | Better UX, free tiers |
| CloudFront | Cloudflare CDN | Faster, more features on free tier |
| SQS | Redis (Celery) | Simpler, real-time |

## Scalability Plan

### Phase 1: MVP (0-100 users)
- Single Railway service
- Supabase free tier
- Local development workflow

### Phase 2: Growth (100-1000 users)
- Separate API and worker services
- Upgrade to Supabase Pro
- Add caching layer
- Implement CDN

### Phase 3: Scale (1000-10k users)
- Horizontal scaling (multiple workers)
- Database read replicas
- Advanced caching strategies
- Rate limiting per user tier

### Phase 4: Enterprise (10k+ users)
- Multi-region deployment
- Database sharding by user_id
- Dedicated Redis cluster
- Advanced monitoring and alerts

## Security Measures

1. **Database**:
   - Row-level security (RLS) in Supabase
   - Encrypted connections (SSL)
   - Regular backups (automated)
   - Secrets in environment variables

2. **API**:
   - JWT authentication
   - Rate limiting (per IP, per user)
   - CORS configuration
   - Input validation (Pydantic)
   - SQL injection protection (SQLAlchemy)

3. **Storage**:
   - Signed URLs for private files
   - Automatic virus scanning (Cloudinary)
   - File type validation
   - Size limits

4. **Monitoring**:
   - Error tracking (Sentry)
   - Security alerts
   - Audit logs for sensitive operations
   - Failed login attempts tracking

## Next Steps

1. ✅ Design complete architecture
2. Set up Supabase database
3. Configure Upstash Redis
4. Set up Cloudflare R2 storage
5. Deploy to Railway
6. Configure Celery workers
7. Implement monitoring
8. Load testing
9. Documentation
10. CI/CD pipeline
