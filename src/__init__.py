"""
InstaAI Studio - Instagram Content Creation with Natural Language
Version: 1.0.0
"""

__version__ = '1.0.0'
__author__ = 'InstaAI Team'
__description__ = 'Create Instagram content with natural language commands'

from .config import Config
from .video_processor import VideoEditor
from .nl_parser import NaturalLanguageParser, CommandExecutor
from .instagram import InstagramPoster, InstagramValidator
from .scheduler import PostScheduler, SchedulerHelper

__all__ = [
    'Config',
    'VideoEditor',
    'NaturalLanguageParser',
    'CommandExecutor',
    'InstagramPoster',
    'InstagramValidator',
    'PostScheduler',
    'SchedulerHelper',
]
