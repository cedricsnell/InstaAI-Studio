# Deployment Guide

Deploy InstaAI Studio to the cloud so anyone can access it from anywhere!

## Quick Overview

The web application consists of:
- **FastAPI Backend** (Python) - handles video processing and Instagram posting
- **Static Frontend** (HTML/CSS/JS) - modern web interface
- **File Storage** - for uploaded videos and created content
- **Database** - SQLite for scheduling (can upgrade to PostgreSQL)

## Deployment Options

### Option 1: DigitalOcean App Platform (Easiest)
**Cost:** ~$12/month
**Best for:** Quick deployment, managed service

### Option 2: AWS EC2 / Google Cloud / Azure VM
**Cost:** ~$10-30/month
**Best for:** Full control, scalability

### Option 3: Heroku
**Cost:** ~$7-25/month
**Best for:** Simple deployment

### Option 4: Docker + Any Cloud
**Cost:** Varies
**Best for:** Portability, consistency

---

## Option 1: DigitalOcean App Platform

### Step 1: Prepare Your Repository

```bash
# Push your code to GitHub
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/yourusername/instaai-studio.git
git push -u origin main
```

### Step 2: Create Deployment Files

Create `runtime.txt`:
```txt
python-3.11
```

Create `Procfile`:
```
web: cd src/web && uvicorn app:app --host 0.0.0.0 --port ${PORT}
```

### Step 3: Deploy to DigitalOcean

1. Go to [DigitalOcean App Platform](https://cloud.digitalocean.com/apps)
2. Click "Create App"
3. Connect your GitHub repository
4. Configure:
   - **Environment:** Python
   - **Build Command:** `pip install -r requirements.txt`
   - **Run Command:** `cd src/web && uvicorn app:app --host 0.0.0.0 --port 8000`

5. Add Environment Variables:
   ```
   ANTHROPIC_API_KEY=your_key
   INSTAGRAM_USERNAME=your_username
   INSTAGRAM_PASSWORD=your_password
   ```

6. Deploy!

### Step 4: Access Your App

Your app will be available at: `https://your-app-name.ondigitalocean.app`

---

## Option 2: AWS EC2 Deployment

### Step 1: Launch EC2 Instance

1. Go to AWS EC2 Console
2. Launch instance:
   - **AMI:** Ubuntu 22.04 LTS
   - **Instance Type:** t3.medium (2 vCPU, 4 GB RAM)
   - **Storage:** 20 GB
   - **Security Group:** Allow ports 22 (SSH), 80 (HTTP), 443 (HTTPS)

### Step 2: Connect and Setup

```bash
# SSH into your instance
ssh -i your-key.pem ubuntu@your-instance-ip

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install python3-pip python3-venv ffmpeg git nginx -y

# Clone your repository
git clone https://github.com/yourusername/instaai-studio.git
cd instaai-studio

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env  # Add your credentials
```

### Step 3: Setup Systemd Service

Create `/etc/systemd/system/instaai.service`:

```ini
[Unit]
Description=InstaAI Studio Web App
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/instaai-studio/src/web
Environment="PATH=/home/ubuntu/instaai-studio/venv/bin"
ExecStart=/home/ubuntu/instaai-studio/venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable instaai
sudo systemctl start instaai
sudo systemctl status instaai
```

### Step 4: Configure Nginx

Create `/etc/nginx/sites-available/instaai`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 100M;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/instaai /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Step 5: Setup SSL with Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com
```

Your app is now available at: `https://your-domain.com`

---

## Option 3: Heroku Deployment

### Step 1: Prepare Files

Create `Procfile`:
```
web: cd src/web && uvicorn app:app --host 0.0.0.0 --port $PORT
```

Create `runtime.txt`:
```
python-3.11.0
```

Create `heroku.yml`:
```yaml
build:
  docker:
    web: Dockerfile
run:
  web: cd src/web && uvicorn app:app --host 0.0.0.0 --port $PORT
```

### Step 2: Deploy

```bash
# Install Heroku CLI
# https://devcenter.heroku.com/articles/heroku-cli

# Login
heroku login

# Create app
heroku create your-app-name

# Set environment variables
heroku config:set ANTHROPIC_API_KEY=your_key
heroku config:set INSTAGRAM_USERNAME=your_username
heroku config:set INSTAGRAM_PASSWORD=your_password

# Deploy
git push heroku main

# Open app
heroku open
```

---

## Option 4: Docker Deployment

### Step 1: Create Dockerfile

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "src.web.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Step 2: Create docker-compose.yml

```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - INSTAGRAM_USERNAME=${INSTAGRAM_USERNAME}
      - INSTAGRAM_PASSWORD=${INSTAGRAM_PASSWORD}
    volumes:
      - ./output:/app/output
      - ./temp:/app/temp
      - ./data:/app/data
    restart: unless-stopped
```

### Step 3: Build and Run

```bash
# Build image
docker build -t instaai-studio .

# Run container
docker run -d \
  -p 8000:8000 \
  -e ANTHROPIC_API_KEY=your_key \
  -e INSTAGRAM_USERNAME=your_username \
  -e INSTAGRAM_PASSWORD=your_password \
  --name instaai \
  instaai-studio

# Or use docker-compose
docker-compose up -d
```

### Step 4: Deploy to Any Cloud

You can now deploy this Docker container to:
- **Google Cloud Run**
- **AWS ECS**
- **Azure Container Instances**
- **DigitalOcean Container Registry**

Example for Google Cloud Run:

```bash
# Build and tag
docker build -t gcr.io/your-project/instaai-studio .

# Push to Google Container Registry
docker push gcr.io/your-project/instaai-studio

# Deploy to Cloud Run
gcloud run deploy instaai-studio \
  --image gcr.io/your-project/instaai-studio \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars ANTHROPIC_API_KEY=your_key
```

---

## Production Considerations

### 1. Security

**Change Default Credentials:**
```python
# In src/web/app.py, update USERS dict or use database
```

**Use Environment Variables:**
Never commit credentials to git. Always use environment variables.

**Enable HTTPS:**
Always use SSL certificates in production.

**Add Rate Limiting:**
```bash
pip install slowapi
```

### 2. Database

**Upgrade to PostgreSQL for Production:**

```bash
# Install PostgreSQL
sudo apt install postgresql

# Update Config
DATABASE_URL=postgresql://user:password@localhost/instaai
```

Update `src/scheduler/post_scheduler.py`:
```python
engine = create_engine(os.getenv('DATABASE_URL'))
```

### 3. File Storage

**Use Object Storage for Large Files:**

**AWS S3:**
```python
import boto3
s3 = boto3.client('s3')
s3.upload_file('local_file.mp4', 'bucket-name', 'remote_file.mp4')
```

**Google Cloud Storage:**
```python
from google.cloud import storage
client = storage.Client()
bucket = client.bucket('your-bucket')
blob = bucket.blob('remote_file.mp4')
blob.upload_from_filename('local_file.mp4')
```

### 4. Scaling

**Use Background Workers:**

Install Celery for background tasks:
```bash
pip install celery redis
```

**Load Balancing:**

Deploy multiple instances behind a load balancer.

### 5. Monitoring

**Add Logging:**
```python
import logging
logging.basicConfig(level=logging.INFO)
```

**Health Checks:**
Already included at `/api/health`

**Error Tracking:**
```bash
pip install sentry-sdk
```

---

## Quick Start Script

Create `deploy.sh`:

```bash
#!/bin/bash

echo "InstaAI Studio - Quick Deploy Script"
echo "===================================="

# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3-pip python3-venv ffmpeg git nginx certbot python3-certbot-nginx

# Clone repo
git clone https://github.com/yourusername/instaai-studio.git
cd instaai-studio

# Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
echo "Please edit .env with your credentials:"
nano .env

# Create systemd service
sudo tee /etc/systemd/system/instaai.service > /dev/null <<EOF
[Unit]
Description=InstaAI Studio
After=network.target

[Service]
User=$USER
WorkingDirectory=$(pwd)/src/web
Environment="PATH=$(pwd)/venv/bin"
ExecStart=$(pwd)/venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000

[Install]
WantedBy=multi-user.target
EOF

# Start service
sudo systemctl enable instaai
sudo systemctl start instaai

echo "InstaAI Studio is running on http://localhost:8000"
echo "Configure Nginx for production deployment"
```

Make executable and run:
```bash
chmod +x deploy.sh
./deploy.sh
```

---

## Troubleshooting

### Port Already in Use
```bash
# Find process using port 8000
sudo lsof -i :8000
# Kill process
sudo kill -9 <PID>
```

### FFmpeg Not Found
```bash
sudo apt install ffmpeg
```

### Out of Memory
Increase instance size or add swap:
```bash
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Logs
```bash
# View systemd logs
sudo journalctl -u instaai -f

# View Nginx logs
sudo tail -f /var/log/nginx/error.log
```

---

## Cost Estimates

| Platform | Cost/Month | Best For |
|----------|-----------|----------|
| DigitalOcean App Platform | $12 | Managed, easy |
| AWS EC2 t3.medium | $30 | Full control |
| Heroku Dyno | $7-25 | Simple deploy |
| Google Cloud Run | Pay per use | Low traffic |
| Self-hosted VPS | $5-15 | Budget friendly |

---

## Support

For deployment issues:
- Check logs: `sudo journalctl -u instaai -f`
- Test API: `curl http://localhost:8000/api/health`
- Verify FFmpeg: `ffmpeg -version`

Happy deploying! 🚀
