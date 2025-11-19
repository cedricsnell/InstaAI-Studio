# Quick Start Guide

Get started with InstaAI Studio in 5 minutes!

## Step 1: Install Dependencies

```bash
# Make sure you have Python 3.8+ installed
python --version

# Install FFmpeg
# Windows (with Chocolatey):
choco install ffmpeg

# macOS:
brew install ffmpeg

# Linux:
sudo apt install ffmpeg

# Install Python packages
pip install -r requirements.txt
```

## Step 2: Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your credentials
```

Add your API keys to `.env`:

```env
# Get your Anthropic API key from: https://console.anthropic.com/
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Instagram credentials
INSTAGRAM_USERNAME=your_instagram_username
INSTAGRAM_PASSWORD=your_password

# Settings
DEFAULT_AI_PROVIDER=anthropic
LOG_LEVEL=INFO
```

## Step 3: Add Sample Content

```bash
# Create a test video directory
mkdir test_videos

# Add a video file to test with
# (copy any .mp4 file into test_videos/)
```

## Step 4: Create Your First Reel

```bash
# Navigate to the src directory
cd src

# Create a simple reel
python main.py create ../test_videos/your_video.mp4 \
  "Make it a vertical reel" \
  "Add text 'My First Reel!' at the center"
```

The output will be saved to `output/reel_TIMESTAMP.mp4`

## Step 5: Try More Advanced Edits

```bash
# Add jump cuts and music
python main.py create ../test_videos/your_video.mp4 \
  "Create a reel" \
  "Add jump cuts to remove pauses" \
  "Add upbeat music at 50% volume" \
  "Add text 'Check this out! 🔥' at the top for 3 seconds"
```

## Step 6: Post to Instagram (Optional)

⚠️ **Warning**: Make sure you're comfortable with the video before posting!

```bash
# Post your reel
python main.py post output/reel_TIMESTAMP.mp4 \
  --type reel \
  --caption "My first AI-created reel!" \
  --hashtags ai --hashtags reel
```

## Step 7: Schedule a Post (Optional)

```bash
# Schedule for later
python main.py schedule output/reel_TIMESTAMP.mp4 \
  --type reel \
  --time "tomorrow at 9am" \
  --caption "Coming soon!"
```

## Common Commands

### Create Content

```bash
# Simple reel
python main.py create video.mp4 "Make it a reel"

# With multiple edits
python main.py create video.mp4 \
  "Trim to 30 seconds" \
  "Add music" \
  "Add text 'Hello!'"

# Custom output
python main.py create video.mp4 \
  "Make it a story" \
  --output my_story.mp4 \
  --type story
```

### Post Content

```bash
# Post reel
python main.py post video.mp4 --type reel --caption "My reel"

# Post story
python main.py post image.jpg --type story

# With hashtags
python main.py post video.mp4 \
  --type reel \
  --caption "Great content" \
  --hashtags viral --hashtags reel
```

### Manage Schedule

```bash
# List scheduled posts
python main.py list-scheduled

# View upcoming posts
python main.py list-scheduled --status scheduled

# Cancel a post
python main.py cancel JOB_ID_HERE
```

### View Account Info

```bash
# See your Instagram account details
python main.py info
```

## Natural Language Examples

The AI understands various ways to express the same command:

### Trimming
- "Keep only the first 30 seconds"
- "Trim to 30 seconds"
- "Cut it down to 30 seconds"

### Jump Cuts
- "Add jump cuts"
- "Remove pauses"
- "Cut out the silent parts"

### Text Overlays
- "Add text 'Hello' at the center"
- "Put 'Hello' in the middle"
- "Add 'Hello' text overlay centered"

### Music
- "Add background music"
- "Add music at 50% volume"
- "Add upbeat.mp3 as background music with fade"

### Speed
- "Speed up by 2x"
- "Make it twice as fast"
- "Double the speed"

### Format
- "Make it vertical for reels"
- "Convert to reel format"
- "Resize for Instagram reel"

## Troubleshooting

### Issue: "FFmpeg not found"
**Solution**: Make sure FFmpeg is installed and in your PATH
```bash
ffmpeg -version  # Should show version info
```

### Issue: "API key not configured"
**Solution**: Check your `.env` file has the correct API key
```env
ANTHROPIC_API_KEY=sk-ant-xxxxx  # Make sure this is set
```

### Issue: "Instagram login failed"
**Solution**:
- Check username/password are correct
- If you have 2FA, you may need an app-specific password
- Instagram may temporarily block automated logins - wait a few hours

### Issue: "Video processing is slow"
**Solution**:
- Reduce video resolution before processing
- Use shorter videos for testing
- Close other applications

### Issue: "Module not found"
**Solution**: Make sure all dependencies are installed
```bash
pip install -r requirements.txt
```

## Next Steps

1. **Add Music**: Place `.mp3` files in `assets/music/` to use them in edits
2. **Batch Processing**: See `examples/example_workflow.py` for batch processing examples
3. **Scheduling**: Set up recurring posts for automated content
4. **Custom Workflows**: Create Python scripts using the InstaAI API

## Getting Help

- Check the full [README.md](README.md) for detailed documentation
- See [examples/example_workflow.py](examples/example_workflow.py) for code examples
- Create an issue on GitHub if you encounter problems

## Tips for Best Results

1. **Start Simple**: Begin with basic commands and add complexity
2. **High Quality Input**: Use good quality source videos (1080p+)
3. **Test First**: Always preview content before posting
4. **Optimal Timing**: Schedule posts for peak engagement times
5. **Hashtag Strategy**: Use 10-15 relevant hashtags per post

Happy creating! 🎬✨
