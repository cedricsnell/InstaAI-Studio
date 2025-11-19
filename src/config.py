"""
Configuration management for InstaAI Studio
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional

# Load environment variables
load_dotenv()

class Config:
    """Application configuration"""

    # Project paths
    BASE_DIR = Path(__file__).parent.parent
    OUTPUT_DIR = Path(os.getenv('OUTPUT_DIRECTORY', BASE_DIR / 'output'))
    TEMP_DIR = Path(os.getenv('TEMP_DIRECTORY', BASE_DIR / 'temp'))
    ASSETS_DIR = BASE_DIR / 'assets'
    MUSIC_DIR = ASSETS_DIR / 'music'
    FONTS_DIR = ASSETS_DIR / 'fonts'

    # API Keys
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    DEFAULT_AI_PROVIDER = os.getenv('DEFAULT_AI_PROVIDER', 'anthropic')

    # Instagram Credentials
    INSTAGRAM_USERNAME = os.getenv('INSTAGRAM_USERNAME')
    INSTAGRAM_PASSWORD = os.getenv('INSTAGRAM_PASSWORD')
    INSTAGRAM_ACCESS_TOKEN = os.getenv('INSTAGRAM_ACCESS_TOKEN')
    INSTAGRAM_BUSINESS_ACCOUNT_ID = os.getenv('INSTAGRAM_BUSINESS_ACCOUNT_ID')

    # Application Settings
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

    # Video Settings
    DEFAULT_VIDEO_CODEC = os.getenv('DEFAULT_VIDEO_CODEC', 'libx264')
    DEFAULT_AUDIO_CODEC = os.getenv('DEFAULT_AUDIO_CODEC', 'aac')
    DEFAULT_VIDEO_QUALITY = os.getenv('DEFAULT_VIDEO_QUALITY', 'high')
    MAX_VIDEO_DURATION = int(os.getenv('MAX_VIDEO_DURATION', '90'))

    # Scheduling
    ENABLE_SCHEDULER = os.getenv('ENABLE_SCHEDULER', 'true').lower() == 'true'
    SCHEDULER_DB_PATH = os.getenv('SCHEDULER_DB_PATH', str(BASE_DIR / 'data' / 'scheduler.db'))

    # Instagram Content Specs
    INSTAGRAM_SPECS = {
        'reel': {
            'aspect_ratio': (9, 16),
            'min_duration': 3,
            'max_duration': 90,
            'resolution': (1080, 1920),
            'formats': ['.mp4', '.mov']
        },
        'story': {
            'aspect_ratio': (9, 16),
            'duration': 15,
            'resolution': (1080, 1920),
            'formats': ['.mp4', '.mov', '.jpg', '.png']
        },
        'carousel': {
            'aspect_ratio': (1, 1),
            'min_items': 2,
            'max_items': 10,
            'resolution': (1080, 1080),
            'formats': ['.jpg', '.png', '.mp4']
        },
        'feed': {
            'aspect_ratio': (1, 1),
            'resolution': (1080, 1080),
            'formats': ['.jpg', '.png', '.mp4']
        }
    }

    @classmethod
    def ensure_directories(cls):
        """Create necessary directories if they don't exist"""
        for directory in [cls.OUTPUT_DIR, cls.TEMP_DIR, cls.MUSIC_DIR, cls.FONTS_DIR]:
            directory.mkdir(parents=True, exist_ok=True)

        # Create data directory for scheduler
        Path(cls.SCHEDULER_DB_PATH).parent.mkdir(parents=True, exist_ok=True)

    @classmethod
    def validate(cls) -> list[str]:
        """Validate configuration and return list of warnings"""
        warnings = []

        if not cls.ANTHROPIC_API_KEY and not cls.OPENAI_API_KEY:
            warnings.append("No AI API key configured. Natural language processing will be limited.")

        if not cls.INSTAGRAM_USERNAME or not cls.INSTAGRAM_PASSWORD:
            warnings.append("Instagram credentials not configured. Posting features will be disabled.")

        return warnings


# Initialize directories on import
Config.ensure_directories()
