"""
Video Repurposing Engine
Downloads Instagram videos and creates new content by stitching clips
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import httpx
import hashlib
from datetime import datetime
import asyncio
import tempfile
import os

from .video_editor import VideoEditor
from moviepy.editor import VideoFileClip, ImageClip

logger = logging.getLogger(__name__)


class VideoRepurposer:
    """
    Repurpose existing Instagram content into new reels.
    Downloads videos, extracts best clips, stitches them together.
    """

    def __init__(self, workspace_dir: Optional[Path] = None):
        """
        Initialize video repurposer.

        Args:
            workspace_dir: Directory for downloading and processing videos
        """
        if workspace_dir:
            self.workspace = Path(workspace_dir)
        else:
            self.workspace = Path(tempfile.gettempdir()) / "instaai_videos"

        self.workspace.mkdir(parents=True, exist_ok=True)
        self.downloads_dir = self.workspace / "downloads"
        self.downloads_dir.mkdir(exist_ok=True)
        self.outputs_dir = self.workspace / "outputs"
        self.outputs_dir.mkdir(exist_ok=True)

        self.editor = VideoEditor(output_dir=self.outputs_dir)

    async def download_media(
        self, url: str, media_id: str, media_type: str = "video"
    ) -> Optional[Path]:
        """
        Download Instagram media from URL.

        Args:
            url: Media URL
            media_id: Instagram media ID
            media_type: 'video' or 'image'

        Returns:
            Path to downloaded file or None if failed
        """
        try:
            # Create filename from media ID hash
            file_hash = hashlib.md5(media_id.encode()).hexdigest()[:12]
            extension = ".mp4" if media_type == "video" else ".jpg"
            filename = f"{file_hash}{extension}"
            filepath = self.downloads_dir / filename

            # Skip if already downloaded
            if filepath.exists():
                logger.info(f"Media already downloaded: {filename}")
                return filepath

            # Download
            logger.info(f"Downloading media from {url}")
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()

                with open(filepath, "wb") as f:
                    f.write(response.content)

            logger.info(f"Downloaded: {filename} ({len(response.content) / 1024 / 1024:.2f}MB)")
            return filepath

        except Exception as e:
            logger.error(f"Failed to download media {media_id}: {e}")
            return None

    async def download_batch(
        self, posts: List[Dict[str, Any]]
    ) -> List[Tuple[str, Path]]:
        """
        Download multiple media files in batch.

        Args:
            posts: List of post dicts with media_id, media_url, media_type

        Returns:
            List of (media_id, filepath) tuples for successful downloads
        """
        download_tasks = []
        for post in posts:
            media_id = post.get("media_id")
            media_url = post.get("media_url")
            media_type = post.get("media_type", "VIDEO").lower()

            if not media_url or not media_id:
                continue

            # Only download videos and images
            if "video" in media_type.lower():
                download_tasks.append((media_id, self.download_media(media_url, media_id, "video")))
            elif "image" in media_type.lower():
                download_tasks.append((media_id, self.download_media(media_url, media_id, "image")))

        # Execute downloads concurrently
        results = []
        for media_id, task in download_tasks:
            filepath = await task
            if filepath:
                results.append((media_id, filepath))

        logger.info(f"Downloaded {len(results)}/{len(download_tasks)} media files")
        return results

    def extract_best_clips(
        self,
        video_path: Path,
        duration_range: Tuple[float, float] = (3.0, 10.0),
        max_clips: int = 5,
    ) -> List[Tuple[float, float]]:
        """
        Extract the most engaging clips from a video.

        Args:
            video_path: Path to video file
            duration_range: (min, max) duration for clips in seconds
            max_clips: Maximum number of clips to extract

        Returns:
            List of (start, end) time tuples
        """
        try:
            clip = self.editor.load_video(video_path)
            total_duration = clip.duration

            # Auto-detect scene changes
            scenes = self.editor.auto_detect_cuts(clip, threshold=15.0, min_scene_duration=duration_range[0])

            # Filter scenes within duration range
            valid_scenes = []
            for start, end in scenes:
                scene_duration = end - start
                if duration_range[0] <= scene_duration <= duration_range[1]:
                    valid_scenes.append((start, end))

            # If no valid scenes, create clips by splitting video
            if not valid_scenes:
                clip_duration = min(duration_range[1], total_duration / max_clips)
                valid_scenes = []
                for i in range(max_clips):
                    start = i * clip_duration
                    end = min(start + clip_duration, total_duration)
                    if end - start >= duration_range[0]:
                        valid_scenes.append((start, end))

            # Take top N clips
            result = valid_scenes[:max_clips]

            clip.close()
            logger.info(f"Extracted {len(result)} clips from {video_path.name}")
            return result

        except Exception as e:
            logger.error(f"Failed to extract clips from {video_path}: {e}")
            return []

    async def create_reel_from_plan(
        self,
        reel_plan: Dict[str, Any],
        source_posts: List[Dict[str, Any]],
        niche: str = "General",
    ) -> Optional[Path]:
        """
        Create a reel video from an AI-generated plan.

        Args:
            reel_plan: Reel concept from AI (with script, visual_plan, etc.)
            source_posts: Available posts with media_urls
            niche: Content niche for context

        Returns:
            Path to generated reel video
        """
        try:
            title = reel_plan.get("title", "Untitled Reel")
            script = reel_plan.get("script", "")
            visual_plan = reel_plan.get("visual_plan", "")
            duration = reel_plan.get("duration", "30s")
            hook = reel_plan.get("hook", "")

            # Parse target duration
            target_duration = self._parse_duration(duration)

            logger.info(f"Creating reel: {title} (target: {target_duration}s)")

            # Download source videos
            video_posts = [p for p in source_posts if "video" in p.get("media_type", "").lower()][:5]

            if not video_posts:
                logger.warning("No video posts available for repurposing")
                return None

            downloaded = await self.download_batch(video_posts)

            if not downloaded:
                logger.error("Failed to download any source videos")
                return None

            # Extract clips from each video
            all_clips_data = []
            for media_id, filepath in downloaded:
                clips_times = self.extract_best_clips(filepath, duration_range=(3.0, 8.0), max_clips=3)

                for start, end in clips_times:
                    all_clips_data.append({
                        "filepath": filepath,
                        "start": start,
                        "end": end,
                        "duration": end - start
                    })

            if not all_clips_data:
                logger.error("No clips extracted")
                return None

            # Select clips to fit target duration
            selected_clips = self._select_clips_for_duration(all_clips_data, target_duration)

            # Load and process video clips
            video_clips = []
            for clip_data in selected_clips:
                video = self.editor.load_video(clip_data["filepath"])
                trimmed = self.editor.trim_clip(video, clip_data["start"], clip_data["end"])

                # Resize for Instagram Reels (9:16)
                resized = self.editor.resize_for_instagram(trimmed, content_type="reel")

                video_clips.append(resized)

            # Concatenate clips with crossfade transitions
            final_video = self.editor.concatenate_clips(
                video_clips, transition="crossfade", transition_duration=0.3
            )

            # Add hook text overlay at the beginning
            if hook:
                final_video = self.editor.add_text_overlay(
                    final_video,
                    text=hook,
                    position="center",
                    fontsize=60,
                    duration=3.0,
                    start_time=0,
                    stroke_width=3
                )

            # Export
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"reel_{timestamp}.mp4"
            output_path = self.editor.export_video(
                final_video,
                self.outputs_dir / output_filename,
                bitrate="8000k",
                fps=30
            )

            logger.info(f"✅ Reel created: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to create reel: {e}")
            return None

    def _parse_duration(self, duration_str: str) -> float:
        """Parse duration string like '30s', '45s' to float seconds."""
        try:
            if 's' in duration_str.lower():
                return float(duration_str.lower().replace('s', ''))
            return float(duration_str)
        except:
            return 30.0  # Default 30 seconds

    def _select_clips_for_duration(
        self, clips: List[Dict], target_duration: float
    ) -> List[Dict]:
        """
        Select clips that fit target duration.

        Args:
            clips: List of clip data dicts
            target_duration: Target total duration

        Returns:
            Selected clips
        """
        selected = []
        current_duration = 0

        # Shuffle for variety
        import random
        random.shuffle(clips)

        for clip in clips:
            if current_duration >= target_duration:
                break

            remaining = target_duration - current_duration
            clip_duration = clip["duration"]

            # Use full clip if it fits, otherwise trim
            if clip_duration <= remaining:
                selected.append(clip)
                current_duration += clip_duration
            elif remaining >= 3.0:  # At least 3 seconds
                # Trim clip to fit remaining time
                clip["end"] = clip["start"] + remaining
                clip["duration"] = remaining
                selected.append(clip)
                current_duration = target_duration
                break

        return selected

    async def create_compilation_reel(
        self,
        posts: List[Dict[str, Any]],
        theme: str,
        duration: int = 45,
        include_text: bool = True,
    ) -> Optional[Path]:
        """
        Create a compilation reel from multiple posts on a theme.

        Args:
            posts: List of posts to compile
            theme: Theme text for overlay
            duration: Target duration in seconds
            include_text: Add text overlays

        Returns:
            Path to generated reel
        """
        try:
            logger.info(f"Creating compilation reel: {theme} ({duration}s)")

            # Download source media
            downloaded = await self.download_batch(posts)

            if len(downloaded) < 2:
                logger.error("Need at least 2 media files for compilation")
                return None

            # Process each media file
            clips = []
            clip_duration = duration / len(downloaded)

            for i, (media_id, filepath) in enumerate(downloaded):
                # Load video or image
                if filepath.suffix.lower() in ['.mp4', '.mov']:
                    media = self.editor.load_video(filepath)

                    # Extract best segment
                    if media.duration > clip_duration:
                        # Take middle segment
                        start = (media.duration - clip_duration) / 2
                        media = self.editor.trim_clip(media, start, start + clip_duration)
                else:
                    # Image - convert to video clip
                    media = self.editor.load_image(filepath, duration=clip_duration)

                # Resize for reels
                media = self.editor.resize_for_instagram(media, content_type="reel")

                # Add text if requested
                if include_text:
                    caption = posts[i].get("caption", "")[:50]
                    if caption:
                        media = self.editor.add_text_overlay(
                            media,
                            text=caption,
                            position="bottom",
                            fontsize=40,
                            duration=min(3.0, clip_duration)
                        )

                clips.append(media)

            # Concatenate with transitions
            final_video = self.editor.concatenate_clips(
                clips, transition="crossfade", transition_duration=0.5
            )

            # Add theme text at start
            if theme:
                final_video = self.editor.add_text_overlay(
                    final_video,
                    text=theme,
                    position="top",
                    fontsize=70,
                    duration=3.0,
                    start_time=0
                )

            # Export
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.editor.export_video(
                final_video,
                self.outputs_dir / f"compilation_{timestamp}.mp4",
                bitrate="8000k"
            )

            logger.info(f"✅ Compilation reel created: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to create compilation: {e}")
            return None

    def cleanup(self):
        """Clean up temporary files."""
        try:
            self.editor.cleanup()
            logger.info("Cleaned up video processor")
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
