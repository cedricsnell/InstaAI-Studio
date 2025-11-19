# InstaAI Studio 🎬

Create stunning Instagram Reels, Stories, and Carousels using **natural language commands**! No complex video editing software needed - just describe what you want, and InstaAI Studio does the rest.

## 🌐 Two Ways to Use

### 1. **Web Interface** (Recommended for Teams)
- Modern, Instagram-inspired UI
- Access from any browser
- Multi-user support
- Drag & drop file uploads
- **Deploy to cloud for team access!**

[👉 Web UI Guide](WEB_UI.md) | [☁️ Deployment Guide](DEPLOYMENT.md)

### 2. **Command Line Interface** (For Developers)
- Powerful CLI tool
- Perfect for automation
- Scriptable workflows
- Local processing

## ✨ Features

- **🗣️ Natural Language Editing**: Edit videos by simply describing what you want
  - "Add jump cuts to remove pauses"
  - "Make it a vertical reel with upbeat music"
  - "Add a 'Link in bio' CTA at the end"

- **🎬 Professional Video Editing**:
  - Jump cuts and auto-detection of scene changes
  - Text overlays and CTAs
  - Background music with fade in/out
  - Speed effects (slow-mo, time-lapse)
  - Automatic Instagram formatting (Reels, Stories, Carousels)

- **📱 Instagram Integration**:
  - Direct posting to Instagram
  - Support for Reels, Stories, Carousels, Photos, and Videos
  - Automatic validation of Instagram requirements

- **⏰ Scheduling**:
  - Schedule posts for optimal engagement times
  - Recurring posts with cron expressions
  - Track scheduled, posted, and failed posts

- **🤖 AI-Powered**:
  - Uses Claude 3.5 Sonnet or GPT-4 for natural language understanding
  - Smart parameter inference (e.g., "at the end" → calculates exact timestamp)

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- FFmpeg installed on your system
- Instagram account
- Anthropic API key (Claude) or OpenAI API key

### Installation

1. **Clone the repository**:
```bash
git clone https://github.com/yourusername/instaai-studio.git
cd instaai-studio
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

Or install as a package:
```bash
pip install -e .
```

3. **Install FFmpeg**:

**Windows**:
```bash
# Using Chocolatey
choco install ffmpeg

# Or download from https://ffmpeg.org/download.html
```

**macOS**:
```bash
brew install ffmpeg
```

**Linux**:
```bash
sudo apt install ffmpeg
```

4. **Configure environment**:
```bash
# Copy example env file
cp .env.example .env

# Edit .env and add your credentials
```

**.env file**:
```env
# API Keys (choose one)
ANTHROPIC_API_KEY=sk-ant-xxxxx
OPENAI_API_KEY=sk-xxxxx

# Instagram Credentials
INSTAGRAM_USERNAME=your_username
INSTAGRAM_PASSWORD=your_password

# Settings
DEFAULT_AI_PROVIDER=anthropic
LOG_LEVEL=INFO
```

## 📖 Usage

### Web Interface (Quick Start)

```bash
# Start the web server
# Windows:
start-web.bat

# Mac/Linux:
chmod +x start-web.sh
./start-web.sh
```

Then open: **http://localhost:8000**

**Default login:** admin / admin123

**Features:**
- 📤 Drag & drop video/image uploads
- ✍️ Natural language command input
- 🎬 One-click content creation
- 📅 Schedule Instagram posts
- 📁 File management
- 👥 Multi-user support

[Full Web UI Documentation →](WEB_UI.md)

### Command Line Interface

#### Create Content with Natural Language

```bash
# Basic reel creation
instaai create video.mp4 "Make it a reel with jump cuts"

# Multiple editing commands
instaai create video.mp4 \
  "Remove pauses with jump cuts" \
  "Add upbeat background music at 60% volume" \
  "Add text 'New Product Launch!' at the beginning" \
  "Add CTA 'Link in bio' at the end"

# Create from multiple files
instaai create clip1.mp4 clip2.mp4 clip3.mp4 \
  "Combine these into one reel" \
  "Add crossfade transitions" \
  "Speed up by 1.5x"

# Specify output path and type
instaai create video.mp4 \
  "Make it a story with music" \
  --output my_story.mp4 \
  --type story
```

#### Post to Instagram

```bash
# Post immediately
instaai post my_reel.mp4 \
  --type reel \
  --caption "Check out my new reel! 🔥" \
  --hashtags viral --hashtags reels --hashtags trending

# Post a story
instaai post my_story.mp4 \
  --type story \
  --caption "Story time!"

# Post a carousel
instaai post image1.jpg image2.jpg image3.jpg \
  --type carousel \
  --caption "Swipe to see more!"
```

#### Schedule Posts

```bash
# Schedule for specific time
instaai schedule my_reel.mp4 \
  --type reel \
  --time "tomorrow at 9am" \
  --caption "Good morning! ☀️"

# Schedule with date-time
instaai schedule my_reel.mp4 \
  --type reel \
  --time "2024-01-15 14:30" \
  --caption "Launching now!"

# List scheduled posts
instaai list-scheduled

# Cancel a scheduled post
instaai cancel job_id_here
```

#### View Account Info

```bash
instaai info
```

### Python API

You can also use InstaAI Studio programmatically:

```python
from pathlib import Path
from src.main import InstaAIStudio
from datetime import datetime, timedelta

# Initialize
app = InstaAIStudio()

# Create content
output = app.create_content(
    input_files=[Path('video.mp4')],
    commands=[
        "Create a reel",
        "Add jump cuts to remove pauses",
        "Add text 'Check this out!' at the start",
        "Add upbeat music with fade in"
    ],
    output_path=Path('output/my_reel.mp4'),
    content_type='reel'
)

# Post immediately
app.post_content(
    media_path=output,
    post_type='reel',
    caption="My awesome reel!",
    hashtags=['viral', 'reels', 'trending']
)

# Or schedule for later
scheduled_time = datetime.now() + timedelta(hours=2)
app.post_content(
    media_path=output,
    post_type='reel',
    caption="Coming soon!",
    scheduled_time=scheduled_time
)
```

## 🎨 Natural Language Commands

### Video Editing Operations

**Trimming**:
- "Keep only the first 30 seconds"
- "Trim from 10 seconds to 45 seconds"

**Jump Cuts**:
- "Add jump cuts to remove pauses"
- "Remove silent parts"
- "Create jump cuts every 5 seconds"

**Text Overlays**:
- "Add text 'Hello World' at the center"
- "Add text 'Subscribe!' at the bottom for 5 seconds"
- "Add CTA 'Link in bio' at the end"

**Music & Audio**:
- "Add upbeat background music"
- "Add music at 50% volume with fade in and fade out"
- "Add upbeat.mp3 as background music"

**Speed Effects**:
- "Speed up by 2x"
- "Slow down to half speed"
- "Make it 1.5x faster"

**Format Conversion**:
- "Make it vertical for reels"
- "Resize for Instagram story"
- "Convert to square for feed post"

**Combining Operations**:
```bash
instaai create raw_video.mp4 \
  "Trim to 60 seconds" \
  "Add jump cuts to remove pauses" \
  "Resize for Instagram reel" \
  "Add text 'Product Launch 2024' at the top for 3 seconds" \
  "Add energetic music at 40% volume" \
  "Speed up by 1.3x" \
  "Add CTA 'Shop now - link in bio' at the end"
```

## 📁 Project Structure

```
InstaAI-Studio/
├── src/
│   ├── config.py              # Configuration management
│   ├── main.py                # Main CLI application
│   ├── video_processor/       # Video editing engine
│   │   ├── __init__.py
│   │   └── video_editor.py    # Core editing functions
│   ├── nl_parser/             # Natural language processing
│   │   ├── __init__.py
│   │   └── command_parser.py  # AI-powered command parser
│   ├── instagram/             # Instagram integration
│   │   ├── __init__.py
│   │   └── poster.py          # Instagram posting
│   └── scheduler/             # Post scheduling
│       ├── __init__.py
│       └── post_scheduler.py  # Scheduling system
├── assets/
│   ├── music/                 # Background music files
│   └── fonts/                 # Custom fonts
├── examples/                  # Example videos and scripts
├── output/                    # Generated content
├── requirements.txt
├── setup.py
├── .env.example
└── README.md
```

## 🎯 Examples

### Example 1: Product Launch Reel

```bash
instaai create product_demo.mp4 \
  "Create a 30-second reel" \
  "Add jump cuts for dynamic pacing" \
  "Add text 'New Product Alert! 🚀' at the top for the first 3 seconds" \
  "Add upbeat electronic music at 50% volume" \
  "Add CTA 'Shop now - Link in bio' at the end for 3 seconds" \
  --output product_launch.mp4

# Schedule for prime time
instaai schedule product_launch.mp4 \
  --type reel \
  --time "tomorrow at 6pm" \
  --caption "Introducing our latest innovation! 🔥" \
  --hashtags newproduct --hashtags launch2024 --hashtags innovation
```

### Example 2: Tutorial Story Series

```bash
# Create story 1
instaai create tutorial_pt1.mp4 \
  "Make it a 15-second story" \
  "Add text 'Tutorial Part 1' at the top" \
  "Speed up by 1.5x" \
  --type story \
  --output tutorial_story_1.mp4

# Post immediately
instaai post tutorial_story_1.mp4 --type story
```

### Example 3: Behind-the-Scenes Carousel

```bash
# Prepare images
instaai create bts1.jpg "Resize for carousel" --output carousel1.jpg
instaai create bts2.jpg "Resize for carousel" --output carousel2.jpg
instaai create bts3.jpg "Resize for carousel" --output carousel3.jpg

# Post carousel
instaai post carousel1.jpg carousel2.jpg carousel3.jpg \
  --type carousel \
  --caption "Behind the scenes! Swipe to see more 👉" \
  --hashtags bts --hashtags behindthescenes
```

## 🔧 Advanced Features

### Custom Music Library

Add your music files to `assets/music/`:

```bash
# Copy music files
cp my_music.mp3 assets/music/

# Use in commands
instaai create video.mp4 "Add my_music.mp3 as background"
```

### Recurring Posts

```python
from src.scheduler import PostScheduler

scheduler = PostScheduler(db_path='data/scheduler.db', instagram_poster=poster)

# Post every day at 9am
def generate_daily_content():
    # Your logic to generate content
    return Path('daily_content.mp4')

scheduler.schedule_recurring(
    post_type='reel',
    cron_expression='0 9 * * *',  # Daily at 9am
    media_generator=generate_daily_content,
    caption="Daily motivation!",
    hashtags=['motivation', 'daily']
)
```

### Batch Processing

```python
from pathlib import Path
from src.main import InstaAIStudio

app = InstaAIStudio()

videos = Path('raw_videos').glob('*.mp4')

for video in videos:
    output = app.create_content(
        input_files=[video],
        commands=[
            "Make it a reel",
            "Add jump cuts",
            "Add upbeat music"
        ],
        output_path=Path(f'output/{video.stem}_reel.mp4')
    )
    print(f"Processed: {output}")
```

## 🛡️ Best Practices

1. **Video Quality**:
   - Use 1080x1920 (9:16) for Reels/Stories
   - Keep Reels between 15-60 seconds for best engagement
   - Use high-quality source videos

2. **Captions & Hashtags**:
   - Keep captions under 2200 characters
   - Use 10-15 relevant hashtags (max 30)
   - Include CTAs for better engagement

3. **Posting Times**:
   - Use scheduler to post during peak engagement times
   - Typically: 9am, 12pm, 5pm, 8pm in your audience's timezone

4. **Music**:
   - Use royalty-free music to avoid copyright issues
   - Keep music volume at 40-60% so it doesn't overpower speech

## ⚠️ Troubleshooting

### FFmpeg Not Found
```bash
# Make sure FFmpeg is in your PATH
ffmpeg -version

# If not, install it (see Installation section)
```

### Instagram Login Issues
- Use app-specific password if you have 2FA enabled
- Instagram may block automated logins - wait a few hours and try again
- Consider using Instagram Graph API for business accounts

### API Rate Limits
- Claude/GPT API calls are rate-limited
- Cache parsed commands for repeated operations
- Consider using batch processing during off-peak hours

### Memory Issues with Large Videos
- Process videos in segments
- Reduce video quality/resolution before editing
- Close clips explicitly after processing

## 📊 Roadmap

- [ ] Web UI with drag-and-drop interface
- [ ] Support for more AI models (local LLMs)
- [ ] Advanced analytics and insights
- [ ] Template library for common content types
- [ ] Multi-account management
- [ ] Video generation from scripts
- [ ] Auto-captioning and subtitle generation
- [ ] Face detection and auto-centering
- [ ] Green screen effects
- [ ] Trending audio suggestions

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- MoviePy for video editing
- Instagrapi for Instagram API
- Anthropic Claude / OpenAI GPT for natural language processing

## 📞 Support

- GitHub Issues: [Create an issue](https://github.com/yourusername/instaai-studio/issues)
- Documentation: [Full docs](https://github.com/yourusername/instaai-studio/wiki)

---

**Made with ❤️ for content creators**

Happy creating! 🎬✨
