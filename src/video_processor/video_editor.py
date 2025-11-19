"""
Core video editing functionality using MoviePy and FFmpeg
"""
from typing import List, Tuple, Optional, Union
from pathlib import Path
import numpy as np
from moviepy.editor import (
    VideoFileClip, ImageClip, AudioFileClip, CompositeVideoClip,
    TextClip, concatenate_videoclips, CompositeAudioClip
)
from moviepy.video.fx import resize, crop, fadein, fadeout
from moviepy.video.tools.cuts import detect_scenes
import logging

logger = logging.getLogger(__name__)


class VideoEditor:
    """Main video editing engine"""

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_clips = []

    def load_video(self, video_path: Union[str, Path]) -> VideoFileClip:
        """Load a video file"""
        try:
            clip = VideoFileClip(str(video_path))
            logger.info(f"Loaded video: {video_path} (duration: {clip.duration}s)")
            return clip
        except Exception as e:
            logger.error(f"Failed to load video {video_path}: {e}")
            raise

    def load_image(self, image_path: Union[str, Path], duration: float = 5.0) -> ImageClip:
        """Load an image and convert to video clip"""
        try:
            clip = ImageClip(str(image_path), duration=duration)
            logger.info(f"Loaded image: {image_path} (duration: {duration}s)")
            return clip
        except Exception as e:
            logger.error(f"Failed to load image {image_path}: {e}")
            raise

    def trim_clip(self, clip: VideoFileClip, start: float, end: float) -> VideoFileClip:
        """Trim a video clip to specified time range"""
        try:
            trimmed = clip.subclip(start, end)
            logger.info(f"Trimmed clip from {start}s to {end}s")
            return trimmed
        except Exception as e:
            logger.error(f"Failed to trim clip: {e}")
            raise

    def create_jump_cuts(
        self,
        clip: VideoFileClip,
        segments: List[Tuple[float, float]],
        transition_duration: float = 0.0
    ) -> VideoFileClip:
        """
        Create jump cuts by keeping only specified segments

        Args:
            clip: Source video clip
            segments: List of (start, end) time tuples to keep
            transition_duration: Optional crossfade between segments
        """
        try:
            subclips = []
            for start, end in segments:
                subclip = clip.subclip(start, end)
                if transition_duration > 0 and len(subclips) > 0:
                    subclip = subclip.crossfadein(transition_duration)
                subclips.append(subclip)

            result = concatenate_videoclips(subclips, method="compose")
            logger.info(f"Created jump cuts with {len(segments)} segments")
            return result
        except Exception as e:
            logger.error(f"Failed to create jump cuts: {e}")
            raise

    def auto_detect_cuts(
        self,
        clip: VideoFileClip,
        threshold: float = 20.0,
        min_scene_duration: float = 1.0
    ) -> List[Tuple[float, float]]:
        """
        Automatically detect scene changes for jump cuts

        Args:
            clip: Source video clip
            threshold: Sensitivity for scene detection (lower = more sensitive)
            min_scene_duration: Minimum duration for a scene
        """
        try:
            # Detect scenes using MoviePy
            scenes = detect_scenes(clip, threshold=threshold)

            # Filter out very short scenes
            filtered_scenes = []
            for i, (start, end) in enumerate(scenes):
                if end - start >= min_scene_duration:
                    filtered_scenes.append((start, end))

            logger.info(f"Auto-detected {len(filtered_scenes)} scenes")
            return filtered_scenes
        except Exception as e:
            logger.error(f"Failed to auto-detect cuts: {e}")
            # Fallback: return entire video as one scene
            return [(0, clip.duration)]

    def resize_for_instagram(
        self,
        clip: Union[VideoFileClip, ImageClip],
        content_type: str = 'reel',
        method: str = 'crop'
    ) -> Union[VideoFileClip, ImageClip]:
        """
        Resize video/image for Instagram specs

        Args:
            clip: Source clip
            content_type: 'reel', 'story', 'carousel', or 'feed'
            method: 'crop' or 'pad' (pad adds black bars)
        """
        from ..config import Config

        specs = Config.INSTAGRAM_SPECS.get(content_type, Config.INSTAGRAM_SPECS['reel'])
        target_width, target_height = specs['resolution']
        target_ratio = target_width / target_height

        # Get current dimensions
        current_ratio = clip.w / clip.h

        if method == 'crop':
            if current_ratio > target_ratio:
                # Video is wider, crop width
                new_width = int(clip.h * target_ratio)
                x_center = clip.w / 2
                clip = crop(clip, x1=x_center - new_width/2, width=new_width)
            else:
                # Video is taller, crop height
                new_height = int(clip.w / target_ratio)
                y_center = clip.h / 2
                clip = crop(clip, y1=y_center - new_height/2, height=new_height)

        # Resize to exact dimensions
        clip = resize(clip, newsize=(target_width, target_height))
        logger.info(f"Resized clip to {target_width}x{target_height} for {content_type}")
        return clip

    def add_text_overlay(
        self,
        clip: VideoFileClip,
        text: str,
        position: Union[str, Tuple[float, float]] = 'center',
        fontsize: int = 70,
        color: str = 'white',
        font: str = 'Arial-Bold',
        duration: Optional[float] = None,
        start_time: float = 0,
        bg_color: Optional[str] = None,
        stroke_color: Optional[str] = 'black',
        stroke_width: int = 2
    ) -> VideoFileClip:
        """
        Add text overlay to video

        Args:
            clip: Source video clip
            text: Text to display
            position: 'center', 'top', 'bottom', or (x, y) tuple
            fontsize: Font size
            color: Text color
            font: Font name
            duration: Text duration (None = entire clip)
            start_time: When text appears
            bg_color: Background color (None = transparent)
            stroke_color: Outline color
            stroke_width: Outline width
        """
        try:
            # Create text clip
            txt_clip = TextClip(
                text,
                fontsize=fontsize,
                color=color,
                font=font,
                stroke_color=stroke_color,
                stroke_width=stroke_width,
                bg_color=bg_color,
                method='caption',
                size=(clip.w * 0.8, None)  # Max width 80% of video
            )

            # Set duration and position
            if duration is None:
                duration = clip.duration - start_time

            txt_clip = txt_clip.set_duration(duration).set_start(start_time)

            # Handle position
            if isinstance(position, str):
                txt_clip = txt_clip.set_position(position)
            else:
                txt_clip = txt_clip.set_position(position)

            # Composite video with text
            result = CompositeVideoClip([clip, txt_clip])
            logger.info(f"Added text overlay: '{text[:30]}...'")
            return result
        except Exception as e:
            logger.error(f"Failed to add text overlay: {e}")
            raise

    def add_audio(
        self,
        clip: VideoFileClip,
        audio_path: Union[str, Path],
        start_time: float = 0,
        volume: float = 1.0,
        fade_in: float = 0,
        fade_out: float = 0,
        loop: bool = False
    ) -> VideoFileClip:
        """
        Add or replace audio track

        Args:
            clip: Source video clip
            audio_path: Path to audio file
            start_time: When audio starts
            volume: Audio volume (0.0 to 1.0)
            fade_in: Fade in duration (seconds)
            fade_out: Fade out duration (seconds)
            loop: Loop audio to match video duration
        """
        try:
            audio = AudioFileClip(str(audio_path))

            # Apply volume
            if volume != 1.0:
                audio = audio.volumex(volume)

            # Apply fades
            if fade_in > 0:
                audio = audio.audio_fadein(fade_in)
            if fade_out > 0:
                audio = audio.audio_fadeout(fade_out)

            # Loop if needed
            if loop and audio.duration < clip.duration:
                n_loops = int(np.ceil(clip.duration / audio.duration))
                audio = concatenate_videoclips([audio] * n_loops)

            # Trim to video duration
            audio = audio.subclip(0, min(audio.duration, clip.duration))

            # Set start time
            if start_time > 0:
                audio = audio.set_start(start_time)

            # Mix with existing audio or replace
            if clip.audio is not None:
                final_audio = CompositeAudioClip([clip.audio, audio])
            else:
                final_audio = audio

            result = clip.set_audio(final_audio)
            logger.info(f"Added audio from {audio_path}")
            return result
        except Exception as e:
            logger.error(f"Failed to add audio: {e}")
            raise

    def concatenate_clips(
        self,
        clips: List[Union[VideoFileClip, ImageClip]],
        transition: Optional[str] = None,
        transition_duration: float = 0.5
    ) -> VideoFileClip:
        """
        Concatenate multiple clips into one

        Args:
            clips: List of video/image clips
            transition: None, 'crossfade', 'fadein', 'fadeout'
            transition_duration: Transition effect duration
        """
        try:
            if transition == 'crossfade':
                # Add crossfade between clips
                for i in range(1, len(clips)):
                    clips[i] = clips[i].crossfadein(transition_duration)
            elif transition == 'fadein':
                clips[0] = fadein(clips[0], transition_duration)
            elif transition == 'fadeout':
                clips[-1] = fadeout(clips[-1], transition_duration)

            result = concatenate_videoclips(clips, method="compose")
            logger.info(f"Concatenated {len(clips)} clips")
            return result
        except Exception as e:
            logger.error(f"Failed to concatenate clips: {e}")
            raise

    def apply_speed_effect(
        self,
        clip: VideoFileClip,
        factor: float
    ) -> VideoFileClip:
        """
        Apply speed effect (slow motion or fast forward)

        Args:
            clip: Source clip
            factor: Speed factor (0.5 = half speed, 2.0 = double speed)
        """
        try:
            result = clip.fx(lambda c: c.speedx(factor))
            logger.info(f"Applied {factor}x speed effect")
            return result
        except Exception as e:
            logger.error(f"Failed to apply speed effect: {e}")
            raise

    def export_video(
        self,
        clip: VideoFileClip,
        output_path: Union[str, Path],
        codec: str = 'libx264',
        audio_codec: str = 'aac',
        bitrate: str = '5000k',
        fps: int = 30,
        preset: str = 'medium'
    ) -> Path:
        """
        Export final video

        Args:
            clip: Video clip to export
            output_path: Output file path
            codec: Video codec
            audio_codec: Audio codec
            bitrate: Video bitrate
            fps: Frames per second
            preset: Encoding preset (ultrafast, fast, medium, slow)
        """
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            clip.write_videofile(
                str(output_path),
                codec=codec,
                audio_codec=audio_codec,
                bitrate=bitrate,
                fps=fps,
                preset=preset,
                threads=4,
                logger=None  # Suppress moviepy's verbose output
            )

            logger.info(f"Exported video to {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Failed to export video: {e}")
            raise
        finally:
            # Clean up
            clip.close()

    def cleanup(self):
        """Clean up temporary clips"""
        for clip in self.temp_clips:
            try:
                clip.close()
            except:
                pass
        self.temp_clips.clear()
