"""
Natural Language Command Parser using AI
Converts natural language instructions into structured video editing commands
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from anthropic import Anthropic
from openai import OpenAI

logger = logging.getLogger(__name__)


class NaturalLanguageParser:
    """Parse natural language editing commands using AI"""

    SYSTEM_PROMPT = """You are an expert video editing assistant. Your job is to convert natural language editing instructions into structured JSON commands that can be executed by a video editing system.

Available editing operations:
1. **trim**: Cut video to specific time range
   - Parameters: start_time (seconds), end_time (seconds)

2. **jump_cuts**: Create jump cuts by keeping specific segments
   - Parameters: segments (list of [start, end] time pairs)

3. **auto_jump_cuts**: Automatically detect and create jump cuts
   - Parameters: threshold (optional, default 20), min_duration (optional, default 1.0)

4. **add_text**: Add text overlay
   - Parameters: text, position (center/top/bottom), start_time, duration, fontsize, color, stroke_color

5. **add_music**: Add background music
   - Parameters: audio_file, volume (0-1), fade_in, fade_out, loop (true/false)

6. **concatenate**: Join multiple clips
   - Parameters: clip_indices (list), transition (none/crossfade/fadein/fadeout)

7. **speed**: Change playback speed
   - Parameters: factor (0.5 = slow, 2.0 = fast)

8. **resize**: Resize for Instagram format
   - Parameters: content_type (reel/story/carousel/feed), method (crop/pad)

9. **add_cta**: Add call-to-action text
   - Parameters: text, position, start_time, duration

Return ONLY valid JSON in this format:
{
  "operations": [
    {
      "type": "operation_name",
      "params": { ... }
    }
  ],
  "metadata": {
    "content_type": "reel|story|carousel|feed",
    "description": "brief description of what will be done"
  }
}

Be smart about inferring parameters. For example:
- "Add CTA at the end" means start_time should be near the end of the video
- "Make it a reel" means resize to reel format
- "Add upbeat music" means look for upbeat music files
- "Remove pauses" means use auto_jump_cuts
- "Speed it up" means speed factor around 1.5-2.0
"""

    def __init__(self, provider: str = 'anthropic', api_key: Optional[str] = None):
        """
        Initialize the parser

        Args:
            provider: 'anthropic' or 'openai'
            api_key: API key (if not provided, will use environment variable)
        """
        self.provider = provider.lower()

        if self.provider == 'anthropic':
            self.client = Anthropic(api_key=api_key)
            self.model = "claude-3-5-sonnet-20241022"
        elif self.provider == 'openai':
            self.client = OpenAI(api_key=api_key)
            self.model = "gpt-4-turbo-preview"
        else:
            raise ValueError(f"Unsupported provider: {provider}")

        logger.info(f"Initialized NL parser with {provider}")

    def parse_command(
        self,
        command: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Parse natural language command into structured operations

        Args:
            command: Natural language editing instruction
            context: Optional context (video duration, available music, etc.)

        Returns:
            Dict with 'operations' and 'metadata'
        """
        try:
            # Build the user message with context
            user_message = f"Editing instruction: {command}"

            if context:
                user_message += f"\n\nContext:\n{json.dumps(context, indent=2)}"

            # Call AI API
            if self.provider == 'anthropic':
                response = self._call_anthropic(user_message)
            else:
                response = self._call_openai(user_message)

            # Parse JSON response
            result = json.loads(response)

            # Validate structure
            if 'operations' not in result:
                raise ValueError("Response missing 'operations' field")

            logger.info(f"Parsed command: {len(result['operations'])} operations")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            logger.error(f"Response was: {response}")
            raise ValueError("AI returned invalid JSON")
        except Exception as e:
            logger.error(f"Failed to parse command: {e}")
            raise

    def _call_anthropic(self, user_message: str) -> str:
        """Call Anthropic Claude API"""
        message = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            system=self.SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": user_message}
            ]
        )
        return message.content[0].text

    def _call_openai(self, user_message: str) -> str:
        """Call OpenAI GPT API"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            response_format={"type": "json_object"}
        )
        return response.choices[0].message.content

    def parse_batch_commands(
        self,
        commands: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Parse multiple commands in sequence

        Args:
            commands: List of natural language commands
            context: Optional context

        Returns:
            List of parsed command dicts
        """
        results = []
        for i, command in enumerate(commands):
            try:
                result = self.parse_command(command, context)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to parse command {i+1}: {command}")
                logger.error(f"Error: {e}")
                # Continue with other commands
        return results

    def validate_operations(self, operations: List[Dict]) -> List[str]:
        """
        Validate parsed operations

        Returns:
            List of validation warnings/errors
        """
        issues = []
        valid_types = {
            'trim', 'jump_cuts', 'auto_jump_cuts', 'add_text',
            'add_music', 'concatenate', 'speed', 'resize', 'add_cta'
        }

        for i, op in enumerate(operations):
            if 'type' not in op:
                issues.append(f"Operation {i+1}: Missing 'type' field")
                continue

            if op['type'] not in valid_types:
                issues.append(f"Operation {i+1}: Unknown type '{op['type']}'")

            if 'params' not in op:
                issues.append(f"Operation {i+1}: Missing 'params' field")

        return issues


class CommandExecutor:
    """Execute parsed commands on VideoEditor"""

    def __init__(self, video_editor):
        """
        Initialize executor

        Args:
            video_editor: VideoEditor instance
        """
        self.editor = video_editor
        self.context = {}

    def execute_operations(
        self,
        operations: List[Dict],
        input_clip,
        context: Optional[Dict] = None
    ):
        """
        Execute a list of operations on a clip

        Args:
            operations: List of operation dicts
            input_clip: Source video/image clip
            context: Execution context (available music files, etc.)

        Returns:
            Final edited clip
        """
        if context:
            self.context.update(context)

        current_clip = input_clip

        for i, op in enumerate(operations):
            try:
                current_clip = self._execute_single_operation(op, current_clip)
                logger.info(f"Executed operation {i+1}/{len(operations)}: {op['type']}")
            except Exception as e:
                logger.error(f"Failed to execute operation {i+1}: {op}")
                logger.error(f"Error: {e}")
                raise

        return current_clip

    def _execute_single_operation(self, operation: Dict, clip):
        """Execute a single operation"""
        op_type = operation['type']
        params = operation.get('params', {})

        if op_type == 'trim':
            return self.editor.trim_clip(clip, **params)

        elif op_type == 'jump_cuts':
            return self.editor.create_jump_cuts(clip, **params)

        elif op_type == 'auto_jump_cuts':
            segments = self.editor.auto_detect_cuts(clip, **params)
            return self.editor.create_jump_cuts(clip, segments)

        elif op_type == 'add_text' or op_type == 'add_cta':
            return self.editor.add_text_overlay(clip, **params)

        elif op_type == 'add_music':
            # Resolve music file path if needed
            if 'audio_file' in params and not Path(params['audio_file']).exists():
                # Look in music directory
                music_dir = self.context.get('music_dir')
                if music_dir:
                    params['audio_file'] = music_dir / params['audio_file']
            return self.editor.add_audio(clip, **params)

        elif op_type == 'speed':
            return self.editor.apply_speed_effect(clip, **params)

        elif op_type == 'resize':
            return self.editor.resize_for_instagram(clip, **params)

        elif op_type == 'concatenate':
            # This would need multiple clips - handle specially
            raise NotImplementedError("Concatenate needs to be handled at a higher level")

        else:
            raise ValueError(f"Unknown operation type: {op_type}")


# Example usage
if __name__ == "__main__":
    # Test the parser
    parser = NaturalLanguageParser(provider='anthropic')

    test_commands = [
        "Create a reel from this video, add jump cuts to remove pauses, and add text 'Check this out!' at the beginning",
        "Add upbeat background music at 50% volume with fade in and out",
        "Speed up the video by 1.5x and add a CTA 'Link in bio' at the end",
        "Make it vertical for Instagram stories with the subject centered"
    ]

    context = {
        "video_duration": 45.0,
        "available_music": ["upbeat.mp3", "chill.mp3", "energetic.mp3"]
    }

    for cmd in test_commands:
        print(f"\nCommand: {cmd}")
        result = parser.parse_command(cmd, context)
        print(json.dumps(result, indent=2))
