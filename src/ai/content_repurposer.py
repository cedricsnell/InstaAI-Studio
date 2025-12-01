"""
AI-powered content repurposing engine.
Analyzes existing Instagram posts and generates new content variations.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import anthropic
import os

logger = logging.getLogger(__name__)


class ContentRepurposer:
    """
    Analyzes Instagram posts and generates repurposing strategies.
    Uses Claude AI to understand what makes content successful.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize content repurposer.

        Args:
            api_key: Anthropic API key (defaults to env var ANTHROPIC_API_KEY)
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = "claude-3-5-sonnet-20241022"

    def analyze_top_performing_posts(
        self, posts: List[Dict[str, Any]], account_context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Analyze top-performing posts to identify success patterns.

        Args:
            posts: List of Instagram posts with engagement metrics
            account_context: Optional account info (niche, audience, etc.)

        Returns:
            {
                "content_themes": [...],
                "successful_formats": [...],
                "caption_patterns": [...],
                "optimal_posting_times": [...],
                "engagement_insights": {...},
                "repurposing_opportunities": [...]
            }
        """
        if not posts:
            return {"error": "No posts provided for analysis"}

        # Sort by engagement rate
        sorted_posts = sorted(
            posts, key=lambda p: p.get("engagement_rate", 0), reverse=True
        )
        top_posts = sorted_posts[:10]  # Analyze top 10

        # Build analysis prompt
        posts_data = []
        for i, post in enumerate(top_posts, 1):
            posts_data.append({
                "rank": i,
                "type": post.get("media_type"),
                "caption": post.get("caption", "")[:500],  # First 500 chars
                "engagement_rate": post.get("engagement_rate"),
                "likes": post.get("likes_count"),
                "comments": post.get("comments_count"),
                "saves": post.get("saves_count"),
                "timestamp": post.get("timestamp"),
            })

        prompt = f"""Analyze these top-performing Instagram posts and provide strategic insights for content repurposing:

{self._format_posts_for_analysis(posts_data)}

Account Context:
{self._format_account_context(account_context)}

Provide a comprehensive analysis including:

1. **Content Themes**: What topics/themes consistently perform well?

2. **Successful Formats**: Which content types (images, videos, carousels) get the most engagement?

3. **Caption Patterns**: What caption styles, lengths, and structures work best?

4. **Timing Insights**: Any patterns in posting times?

5. **Engagement Drivers**: What specific elements drive saves, comments, or likes?

6. **Repurposing Opportunities**: Specific ideas for how to repurpose this content into new posts/reels. Be creative and specific!

Format your response as JSON with these exact keys:
- content_themes: [array of theme objects with "theme" and "evidence" fields]
- successful_formats: [array of format insights]
- caption_patterns: [array of caption strategy objects]
- timing_insights: [array of timing patterns]
- engagement_drivers: [array of specific tactics]
- repurposing_opportunities: [array of detailed repurposing ideas with "idea", "source_posts", "format", "expected_engagement"]

Be specific, actionable, and data-driven."""

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = message.content[0].text

            # Parse JSON response
            import json

            # Extract JSON from markdown code blocks if present
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            analysis = json.loads(response_text)

            logger.info("Successfully analyzed top-performing posts")
            return analysis

        except Exception as e:
            logger.error(f"Failed to analyze posts: {e}")
            return {
                "error": str(e),
                "fallback_insights": self._generate_fallback_insights(posts_data),
            }

    def generate_reel_ideas(
        self,
        source_posts: List[Dict[str, Any]],
        analysis: Dict[str, Any],
        count: int = 10,
        niche: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generate specific reel ideas based on top-performing content.

        Args:
            source_posts: Available posts to repurpose
            analysis: Content analysis from analyze_top_performing_posts()
            count: Number of reel ideas to generate
            niche: Industry/niche for context

        Returns:
            List of reel ideas with scripts, hooks, and production notes
        """
        # Filter video posts
        video_posts = [
            p for p in source_posts if p.get("media_type") in ["VIDEO", "REELS"]
        ]

        # Get top themes from analysis
        themes = analysis.get("content_themes", [])
        themes_text = "\n".join([f"- {t.get('theme', '')}" for t in themes[:5]])

        prompt = f"""Based on this content analysis, generate {count} high-performing reel ideas:

**Top Content Themes:**
{themes_text}

**Niche:** {niche or 'General'}

**Available Source Content:**
{len(video_posts)} videos and {len(source_posts) - len(video_posts)} images available for repurposing

**Repurposing Opportunities:**
{self._format_repurposing_opps(analysis.get('repurposing_opportunities', []))}

Generate {count} reel concepts that:
1. Leverage proven content themes
2. Follow Instagram Reels best practices (hook in 1st second, 15-60 second duration)
3. Can be created by repurposing existing content
4. Have high viral potential

For each reel, provide:
- **Title**: Catchy, scroll-stopping title
- **Hook**: First 3 seconds (text/visual hook)
- **Script**: Full voiceover/text overlay script
- **Visual Plan**: How to stitch/edit existing content
- **Duration**: Target duration (15-60s)
- **Source Content**: Which posts to use
- **CTA**: Call-to-action
- **Caption**: Instagram caption with hashtags
- **Music Suggestion**: Trending audio style
- **Expected Engagement**: Predicted performance (Low/Medium/High/Viral)

Format as JSON array with these exact fields for each reel."""

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=8000,
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = message.content[0].text

            # Parse JSON
            import json

            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            reel_ideas = json.loads(response_text)

            logger.info(f"Generated {len(reel_ideas)} reel ideas")
            return reel_ideas

        except Exception as e:
            logger.error(f"Failed to generate reel ideas: {e}")
            return []

    def generate_carousel_from_content(
        self, theme: str, source_posts: List[Dict[str, Any]], slide_count: int = 7
    ) -> Dict[str, Any]:
        """
        Generate a carousel post concept from existing content.

        Args:
            theme: Main theme/topic for carousel
            source_posts: Posts to pull content from
            slide_count: Number of slides (2-10)

        Returns:
            {
                "title": "...",
                "slides": [...],
                "caption": "...",
                "design_notes": "..."
            }
        """
        slide_count = max(2, min(10, slide_count))

        # Get relevant posts
        relevant_posts = []
        for post in source_posts:
            caption = post.get("caption", "").lower()
            if theme.lower() in caption or len(relevant_posts) < slide_count:
                relevant_posts.append(post)
            if len(relevant_posts) >= slide_count * 2:
                break

        prompt = f"""Create a {slide_count}-slide Instagram carousel about: {theme}

**Source Content Available:**
{self._format_posts_brief(relevant_posts[:20])}

Design a carousel that:
1. Starts with an attention-grabbing title slide
2. Provides value through educational/entertaining content
3. Ends with a strong CTA
4. Uses consistent visual branding
5. Can be created using screenshots/clips from source posts

Provide:
- **Carousel Title**: Hook-driven title for slide 1
- **Slides**: Array of {slide_count} slide objects with:
  - slide_number
  - headline (3-7 words)
  - body_text (15-30 words)
  - visual_direction (how to create this slide from source content)
  - source_post_ids (which posts to reference)
- **Caption**: Engaging Instagram caption with hashtags
- **Design Notes**: Visual style, colors, fonts
- **CTA**: Final call-to-action

Format as JSON."""

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = message.content[0].text

            import json

            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            carousel = json.loads(response_text)

            logger.info(f"Generated {slide_count}-slide carousel concept")
            return carousel

        except Exception as e:
            logger.error(f"Failed to generate carousel: {e}")
            return {"error": str(e)}

    # Helper methods
    def _format_posts_for_analysis(self, posts: List[Dict]) -> str:
        """Format posts for AI analysis."""
        formatted = []
        for post in posts:
            formatted.append(
                f"""
Post #{post['rank']}:
- Type: {post['type']}
- Engagement Rate: {post['engagement_rate']:.2f}%
- Likes: {post['likes']}, Comments: {post['comments']}, Saves: {post['saves']}
- Posted: {post['timestamp']}
- Caption: {post['caption']}
---"""
            )
        return "\n".join(formatted)

    def _format_account_context(self, context: Optional[Dict]) -> str:
        """Format account context."""
        if not context:
            return "No additional context provided"

        return f"""
Niche: {context.get('niche', 'Unknown')}
Followers: {context.get('followers_count', 'N/A')}
Account Type: {context.get('account_type', 'N/A')}
"""

    def _format_repurposing_opps(self, opps: List[Dict]) -> str:
        """Format repurposing opportunities."""
        if not opps:
            return "No specific opportunities identified yet"

        formatted = []
        for i, opp in enumerate(opps[:5], 1):
            formatted.append(
                f"{i}. {opp.get('idea', 'N/A')} (Format: {opp.get('format', 'N/A')})"
            )
        return "\n".join(formatted)

    def _format_posts_brief(self, posts: List[Dict]) -> str:
        """Brief format for posts list."""
        return "\n".join(
            [
                f"- Post {i}: {p.get('media_type')} ({p.get('engagement_rate', 0):.1f}% engagement)"
                for i, p in enumerate(posts, 1)
            ]
        )

    def _generate_fallback_insights(self, posts: List[Dict]) -> Dict:
        """Generate basic insights if AI fails."""
        # Count media types
        type_counts = {}
        for post in posts:
            media_type = post.get("type", "UNKNOWN")
            type_counts[media_type] = type_counts.get(media_type, 0) + 1

        return {
            "content_themes": [{"theme": "Various topics", "evidence": "Multiple posts"}],
            "successful_formats": [
                {
                    "format": f"{k} ({v} posts)",
                    "performance": "Top performer" if v == max(type_counts.values()) else "Good",
                }
                for k, v in type_counts.items()
            ],
            "caption_patterns": [
                {"pattern": "Varies", "recommendation": "Analyze manually"}
            ],
        }
