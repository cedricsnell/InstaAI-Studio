# Windows Setup Guide for InstaAI Studio

## Step 1: Install Python

### Option A: From Microsoft Store (Easiest)
1. Press `Win + S` and search for "Microsoft Store"
2. Search for "Python 3.11"
3. Click "Get" to install
4. Wait for installation to complete

### Option B: From Python.org
1. Visit https://www.python.org/downloads/
2. Download Python 3.11 (or later)
3. Run the installer
4. **IMPORTANT:** Check "Add Python to PATH" ✓
5. Click "Install Now"

### Verify Installation
Open Command Prompt and run:
```cmd
python --version
```
Should show: `Python 3.11.x`

## Step 2: Install FFmpeg

### Option A: Using Chocolatey (Recommended)

**Install Chocolatey first (if you don't have it):**
1. Open PowerShell as Administrator
2. Run:
```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
```

**Then install FFmpeg:**
```powershell
choco install ffmpeg -y
```

### Option B: Manual Installation
1. Download FFmpeg from: https://www.gyan.dev/ffmpeg/builds/
2. Extract to `C:\ffmpeg`
3. Add to PATH:
   - Press `Win + X` → System → Advanced system settings
   - Environment Variables → System Variables → Path → Edit
   - Add: `C:\ffmpeg\bin`
   - Click OK

### Verify Installation
```cmd
ffmpeg -version
```
Should show FFmpeg version info.

## Step 3: Install InstaAI Studio Dependencies

Open Command Prompt in the InstaAI-Studio folder:

```cmd
cd C:\CODING\Apps\InstaAI-Studio

# Install dependencies
pip install -r requirements.txt
```

This will take a few minutes.

## Step 4: Configure Environment

```cmd
# Copy environment template
copy .env.example .env

# Edit with Notepad
notepad .env
```

Add your credentials:
```env
ANTHROPIC_API_KEY=sk-ant-your-key-here
INSTAGRAM_USERNAME=your_instagram_username
INSTAGRAM_PASSWORD=your_instagram_password
DEFAULT_AI_PROVIDER=anthropic
```

Save and close.

## Step 5: Start the Web Server

```cmd
# Simply double-click:
start-web.bat

# Or run manually:
cd src\web
python app.py
```

The server will start at: **http://localhost:8000**

## Step 6: Access the Web Interface

1. Open your browser
2. Go to: http://localhost:8000
3. Login with:
   - Username: `admin`
   - Password: `admin123`

## Troubleshooting

### "pip is not recognized"
```cmd
python -m pip install -r requirements.txt
```

### "Permission denied" when installing
Run Command Prompt as Administrator

### FFmpeg not found after installation
Restart Command Prompt after adding to PATH

### Port 8000 already in use
Edit `src/web/app.py` and change port to 3000 or 5000

### Import errors
Make sure you're in the correct directory:
```cmd
cd C:\CODING\Apps\InstaAI-Studio
```

## Quick Start Commands

```cmd
# Start web server
start-web.bat

# Or use CLI
cd src
python main.py create video.mp4 "Make it a reel"
```

## Next Steps

1. Upload a test video
2. Try creating a reel
3. Check out the examples folder
4. Read the full documentation

Happy creating! 🎬
