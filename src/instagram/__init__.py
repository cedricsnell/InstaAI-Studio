"""
Instagram integration module for InstaAI Studio
Uses the official Meta Graph API via OAuth tokens.
"""
from .graph_api import get_instagram_api, InstagramGraphAPI

__all__ = ['get_instagram_api', 'InstagramGraphAPI']
