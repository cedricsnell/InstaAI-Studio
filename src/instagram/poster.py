"""
Instagram posting functionality using instagrapi
Supports Reels, Stories, Carousels, and Feed posts
"""
import logging
from pathlib import Path
from typing import List, Optional, Union, Dict
from datetime import datetime
from instagrapi import Client
from instagrapi.types import Media, Story, StoryMention, StoryLink

logger = logging.getLogger(__name__)


class InstagramPoster:
    """Handle Instagram posting operations"""

    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize Instagram client

        Args:
            username: Instagram username
            password: Instagram password
        """
        self.username = username
        self.password = password
        self.client = None
        self._is_logged_in = False

    def login(self) -> bool:
        """
        Login to Instagram

        Returns:
            True if login successful
        """
        if not self.username or not self.password:
            raise ValueError("Instagram credentials not provided")

        try:
            self.client = Client()
            self.client.login(self.username, self.password)
            self._is_logged_in = True
            logger.info(f"Successfully logged in to Instagram as {self.username}")
            return True
        except Exception as e:
            logger.error(f"Failed to login to Instagram: {e}")
            raise

    def logout(self):
        """Logout from Instagram"""
        if self.client and self._is_logged_in:
            self.client.logout()
            self._is_logged_in = False
            logger.info("Logged out from Instagram")

    def _ensure_logged_in(self):
        """Ensure client is logged in"""
        if not self._is_logged_in:
            self.login()

    def post_reel(
        self,
        video_path: Union[str, Path],
        caption: str = "",
        cover_image_path: Optional[Union[str, Path]] = None,
        share_to_feed: bool = True,
        location: Optional[str] = None,
        hashtags: Optional[List[str]] = None
    ) -> Media:
        """
        Post a video as Instagram Reel

        Args:
            video_path: Path to video file
            caption: Post caption
            cover_image_path: Optional custom cover image
            share_to_feed: Also share to main feed
            location: Location tag
            hashtags: List of hashtags (without #)

        Returns:
            Media object of posted reel
        """
        self._ensure_logged_in()

        try:
            video_path = Path(video_path)
            if not video_path.exists():
                raise FileNotFoundError(f"Video file not found: {video_path}")

            # Add hashtags to caption
            if hashtags:
                caption = self._add_hashtags(caption, hashtags)

            logger.info(f"Posting reel: {video_path.name}")

            # Upload reel
            media = self.client.clip_upload(
                path=str(video_path),
                caption=caption,
                thumbnail=str(cover_image_path) if cover_image_path else None,
                share_to_feed=share_to_feed
            )

            logger.info(f"Reel posted successfully: {media.pk}")
            return media

        except Exception as e:
            logger.error(f"Failed to post reel: {e}")
            raise

    def post_story(
        self,
        media_path: Union[str, Path],
        caption: Optional[str] = None,
        mentions: Optional[List[str]] = None,
        link: Optional[str] = None,
        link_text: Optional[str] = "See more"
    ) -> Story:
        """
        Post to Instagram Story

        Args:
            media_path: Path to image or video
            caption: Story caption/text
            mentions: List of usernames to mention
            link: Swipe-up link (requires business account)
            link_text: Text for the link

        Returns:
            Story object
        """
        self._ensure_logged_in()

        try:
            media_path = Path(media_path)
            if not media_path.exists():
                raise FileNotFoundError(f"Media file not found: {media_path}")

            logger.info(f"Posting story: {media_path.name}")

            # Determine if it's a photo or video
            is_video = media_path.suffix.lower() in ['.mp4', '.mov']

            # Prepare mentions
            story_mentions = []
            if mentions:
                for username in mentions:
                    try:
                        user_id = self.client.user_id_from_username(username)
                        story_mentions.append(
                            StoryMention(user_id=user_id, x=0.5, y=0.5, width=0.5, height=0.1)
                        )
                    except Exception as e:
                        logger.warning(f"Failed to add mention for {username}: {e}")

            # Prepare link
            story_links = []
            if link:
                story_links.append(StoryLink(webUri=link, text=link_text))

            # Upload story
            if is_video:
                story = self.client.video_upload_to_story(
                    path=str(media_path),
                    caption=caption,
                    mentions=story_mentions if story_mentions else None,
                    links=story_links if story_links else None
                )
            else:
                story = self.client.photo_upload_to_story(
                    path=str(media_path),
                    caption=caption,
                    mentions=story_mentions if story_mentions else None,
                    links=story_links if story_links else None
                )

            logger.info(f"Story posted successfully")
            return story

        except Exception as e:
            logger.error(f"Failed to post story: {e}")
            raise

    def post_carousel(
        self,
        media_paths: List[Union[str, Path]],
        caption: str = "",
        location: Optional[str] = None,
        hashtags: Optional[List[str]] = None
    ) -> Media:
        """
        Post a carousel (album) to Instagram

        Args:
            media_paths: List of image/video paths (2-10 items)
            caption: Post caption
            location: Location tag
            hashtags: List of hashtags

        Returns:
            Media object
        """
        self._ensure_logged_in()

        try:
            if len(media_paths) < 2 or len(media_paths) > 10:
                raise ValueError("Carousel must have 2-10 items")

            # Validate all files exist
            paths = [Path(p) for p in media_paths]
            for path in paths:
                if not path.exists():
                    raise FileNotFoundError(f"Media file not found: {path}")

            # Add hashtags
            if hashtags:
                caption = self._add_hashtags(caption, hashtags)

            logger.info(f"Posting carousel with {len(paths)} items")

            # Upload album
            media = self.client.album_upload(
                paths=[str(p) for p in paths],
                caption=caption
            )

            logger.info(f"Carousel posted successfully: {media.pk}")
            return media

        except Exception as e:
            logger.error(f"Failed to post carousel: {e}")
            raise

    def post_photo(
        self,
        image_path: Union[str, Path],
        caption: str = "",
        location: Optional[str] = None,
        hashtags: Optional[List[str]] = None
    ) -> Media:
        """
        Post a single photo to Instagram feed

        Args:
            image_path: Path to image file
            caption: Post caption
            location: Location tag
            hashtags: List of hashtags

        Returns:
            Media object
        """
        self._ensure_logged_in()

        try:
            image_path = Path(image_path)
            if not image_path.exists():
                raise FileNotFoundError(f"Image file not found: {image_path}")

            # Add hashtags
            if hashtags:
                caption = self._add_hashtags(caption, hashtags)

            logger.info(f"Posting photo: {image_path.name}")

            # Upload photo
            media = self.client.photo_upload(
                path=str(image_path),
                caption=caption
            )

            logger.info(f"Photo posted successfully: {media.pk}")
            return media

        except Exception as e:
            logger.error(f"Failed to post photo: {e}")
            raise

    def post_video(
        self,
        video_path: Union[str, Path],
        caption: str = "",
        cover_image_path: Optional[Union[str, Path]] = None,
        location: Optional[str] = None,
        hashtags: Optional[List[str]] = None
    ) -> Media:
        """
        Post a video to Instagram feed

        Args:
            video_path: Path to video file
            caption: Post caption
            cover_image_path: Optional custom thumbnail
            location: Location tag
            hashtags: List of hashtags

        Returns:
            Media object
        """
        self._ensure_logged_in()

        try:
            video_path = Path(video_path)
            if not video_path.exists():
                raise FileNotFoundError(f"Video file not found: {video_path}")

            # Add hashtags
            if hashtags:
                caption = self._add_hashtags(caption, hashtags)

            logger.info(f"Posting video: {video_path.name}")

            # Upload video
            media = self.client.video_upload(
                path=str(video_path),
                caption=caption,
                thumbnail=str(cover_image_path) if cover_image_path else None
            )

            logger.info(f"Video posted successfully: {media.pk}")
            return media

        except Exception as e:
            logger.error(f"Failed to post video: {e}")
            raise

    def _add_hashtags(self, caption: str, hashtags: List[str]) -> str:
        """
        Add hashtags to caption

        Args:
            caption: Original caption
            hashtags: List of hashtags (with or without #)

        Returns:
            Caption with hashtags
        """
        # Ensure hashtags start with #
        formatted_tags = [f"#{tag.lstrip('#')}" for tag in hashtags]

        # Add hashtags to caption
        if caption:
            return f"{caption}\n\n{' '.join(formatted_tags)}"
        else:
            return ' '.join(formatted_tags)

    def get_account_info(self) -> Dict:
        """Get information about the logged-in account"""
        self._ensure_logged_in()

        try:
            user_info = self.client.user_info(self.client.user_id)
            return {
                'username': user_info.username,
                'full_name': user_info.full_name,
                'followers': user_info.follower_count,
                'following': user_info.following_count,
                'posts': user_info.media_count,
                'is_business': user_info.is_business,
                'is_verified': user_info.is_verified
            }
        except Exception as e:
            logger.error(f"Failed to get account info: {e}")
            raise

    def delete_media(self, media_id: str) -> bool:
        """
        Delete a post

        Args:
            media_id: Media ID to delete

        Returns:
            True if successful
        """
        self._ensure_logged_in()

        try:
            self.client.media_delete(media_id)
            logger.info(f"Deleted media: {media_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete media: {e}")
            raise


class InstagramValidator:
    """Validate content before posting"""

    @staticmethod
    def validate_reel(video_path: Path) -> List[str]:
        """
        Validate reel requirements

        Returns:
            List of validation issues (empty if valid)
        """
        issues = []

        if not video_path.exists():
            issues.append(f"Video file not found: {video_path}")
            return issues

        try:
            from moviepy.editor import VideoFileClip

            clip = VideoFileClip(str(video_path))

            # Check duration
            if clip.duration < 3:
                issues.append(f"Reel too short: {clip.duration}s (minimum 3s)")
            elif clip.duration > 90:
                issues.append(f"Reel too long: {clip.duration}s (maximum 90s)")

            # Check resolution
            if clip.size[1] < 1920 or clip.size[0] < 1080:
                issues.append(f"Resolution too low: {clip.size[0]}x{clip.size[1]} (recommended 1080x1920)")

            # Check aspect ratio
            aspect_ratio = clip.size[0] / clip.size[1]
            if not (0.5 <= aspect_ratio <= 0.6):  # 9:16 is ~0.5625
                issues.append(f"Non-optimal aspect ratio: {aspect_ratio:.2f} (recommended 9:16)")

            clip.close()

        except Exception as e:
            issues.append(f"Failed to validate video: {e}")

        return issues

    @staticmethod
    def validate_story(media_path: Path) -> List[str]:
        """Validate story requirements"""
        issues = []

        if not media_path.exists():
            issues.append(f"Media file not found: {media_path}")
            return issues

        # Similar validation as reels
        # Stories have 15s duration for videos

        return issues

    @staticmethod
    def validate_caption(caption: str) -> List[str]:
        """Validate caption"""
        issues = []

        if len(caption) > 2200:
            issues.append(f"Caption too long: {len(caption)} characters (maximum 2200)")

        # Check hashtag count
        hashtag_count = caption.count('#')
        if hashtag_count > 30:
            issues.append(f"Too many hashtags: {hashtag_count} (maximum 30)")

        return issues
