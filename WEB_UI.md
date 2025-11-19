# Web UI Guide

InstaAI Studio includes a modern web interface that can be accessed by anyone with a browser!

## 🌐 Features

- **Modern UI** - Instagram-inspired design
- **Drag & Drop** - Easy file uploads
- **Natural Language** - Describe edits in plain English
- **Multi-User** - Support for multiple users with authentication
- **File Management** - View, download, and delete files
- **Scheduling** - Schedule posts directly from the browser
- **Real-time Status** - See processing progress
- **Mobile Friendly** - Works on phones and tablets

## 🚀 Quick Start

### Local Development

1. **Start the server**:

```bash
# Windows
start-web.bat

# Mac/Linux
chmod +x start-web.sh
./start-web.sh
```

2. **Access the web interface**:
   - Open browser: http://localhost:8000
   - Login: `admin` / `admin123`

3. **Try it out**:
   - Upload a video
   - Add editing commands
   - Create content
   - Download or post to Instagram

### Production Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for cloud hosting options.

## 📱 Using the Web Interface

### Login Screen

Default credentials:
- **Username**: admin
- **Password**: admin123

⚠️ **Important**: Change default credentials in production!

### Create Content Tab

**Step 1: Upload Video/Image**
- Drag & drop files into the upload area
- Or click to browse files
- Supports: MP4, MOV, JPG, PNG

**Step 2: Add Commands**
- Type natural language commands
- Click "+" to add more commands
- Use quick command buttons for common edits

Example commands:
```
Make it a vertical reel
Add jump cuts to remove pauses
Add upbeat music at 50% volume
Add text 'Check this out!' at the top
Speed up by 1.5x
```

**Step 3: Choose Content Type**
- **Reel** - 9:16 vertical video
- **Story** - 9:16 vertical (15s)
- **Feed Post** - 1:1 square
- **Carousel** - Multiple 1:1 images/videos

**Step 4: Create**
- Click "Create Content"
- Wait for processing (may take a few minutes)
- Download or schedule post

### Manage Files Tab

**View Your Files**
- See all created content
- View uploads
- Download any file
- Delete old files

**File Actions**
- **Download** - Save to your device
- **Delete** - Remove from server

### Schedule Posts Tab

**Schedule New Post**
1. Select a created file
2. Choose post type (Reel, Story, Photo, Video)
3. Set schedule time
4. Add caption and hashtags
5. Click "Schedule Post"

**View Scheduled Posts**
- See all upcoming posts
- Cancel scheduled posts
- View post details

**Time Formats**
- Local time picker in browser
- Or use natural language (via API)

### Account Tab

**Instagram Account Info**
- View follower count
- See account details
- Verify connection status

**Configuration Status**
- Check AI configuration
- Verify Instagram connection
- View scheduler status

## 🔐 User Management

### Adding New Users (Admin Only)

Via API:
```bash
curl -X POST http://localhost:8000/api/admin/users \
  -u admin:admin123 \
  -H "Content-Type: application/json" \
  -d '{"username": "newuser", "password": "password123"}'
```

### Changing Passwords

Edit `src/web/app.py`:

```python
import hashlib

# Generate password hash
password = "your_new_password"
password_hash = hashlib.sha256(password.encode()).hexdigest()

# Update USERS dict
USERS = {
    "admin": {
        "password_hash": password_hash,
        "role": "admin"
    }
}
```

For production, use a proper database and password hashing library like `bcrypt`.

## 🔗 API Endpoints

The web UI uses these API endpoints (also available for programmatic access):

### Authentication
- All endpoints require HTTP Basic Auth
- Header: `Authorization: Basic base64(username:password)`

### File Management

**Upload File**
```http
POST /api/upload
Content-Type: multipart/form-data

file: <binary>
```

**List Files**
```http
GET /api/files
```

**Download File**
```http
GET /api/download/{filename}
```

**Delete File**
```http
DELETE /api/files/{filename}
```

### Content Creation

**Create Content**
```http
POST /api/create
Content-Type: application/json

{
  "commands": ["Make it a reel", "Add music"],
  "content_type": "reel",
  "output_filename": "my_reel.mp4"
}
```

### Instagram Posting

**Post Content**
```http
POST /api/post
Content-Type: application/json

{
  "media_filename": "my_reel.mp4",
  "post_type": "reel",
  "caption": "Check this out!",
  "hashtags": ["viral", "reel"],
  "scheduled_time": "2024-01-20T15:00:00"  // Optional
}
```

### Scheduling

**Get Scheduled Posts**
```http
GET /api/scheduled?status=scheduled
```

**Cancel Scheduled Post**
```http
DELETE /api/scheduled/{job_id}
```

### Account

**Get Instagram Account Info**
```http
GET /api/account
```

**Get Configuration**
```http
GET /api/config
```

### Health Check

**Health Check**
```http
GET /api/health
```

## 📊 API Documentation

FastAPI automatically generates interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

These provide:
- Interactive API testing
- Request/response examples
- Schema documentation
- Authentication testing

## 🛠️ Customization

### Change Default Port

Edit `src/web/app.py`:

```python
if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=3000,  # Change port here
        log_level="info"
    )
```

### Add Custom Branding

Edit `src/web/static/style.css`:

```css
:root {
    --primary: #your-color;
    --secondary: #your-color;
}
```

Edit `src/web/static/index.html`:

```html
<h1>🎬 Your Brand Name</h1>
```

### Enable CORS for Specific Domains

Edit `src/web/app.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 🔒 Security Best Practices

### Production Checklist

- [ ] Change default credentials
- [ ] Use HTTPS (SSL certificate)
- [ ] Use environment variables for secrets
- [ ] Enable rate limiting
- [ ] Use proper database (PostgreSQL)
- [ ] Implement proper password hashing (bcrypt)
- [ ] Add CSRF protection
- [ ] Validate file uploads
- [ ] Set file size limits
- [ ] Enable logging
- [ ] Use secure session management

### Rate Limiting

Add to `requirements.txt`:
```
slowapi==0.1.9
```

Add to `src/web/app.py`:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/api/create")
@limiter.limit("5/minute")
async def create_content(...):
    ...
```

### File Upload Limits

Edit `src/web/app.py`:

```python
from fastapi import UploadFile, File

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    content = await file.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large")

    # ... rest of code
```

## 🌐 Multi-User Access

### Sharing with Team

1. **Deploy to cloud** (see DEPLOYMENT.md)
2. **Get public URL**: `https://your-app.example.com`
3. **Create user accounts** for each team member
4. **Share credentials** securely (use password manager)

### User Isolation

Each user's files are prefixed with their username:
- `user1_video.mp4`
- `user2_reel.mp4`

Users can only access their own files.

### Collaborative Workflow

**Content Creator Flow:**
1. Upload raw videos
2. Add editing commands
3. Create content
4. Download for review

**Social Media Manager Flow:**
1. Log in to same instance
2. Review created content
3. Schedule posts
4. Monitor scheduled posts

## 📱 Mobile Access

The web UI is fully responsive and works on:
- **Phones** (iOS, Android)
- **Tablets** (iPad, Android tablets)
- **Desktop** (Windows, Mac, Linux)

### Mobile Tips

- Use landscape mode for better editing experience
- Upload videos directly from phone camera
- Schedule posts on the go
- Monitor scheduled posts anywhere

## 🚀 Performance Tips

### For Large Files

1. **Increase timeout**:
```python
# In app.py
import uvicorn

uvicorn.run(
    app,
    timeout_keep_alive=300  # 5 minutes
)
```

2. **Use background tasks**:
```python
from fastapi import BackgroundTasks

@app.post("/api/create")
async def create_content(background_tasks: BackgroundTasks, ...):
    background_tasks.add_task(create_video_task, ...)
    return {"message": "Processing started"}
```

### Caching

Add Redis for caching:
```bash
pip install redis
```

```python
import redis

cache = redis.Redis(host='localhost', port=6379)
```

## 🐛 Troubleshooting

### Web UI Not Loading

1. Check server is running:
```bash
curl http://localhost:8000/api/health
```

2. Check firewall allows port 8000

3. Check logs:
```bash
tail -f logs/app.log
```

### Upload Fails

1. Check file size limits
2. Verify FFmpeg is installed
3. Check disk space
4. Review error in browser console (F12)

### Login Fails

1. Verify credentials are correct
2. Check HTTP Basic Auth header
3. Clear browser cache
4. Try incognito mode

### Processing Slow

1. Reduce video quality
2. Use shorter videos
3. Upgrade server resources
4. Enable caching

## 📚 Examples

### Example: Batch Upload via API

```python
import requests
from pathlib import Path

# Login
auth = ('admin', 'admin123')
base_url = 'http://localhost:8000'

# Upload multiple files
videos = Path('raw_videos').glob('*.mp4')

for video in videos:
    with open(video, 'rb') as f:
        files = {'file': f}
        response = requests.post(
            f'{base_url}/api/upload',
            files=files,
            auth=auth
        )
        print(f'Uploaded: {video.name}')
```

### Example: Automated Content Creation

```python
import requests
import time

auth = ('admin', 'admin123')
base_url = 'http://localhost:8000'

# Create multiple reels from uploaded videos
commands = [
    "Make it a reel",
    "Add jump cuts",
    "Add upbeat music at 50% volume",
    "Speed up by 1.3x"
]

response = requests.post(
    f'{base_url}/api/create',
    json={
        'commands': commands,
        'content_type': 'reel'
    },
    auth=auth
)

if response.ok:
    result = response.json()
    print(f"Created: {result['output_filename']}")
```

## 🎓 Advanced Usage

### Webhook Integration

Add webhooks to notify when content is ready:

```python
import requests

@app.post("/api/create")
async def create_content(...):
    # ... create content

    # Send webhook notification
    webhook_url = os.getenv('WEBHOOK_URL')
    if webhook_url:
        requests.post(webhook_url, json={
            'event': 'content_created',
            'filename': output_filename
        })
```

### Integration with Other Services

- **Zapier**: Use webhooks to trigger Zapier workflows
- **Slack**: Send notifications to Slack channels
- **Discord**: Post updates to Discord servers
- **Email**: Send email when content is ready

---

Happy creating with the Web UI! 🎬✨
