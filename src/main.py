"""
InstaAI Studio - Main CLI Application
Natural language Instagram content creation and automation
"""
import sys
import logging
from pathlib import Path
from typing import Optional, List
import click
from colorama import init, Fore, Style
from config import Config
from video_processor import VideoEditor
from nl_parser import NaturalLanguageParser, CommandExecutor
from instagram import InstagramPoster, InstagramValidator
from scheduler import PostScheduler, SchedulerHelper
from datetime import datetime

# Initialize colorama for colored terminal output
init(autoreset=True)

# Setup logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class InstaAIStudio:
    """Main application class"""

    def __init__(self):
        self.config = Config
        self.video_editor = VideoEditor(Config.OUTPUT_DIR)
        self.nl_parser = None
        self.instagram_poster = None
        self.scheduler = None
        self.executor = None

        # Initialize AI parser if API key is available
        if Config.ANTHROPIC_API_KEY:
            self.nl_parser = NaturalLanguageParser(
                provider='anthropic',
                api_key=Config.ANTHROPIC_API_KEY
            )
            self.executor = CommandExecutor(self.video_editor)
        elif Config.OPENAI_API_KEY:
            self.nl_parser = NaturalLanguageParser(
                provider='openai',
                api_key=Config.OPENAI_API_KEY
            )
            self.executor = CommandExecutor(self.video_editor)

        # Initialize Instagram poster if credentials available
        if Config.INSTAGRAM_USERNAME and Config.INSTAGRAM_PASSWORD:
            self.instagram_poster = InstagramPoster(
                username=Config.INSTAGRAM_USERNAME,
                password=Config.INSTAGRAM_PASSWORD
            )

        # Initialize scheduler
        if Config.ENABLE_SCHEDULER and self.instagram_poster:
            self.scheduler = PostScheduler(
                db_path=Config.SCHEDULER_DB_PATH,
                instagram_poster=self.instagram_poster
            )

    def create_content(
        self,
        input_files: List[Path],
        commands: List[str],
        output_path: Path,
        content_type: str = 'reel'
    ) -> Path:
        """
        Create Instagram content from natural language commands

        Args:
            input_files: List of input video/image files
            commands: List of natural language editing commands
            output_path: Output file path
            content_type: Type of content (reel, story, carousel, feed)

        Returns:
            Path to created content
        """
        if not self.nl_parser:
            raise ValueError("AI parser not initialized. Please set API key in .env")

        try:
            # Load first input file
            if input_files[0].suffix.lower() in ['.jpg', '.jpeg', '.png']:
                clip = self.video_editor.load_image(input_files[0])
            else:
                clip = self.video_editor.load_video(input_files[0])

            # Prepare context
            context = {
                'video_duration': clip.duration if hasattr(clip, 'duration') else 5.0,
                'video_resolution': (clip.w, clip.h),
                'content_type': content_type,
                'available_music': [f.name for f in Config.MUSIC_DIR.glob('*') if f.is_file()],
                'music_dir': Config.MUSIC_DIR
            }

            # Parse and execute commands
            for command in commands:
                print(f"{Fore.CYAN}Processing: {command}{Style.RESET_ALL}")

                # Parse command
                parsed = self.nl_parser.parse_command(command, context)

                # Execute operations
                clip = self.executor.execute_operations(
                    operations=parsed['operations'],
                    input_clip=clip,
                    context=context
                )

            # Ensure correct format for Instagram
            if content_type in ['reel', 'story', 'carousel', 'feed']:
                clip = self.video_editor.resize_for_instagram(clip, content_type)

            # Export
            output_path = self.video_editor.export_video(clip, output_path)

            print(f"{Fore.GREEN}✓ Content created: {output_path}{Style.RESET_ALL}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to create content: {e}")
            raise

    def post_content(
        self,
        media_path: Path,
        post_type: str,
        caption: str = "",
        hashtags: Optional[List[str]] = None,
        scheduled_time: Optional[datetime] = None
    ):
        """
        Post content to Instagram

        Args:
            media_path: Path to media file
            post_type: Type of post (reel, story, photo, video, carousel)
            caption: Post caption
            hashtags: List of hashtags
            scheduled_time: Optional scheduled time (None = post now)
        """
        if not self.instagram_poster:
            raise ValueError("Instagram credentials not configured")

        try:
            # Validate content
            if post_type == 'reel':
                issues = InstagramValidator.validate_reel(media_path)
                if issues:
                    print(f"{Fore.YELLOW}Validation warnings:")
                    for issue in issues:
                        print(f"  - {issue}")
                    print(Style.RESET_ALL)

            # Validate caption
            if caption:
                issues = InstagramValidator.validate_caption(caption)
                if issues:
                    print(f"{Fore.YELLOW}Caption warnings:")
                    for issue in issues:
                        print(f"  - {issue}")
                    print(Style.RESET_ALL)

            # Post now or schedule
            if scheduled_time:
                if not self.scheduler:
                    raise ValueError("Scheduler not enabled")

                if post_type == 'reel':
                    job_id = self.scheduler.schedule_reel(
                        video_path=media_path,
                        scheduled_time=scheduled_time,
                        caption=caption,
                        hashtags=hashtags
                    )
                    print(f"{Fore.GREEN}✓ Reel scheduled for {scheduled_time} (Job ID: {job_id}){Style.RESET_ALL}")
                elif post_type == 'story':
                    job_id = self.scheduler.schedule_story(
                        media_path=media_path,
                        scheduled_time=scheduled_time,
                        caption=caption
                    )
                    print(f"{Fore.GREEN}✓ Story scheduled for {scheduled_time} (Job ID: {job_id}){Style.RESET_ALL}")
            else:
                # Post immediately
                if post_type == 'reel':
                    media = self.instagram_poster.post_reel(
                        video_path=media_path,
                        caption=caption,
                        hashtags=hashtags
                    )
                    print(f"{Fore.GREEN}✓ Reel posted successfully!{Style.RESET_ALL}")
                elif post_type == 'story':
                    story = self.instagram_poster.post_story(
                        media_path=media_path,
                        caption=caption
                    )
                    print(f"{Fore.GREEN}✓ Story posted successfully!{Style.RESET_ALL}")
                elif post_type == 'photo':
                    media = self.instagram_poster.post_photo(
                        image_path=media_path,
                        caption=caption,
                        hashtags=hashtags
                    )
                    print(f"{Fore.GREEN}✓ Photo posted successfully!{Style.RESET_ALL}")
                elif post_type == 'video':
                    media = self.instagram_poster.post_video(
                        video_path=media_path,
                        caption=caption,
                        hashtags=hashtags
                    )
                    print(f"{Fore.GREEN}✓ Video posted successfully!{Style.RESET_ALL}")

        except Exception as e:
            logger.error(f"Failed to post content: {e}")
            raise


# CLI Commands using Click
@click.group()
@click.version_option(version='1.0.0')
def cli():
    """
    InstaAI Studio - Create Instagram content with natural language!

    Examples:
        instaai create video.mp4 "Make it a reel, add jump cuts, and add text 'Check this out!'"
        instaai post output.mp4 --type reel --caption "My awesome reel!"
        instaai schedule output.mp4 --type reel --time "tomorrow at 9am"
    """
    # Check configuration
    warnings = Config.validate()
    if warnings:
        for warning in warnings:
            click.echo(f"{Fore.YELLOW}Warning: {warning}{Style.RESET_ALL}")


@cli.command()
@click.argument('input_files', nargs=-1, type=click.Path(exists=True))
@click.argument('commands', nargs=-1)
@click.option('--output', '-o', type=click.Path(), help='Output file path')
@click.option('--type', '-t', default='reel', type=click.Choice(['reel', 'story', 'carousel', 'feed']))
def create(input_files, commands, output, type):
    """
    Create Instagram content with natural language commands

    Example:
        instaai create video.mp4 "Add jump cuts to remove pauses" "Add upbeat music" "Add text 'Check this out!' at the start"
    """
    if not input_files:
        click.echo(f"{Fore.RED}Error: No input files specified{Style.RESET_ALL}")
        return

    if not commands:
        click.echo(f"{Fore.RED}Error: No commands specified{Style.RESET_ALL}")
        return

    # Convert to paths
    input_paths = [Path(f) for f in input_files]

    # Generate output path if not specified
    if not output:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output = Config.OUTPUT_DIR / f"{type}_{timestamp}.mp4"
    else:
        output = Path(output)

    try:
        app = InstaAIStudio()
        output_path = app.create_content(
            input_files=input_paths,
            commands=list(commands),
            output_path=output,
            content_type=type
        )
        click.echo(f"\n{Fore.GREEN}✓ Content created successfully!{Style.RESET_ALL}")
        click.echo(f"Output: {output_path}")

    except Exception as e:
        click.echo(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
        sys.exit(1)


@cli.command()
@click.argument('media_path', type=click.Path(exists=True))
@click.option('--type', '-t', required=True, type=click.Choice(['reel', 'story', 'photo', 'video']))
@click.option('--caption', '-c', default='', help='Post caption')
@click.option('--hashtags', '-h', multiple=True, help='Hashtags (can specify multiple)')
def post(media_path, type, caption, hashtags):
    """
    Post content to Instagram immediately

    Example:
        instaai post video.mp4 --type reel --caption "My reel!" --hashtags viral --hashtags reels
    """
    try:
        app = InstaAIStudio()
        app.post_content(
            media_path=Path(media_path),
            post_type=type,
            caption=caption,
            hashtags=list(hashtags) if hashtags else None
        )

    except Exception as e:
        click.echo(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
        sys.exit(1)


@cli.command()
@click.argument('media_path', type=click.Path(exists=True))
@click.option('--type', '-t', required=True, type=click.Choice(['reel', 'story']))
@click.option('--time', required=True, help='Scheduled time (e.g., "tomorrow at 9am", "2024-01-15 14:30")')
@click.option('--caption', '-c', default='', help='Post caption')
@click.option('--hashtags', '-h', multiple=True, help='Hashtags')
def schedule(media_path, type, time, caption, hashtags):
    """
    Schedule content to be posted later

    Example:
        instaai schedule video.mp4 --type reel --time "tomorrow at 9am" --caption "Good morning!"
    """
    try:
        # Parse time
        scheduled_time = SchedulerHelper.parse_natural_time(time)

        app = InstaAIStudio()
        app.post_content(
            media_path=Path(media_path),
            post_type=type,
            caption=caption,
            hashtags=list(hashtags) if hashtags else None,
            scheduled_time=scheduled_time
        )

    except Exception as e:
        click.echo(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
        sys.exit(1)


@cli.command()
@click.option('--status', type=click.Choice(['scheduled', 'posted', 'failed', 'cancelled']))
def list_scheduled(status):
    """List scheduled posts"""
    try:
        app = InstaAIStudio()
        if not app.scheduler:
            click.echo(f"{Fore.RED}Error: Scheduler not enabled{Style.RESET_ALL}")
            return

        posts = app.scheduler.get_scheduled_posts(status)

        if not posts:
            click.echo("No scheduled posts found.")
            return

        click.echo(f"\n{Fore.CYAN}Scheduled Posts:{Style.RESET_ALL}\n")
        for post in posts:
            click.echo(f"Job ID: {post['job_id']}")
            click.echo(f"  Type: {post['post_type']}")
            click.echo(f"  Scheduled: {post['scheduled_time']}")
            click.echo(f"  Status: {post['status']}")
            click.echo(f"  Media: {post['media_path']}")
            click.echo()

    except Exception as e:
        click.echo(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
        sys.exit(1)


@cli.command()
@click.argument('job_id')
def cancel(job_id):
    """Cancel a scheduled post"""
    try:
        app = InstaAIStudio()
        if not app.scheduler:
            click.echo(f"{Fore.RED}Error: Scheduler not enabled{Style.RESET_ALL}")
            return

        success = app.scheduler.cancel_job(job_id)
        if success:
            click.echo(f"{Fore.GREEN}✓ Job cancelled: {job_id}{Style.RESET_ALL}")
        else:
            click.echo(f"{Fore.RED}Failed to cancel job{Style.RESET_ALL}")

    except Exception as e:
        click.echo(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
        sys.exit(1)


@cli.command()
def info():
    """Show account information"""
    try:
        app = InstaAIStudio()
        if not app.instagram_poster:
            click.echo(f"{Fore.RED}Error: Instagram credentials not configured{Style.RESET_ALL}")
            return

        info = app.instagram_poster.get_account_info()

        click.echo(f"\n{Fore.CYAN}Account Information:{Style.RESET_ALL}\n")
        click.echo(f"Username: @{info['username']}")
        click.echo(f"Full Name: {info['full_name']}")
        click.echo(f"Followers: {info['followers']:,}")
        click.echo(f"Following: {info['following']:,}")
        click.echo(f"Posts: {info['posts']:,}")
        click.echo(f"Business Account: {info['is_business']}")
        click.echo(f"Verified: {info['is_verified']}")

    except Exception as e:
        click.echo(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
        sys.exit(1)


if __name__ == '__main__':
    cli()
