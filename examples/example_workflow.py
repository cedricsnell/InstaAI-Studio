"""
Example workflow: Complete Instagram content creation pipeline
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from main import InstaAIStudio
from datetime import datetime, timedelta


def example_1_simple_reel():
    """Example 1: Create a simple reel with basic edits"""
    print("\n=== Example 1: Simple Reel Creation ===\n")

    app = InstaAIStudio()

    # Create a reel from a video
    output = app.create_content(
        input_files=[Path('raw_video.mp4')],
        commands=[
            "Make it a vertical reel",
            "Trim to 30 seconds",
            "Add text 'Check this out!' at the center"
        ],
        output_path=Path('output/simple_reel.mp4'),
        content_type='reel'
    )

    print(f"✓ Created reel: {output}")


def example_2_advanced_editing():
    """Example 2: Advanced editing with multiple effects"""
    print("\n=== Example 2: Advanced Reel with Jump Cuts & Music ===\n")

    app = InstaAIStudio()

    output = app.create_content(
        input_files=[Path('raw_video.mp4')],
        commands=[
            "Create a reel format video",
            "Add jump cuts to remove pauses",
            "Speed up by 1.3x for dynamic pacing",
            "Add upbeat background music at 50% volume with fade in and fade out",
            "Add text 'New Product Launch 🚀' at the top for first 3 seconds",
            "Add CTA 'Link in bio for details' at the bottom starting at 25 seconds"
        ],
        output_path=Path('output/product_launch_reel.mp4'),
        content_type='reel'
    )

    print(f"✓ Created advanced reel: {output}")

    # Post with scheduling
    scheduled_time = datetime.now() + timedelta(hours=2)
    app.post_content(
        media_path=output,
        post_type='reel',
        caption="🚀 Big announcement! Our newest product is here. Link in bio for early access!",
        hashtags=['newproduct', 'launch', 'innovation', 'tech'],
        scheduled_time=scheduled_time
    )

    print(f"✓ Scheduled post for {scheduled_time}")


def example_3_batch_processing():
    """Example 3: Batch process multiple videos"""
    print("\n=== Example 3: Batch Processing ===\n")

    app = InstaAIStudio()

    # List of videos to process
    raw_videos = [
        'raw_video_1.mp4',
        'raw_video_2.mp4',
        'raw_video_3.mp4'
    ]

    editing_commands = [
        "Make it a reel",
        "Add jump cuts to remove pauses",
        "Add upbeat music at 40% volume",
        "Speed up by 1.2x"
    ]

    processed_videos = []

    for i, video in enumerate(raw_videos, 1):
        if not Path(video).exists():
            print(f"⚠ Skipping {video} (not found)")
            continue

        print(f"\nProcessing video {i}/{len(raw_videos)}: {video}")

        output = app.create_content(
            input_files=[Path(video)],
            commands=editing_commands,
            output_path=Path(f'output/reel_{i}.mp4'),
            content_type='reel'
        )

        processed_videos.append(output)
        print(f"✓ Processed: {output}")

    print(f"\n✓ Batch processing complete! Processed {len(processed_videos)} videos")


def example_4_story_series():
    """Example 4: Create a story series"""
    print("\n=== Example 4: Story Series ===\n")

    app = InstaAIStudio()

    story_segments = [
        {
            'video': 'tutorial_part1.mp4',
            'text': 'Tutorial Part 1: Setup',
            'duration': 15
        },
        {
            'video': 'tutorial_part2.mp4',
            'text': 'Tutorial Part 2: Configuration',
            'duration': 15
        },
        {
            'video': 'tutorial_part3.mp4',
            'text': 'Tutorial Part 3: Launch!',
            'duration': 15
        }
    ]

    for i, segment in enumerate(story_segments, 1):
        if not Path(segment['video']).exists():
            print(f"⚠ Skipping {segment['video']} (not found)")
            continue

        print(f"\nCreating story {i}/{len(story_segments)}")

        output = app.create_content(
            input_files=[Path(segment['video'])],
            commands=[
                "Make it a story format",
                f"Trim to {segment['duration']} seconds",
                f"Add text '{segment['text']}' at the top",
                "Speed up by 1.5x"
            ],
            output_path=Path(f'output/story_{i}.mp4'),
            content_type='story'
        )

        print(f"✓ Created story: {output}")

        # Post stories in sequence (5 seconds apart)
        post_time = datetime.now() + timedelta(seconds=i * 5)
        app.post_content(
            media_path=output,
            post_type='story',
            scheduled_time=post_time
        )

        print(f"✓ Scheduled story {i} for {post_time}")


def example_5_carousel_from_video():
    """Example 5: Create carousel from video frames"""
    print("\n=== Example 5: Carousel from Video ===\n")

    app = InstaAIStudio()

    # Create multiple clips from one video
    video_path = Path('long_video.mp4')

    if not video_path.exists():
        print(f"⚠ Video not found: {video_path}")
        return

    # Split into 3 segments
    segments = [
        (0, 10),    # First 10 seconds
        (10, 20),   # Next 10 seconds
        (20, 30)    # Last 10 seconds
    ]

    carousel_items = []

    for i, (start, end) in enumerate(segments, 1):
        output = app.create_content(
            input_files=[video_path],
            commands=[
                f"Trim from {start} to {end} seconds",
                "Resize for carousel (square format)",
                f"Add text 'Part {i} of 3' at the top"
            ],
            output_path=Path(f'output/carousel_item_{i}.mp4'),
            content_type='carousel'
        )

        carousel_items.append(output)
        print(f"✓ Created carousel item {i}: {output}")

    # Post as carousel
    app.post_content(
        media_path=carousel_items[0],  # Primary media
        post_type='carousel',
        caption="Swipe to see the full tutorial! 👉",
        hashtags=['tutorial', 'howto', 'learn']
    )

    print(f"\n✓ Posted carousel with {len(carousel_items)} items")


def example_6_scheduled_content_calendar():
    """Example 6: Schedule a week's worth of content"""
    print("\n=== Example 6: Content Calendar ===\n")

    app = InstaAIStudio()

    # Define content schedule
    content_calendar = [
        {
            'day': 'Monday',
            'time': '9:00',
            'video': 'monday_motivation.mp4',
            'caption': 'Start your week strong! 💪',
            'hashtags': ['mondaymotivation', 'motivation', 'success']
        },
        {
            'day': 'Wednesday',
            'time': '12:00',
            'video': 'midweek_tips.mp4',
            'caption': 'Midweek tips for productivity 🚀',
            'hashtags': ['productivity', 'tips', 'business']
        },
        {
            'day': 'Friday',
            'time': '17:00',
            'video': 'weekend_preview.mp4',
            'caption': 'Weekend vibes incoming! 🎉',
            'hashtags': ['friday', 'weekend', 'celebrate']
        }
    ]

    from datetime import datetime
    from dateutil import parser

    for item in content_calendar:
        video_path = Path(item['video'])

        if not video_path.exists():
            print(f"⚠ Skipping {item['day']}: video not found")
            continue

        # Create the content
        output = app.create_content(
            input_files=[video_path],
            commands=[
                "Make it a reel",
                "Add jump cuts",
                "Add upbeat music at 50% volume"
            ],
            output_path=Path(f"output/{item['day'].lower()}_reel.mp4"),
            content_type='reel'
        )

        # Schedule for specific day and time
        # Calculate next occurrence of the day
        schedule_time = parser.parse(f"next {item['day']} at {item['time']}")

        app.post_content(
            media_path=output,
            post_type='reel',
            caption=item['caption'],
            hashtags=item['hashtags'],
            scheduled_time=schedule_time
        )

        print(f"✓ Scheduled {item['day']} reel for {schedule_time}")

    print("\n✓ Content calendar set up successfully!")


if __name__ == '__main__':
    print("InstaAI Studio - Example Workflows")
    print("=" * 50)

    # Run examples
    # Uncomment the examples you want to run

    # example_1_simple_reel()
    # example_2_advanced_editing()
    # example_3_batch_processing()
    # example_4_story_series()
    # example_5_carousel_from_video()
    # example_6_scheduled_content_calendar()

    print("\n" + "=" * 50)
    print("Examples completed!")
    print("\nNote: Make sure you have:")
    print("  1. Set up your .env file with API keys")
    print("  2. Placed sample videos in the appropriate locations")
    print("  3. Installed all dependencies (pip install -r requirements.txt)")
