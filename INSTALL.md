# Installation Guide

Detailed installation instructions for InstaAI Studio on different platforms.

## Prerequisites

- **Python 3.8 or higher**
- **FFmpeg** (required for video processing)
- **Git** (for cloning the repository)
- **Anthropic API key** or **OpenAI API key**
- **Instagram account**

## Platform-Specific Installation

### Windows

#### 1. Install Python

Download from [python.org](https://www.python.org/downloads/) or use Microsoft Store.

```powershell
# Verify installation
python --version
```

#### 2. Install FFmpeg

**Option A: Using Chocolatey (Recommended)**
```powershell
# Install Chocolatey first if you haven't:
# https://chocolatey.org/install

choco install ffmpeg
```

**Option B: Manual Installation**
1. Download from [ffmpeg.org](https://ffmpeg.org/download.html)
2. Extract to `C:\ffmpeg`
3. Add `C:\ffmpeg\bin` to System PATH

**Verify FFmpeg**:
```powershell
ffmpeg -version
```

#### 3. Clone and Install InstaAI Studio

```powershell
# Clone repository
git clone https://github.com/yourusername/instaai-studio.git
cd instaai-studio

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

#### 4. Configure

```powershell
# Copy environment template
copy .env.example .env

# Edit .env with your credentials
notepad .env
```

### macOS

#### 1. Install Homebrew (if not already installed)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

#### 2. Install Python and FFmpeg

```bash
brew install python ffmpeg

# Verify installations
python3 --version
ffmpeg -version
```

#### 3. Clone and Install InstaAI Studio

```bash
# Clone repository
git clone https://github.com/yourusername/instaai-studio.git
cd instaai-studio

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Make shell script executable
chmod +x instaai.sh
```

#### 4. Configure

```bash
# Copy environment template
cp .env.example .env

# Edit with your favorite editor
nano .env
# or
code .env
```

### Linux (Ubuntu/Debian)

#### 1. Install Python and FFmpeg

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv ffmpeg git

# Verify installations
python3 --version
ffmpeg -version
```

#### 2. Clone and Install InstaAI Studio

```bash
# Clone repository
git clone https://github.com/yourusername/instaai-studio.git
cd instaai-studio

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Make shell script executable
chmod +x instaai.sh
```

#### 3. Configure

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

## Configuration

### 1. Get Anthropic API Key

1. Visit [console.anthropic.com](https://console.anthropic.com/)
2. Sign up or log in
3. Create a new API key
4. Copy the key (starts with `sk-ant-`)

### 2. Alternative: Get OpenAI API Key

1. Visit [platform.openai.com](https://platform.openai.com/)
2. Sign up or log in
3. Go to API keys section
4. Create a new API key
5. Copy the key (starts with `sk-`)

### 3. Configure .env File

Edit your `.env` file:

```env
# AI Provider (choose one)
ANTHROPIC_API_KEY=sk-ant-your-key-here
# OR
OPENAI_API_KEY=sk-your-key-here

# Instagram Credentials
INSTAGRAM_USERNAME=your_instagram_username
INSTAGRAM_PASSWORD=your_password

# If you have 2FA enabled, you may need an app-specific password
# Generate one from Instagram settings

# Application Settings
DEFAULT_AI_PROVIDER=anthropic  # or openai
LOG_LEVEL=INFO
OUTPUT_DIRECTORY=./output
MAX_VIDEO_DURATION=90

# Scheduling
ENABLE_SCHEDULER=true
```

## Verification

### Test the Installation

```bash
# Activate virtual environment if not already active
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# On Windows:
python src/main.py --version

# On macOS/Linux:
./instaai.sh --version
```

### Run a Test Command

```bash
# Create a simple test
# Make sure you have a test video file

# Windows:
python src/main.py create test_video.mp4 "Make it a reel"

# macOS/Linux:
./instaai.sh create test_video.mp4 "Make it a reel"
```

## Common Issues

### Issue: "Python not found"

**Windows**: Make sure Python is in your PATH. During installation, check "Add Python to PATH"

**macOS/Linux**: Use `python3` instead of `python`

### Issue: "FFmpeg not found"

**Solution**: Ensure FFmpeg is in your PATH

```bash
# Test FFmpeg
ffmpeg -version

# If not found, reinstall and add to PATH
```

### Issue: "No module named 'moviepy'"

**Solution**: Install dependencies
```bash
pip install -r requirements.txt
```

### Issue: "Permission denied" (macOS/Linux)

**Solution**: Make scripts executable
```bash
chmod +x instaai.sh
```

### Issue: "Instagram login failed"

**Solutions**:
1. Verify username/password are correct
2. If you have 2FA, generate an app-specific password
3. Instagram may block automated logins temporarily - wait a few hours
4. Try logging in manually to your account first

## Optional: Install as System Command

### Windows

Add InstaAI Studio to PATH:
1. Right-click "This PC" → Properties → Advanced System Settings
2. Environment Variables → User Variables → Path → Edit
3. Add the full path to `InstaAI-Studio` directory
4. Now you can run `instaai` from anywhere

### macOS/Linux

Create a symbolic link:
```bash
# Make sure the script is executable
chmod +x /path/to/instaai-studio/instaai.sh

# Create symlink
sudo ln -s /path/to/instaai-studio/instaai.sh /usr/local/bin/instaai

# Now you can run from anywhere
instaai --version
```

Or add to your shell profile:
```bash
# Add to ~/.bashrc or ~/.zshrc
echo 'alias instaai="/path/to/instaai-studio/instaai.sh"' >> ~/.bashrc
source ~/.bashrc
```

## Updating

```bash
# Pull latest changes
git pull origin main

# Update dependencies
pip install -r requirements.txt --upgrade
```

## Uninstalling

```bash
# Deactivate virtual environment
deactivate

# Remove directory
cd ..
rm -rf instaai-studio

# Remove symlink (if created)
sudo rm /usr/local/bin/instaai
```

## Next Steps

- Read the [Quick Start Guide](QUICKSTART.md)
- Check out [Examples](examples/example_workflow.py)
- Review the full [README](README.md)

## Getting Help

- Check [Troubleshooting](#common-issues) above
- Review [QUICKSTART.md](QUICKSTART.md)
- Open an issue on GitHub
- Check existing issues for solutions

Happy creating! 🎬
