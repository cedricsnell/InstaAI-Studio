"""
AI-powered Instagram insights analyzer using Claude.
Generates marketing recommendations based on account performance.
"""
import os
import json
import logging
from typing import Dict, Any, List, Optional
from anthropic import Anthropic
from datetime import datetime

logger = logging.getLogger(__name__)


class InsightsAnalyzer:
    """Analyzes Instagram insights and generates AI-powered recommendations."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize insights analyzer.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if self.api_key:
            self.client = Anthropic(api_key=self.api_key)
        else:
            logger.warning("Anthropic API key not configured. AI analysis will be unavailable.")
            self.client = None

    def analyze_insights(
        self,
        insights_data: Dict[str, Any],
        campaign_goal: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze Instagram insights and generate recommendations.

        Args:
            insights_data: Full insights data from Instagram Graph API
            campaign_goal: Optional campaign goal info
                {
                    "type": "awareness" | "traffic" | "conversions" | "engagement",
                    "product_name": "...",
                    "product_price": 99.99,
                    "target_audience": "...",
                    "budget": 500
                }

        Returns:
            {
                "summary": "...",
                "ad_formats": [...],
                "targeting": {...},
                "budget_allocation": {...},
                "posting_schedule": {...},
                "content_strategy": {...},
                "roi_projection": {...},
                "generated_at": "..."
            }
        """
        if not self.client:
            logger.warning("Claude API not available, using default recommendations")
            return get_default_recommendations(insights_data)

        try:
            # Build analysis prompt
            prompt = self._build_analysis_prompt(insights_data, campaign_goal)

            # Call Claude API
            logger.info("Sending insights to Claude for analysis...")
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                temperature=0.7,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # Extract JSON response
            response_text = message.content[0].text

            # Parse JSON from response
            # Claude might wrap it in markdown code blocks
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            recommendations = json.loads(response_text)
            recommendations["generated_at"] = datetime.utcnow().isoformat()

            logger.info("Successfully generated AI recommendations")
            return recommendations

        except Exception as e:
            logger.error(f"Failed to analyze insights with Claude: {e}")
            logger.info("Falling back to default recommendations")
            return get_default_recommendations(insights_data)

    def _build_analysis_prompt(
        self,
        insights_data: Dict[str, Any],
        campaign_goal: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build comprehensive analysis prompt for Claude."""
        account = insights_data.get("account", {})
        account_insights = insights_data.get("account_insights", [])
        media = insights_data.get("media", [])[:20]  # Top 20 posts
        audience = insights_data.get("audience", [])

        # Extract key metrics
        follower_count = account.get("followers_count", 0)
        media_count = account.get("media_count", 0)

        # Calculate average engagement
        total_engagement = 0
        total_reach = 0
        for post in media:
            insights = post.get("insights", [])
            for insight in insights:
                if insight["name"] == "engagement":
                    total_engagement += insight["values"][0].get("value", 0)
                elif insight["name"] == "reach":
                    total_reach += insight["values"][0].get("value", 0)

        avg_engagement_rate = (total_engagement / total_reach * 100) if total_reach > 0 else 0

        # Content type breakdown
        content_types = {}
        for post in media:
            media_type = post.get("media_type", "IMAGE")
            content_types[media_type] = content_types.get(media_type, 0) + 1

        # Build prompt
        prompt = f"""You are an expert Instagram marketing strategist. Analyze this Instagram Business account data and provide comprehensive, actionable marketing recommendations.

## Account Overview
- Username: @{account.get('username', 'unknown')}
- Account Type: {account.get('account_type', 'BUSINESS')}
- Followers: {follower_count:,}
- Total Posts: {media_count}
- Average Engagement Rate: {avg_engagement_rate:.2f}%

## Content Performance (Last {len(media)} Posts)
{json.dumps([{
    'type': p.get('media_type'),
    'caption': p.get('caption', '')[:100] + '...' if p.get('caption') and len(p.get('caption', '')) > 100 else p.get('caption', ''),
    'likes': p.get('like_count', 0),
    'comments': p.get('comments_count', 0),
    'timestamp': p.get('timestamp', '')
} for p in media[:10]], indent=2)}

## Content Type Distribution
{json.dumps(content_types, indent=2)}

## Audience Demographics
{json.dumps([{
    'metric': a.get('name'),
    'data': a.get('values', [{}])[0].get('value', {}) if a.get('values') else {}
} for a in audience[:3]], indent=2)}

{"## Campaign Goal" if campaign_goal else ""}
{json.dumps(campaign_goal, indent=2) if campaign_goal else ""}

## Your Task
Analyze this data and provide strategic marketing recommendations in the following JSON format:

{{
  "summary": "2-3 sentence executive summary of key insights and top recommendation",

  "ad_formats": [
    {{
      "format": "REELS" | "IMAGE" | "VIDEO" | "CAROUSEL_ALBUM",
      "score": 85,  // 0-100 based on past performance
      "reasoning": "Why this format will perform well"
    }},
    // Top 3 formats
  ],

  "targeting": {{
    "age_ranges": ["18-24", "25-34", "35-44"],
    "genders": ["F", "M", "ALL"],
    "locations": ["New York, NY", "Los Angeles, CA"],  // Top cities from audience
    "interests": ["wellness", "fitness", "lifestyle"],  // Based on content
    "lookalike": true,  // Recommend lookalike audience?
    "reasoning": "Why target this audience"
  }},

  "budget_allocation": {{
    "instagram": 70,  // Percentage
    "facebook": 20,
    "google": 10,
    "reasoning": "Why this allocation"
  }},

  "posting_schedule": {{
    "best_days": ["Tuesday", "Thursday", "Saturday"],
    "best_times": ["9:00 AM", "12:00 PM", "6:00 PM"],  // In user's timezone
    "frequency": "Daily" | "3-5 times per week" | "2-3 times per week",
    "reasoning": "Based on when audience is most active"
  }},

  "content_strategy": {{
    "tone": "professional" | "casual" | "inspirational" | "educational",
    "topics": ["topic1", "topic2", "topic3"],  // Based on top performers
    "hashtags": ["#hashtag1", "#hashtag2"],  // 8-12 relevant hashtags
    "call_to_action": "Click link in bio" | "DM us" | "Visit website",
    "reasoning": "What content resonates with this audience"
  }},

  "roi_projection": {{
    "estimated_reach": 50000,  // Conservative estimate
    "estimated_clicks": 1000,  // Based on 2% CTR
    "estimated_conversions": 50,  // Based on 5% conversion rate
    "estimated_revenue": 5000,  // conversions * average order value
    "confidence": "high" | "medium" | "low",
    "assumptions": "Key assumptions for these projections"
  }}
}}

Focus on:
1. Data-driven recommendations based on actual performance
2. Actionable insights that can be implemented immediately
3. Realistic projections based on the account's current metrics
4. Specific, concrete suggestions (not generic advice)

Return ONLY the JSON object, no additional text."""

        return prompt


def get_default_recommendations(insights_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate data-driven default recommendations when AI is unavailable.

    Args:
        insights_data: Instagram insights data

    Returns:
        Recommendation structure (same as AI-generated)
    """
    media = insights_data.get("media", [])
    account = insights_data.get("account", {})
    audience = insights_data.get("audience", [])

    # Analyze content type performance
    content_performance = {}
    for post in media:
        media_type = post.get("media_type", "IMAGE")
        if media_type not in content_performance:
            content_performance[media_type] = {
                "count": 0,
                "total_engagement": 0,
                "total_reach": 0
            }

        insights = post.get("insights", [])
        engagement = 0
        reach = 0
        for insight in insights:
            if insight["name"] == "engagement":
                engagement = insight["values"][0].get("value", 0)
            elif insight["name"] == "reach":
                reach = insight["values"][0].get("value", 0)

        content_performance[media_type]["count"] += 1
        content_performance[media_type]["total_engagement"] += engagement
        content_performance[media_type]["total_reach"] += reach

    # Calculate engagement rates
    format_scores = []
    for media_type, perf in content_performance.items():
        if perf["total_reach"] > 0:
            engagement_rate = (perf["total_engagement"] / perf["total_reach"]) * 100
            format_scores.append({
                "format": media_type,
                "score": min(int(engagement_rate * 10), 100),  # Scale to 0-100
                "reasoning": f"Based on {perf['count']} posts with {engagement_rate:.1f}% avg engagement"
            })

    # Sort by score
    format_scores.sort(key=lambda x: x["score"], reverse=True)

    # Extract audience demographics
    age_ranges = []
    locations = []
    for demo in audience:
        if demo.get("name") == "audience_gender_age":
            values = demo.get("values", [{}])[0].get("value", {})
            # Extract age ranges
            age_set = set()
            for key in values.keys():
                if '.' in key:
                    age = key.split('.')[1]
                    age_set.add(age)
            age_ranges = sorted(list(age_set))[:3]

        elif demo.get("name") == "audience_city":
            values = demo.get("values", [{}])[0].get("value", {})
            # Top 5 cities
            sorted_cities = sorted(values.items(), key=lambda x: x[1], reverse=True)
            locations = [city for city, _ in sorted_cities[:5]]

    return {
        "summary": f"Your Instagram account shows strong engagement with {len(media)} recent posts. Focus on {format_scores[0]['format'] if format_scores else 'IMAGE'} content for best results.",
        "ad_formats": format_scores[:3] if format_scores else [
            {"format": "REELS", "score": 85, "reasoning": "Reels typically perform best on Instagram"},
            {"format": "IMAGE", "score": 75, "reasoning": "Static images are easy to create and effective"},
            {"format": "CAROUSEL_ALBUM", "score": 70, "reasoning": "Carousels encourage engagement"}
        ],
        "targeting": {
            "age_ranges": age_ranges if age_ranges else ["25-34", "35-44"],
            "genders": ["ALL"],
            "locations": locations if locations else ["United States"],
            "interests": ["lifestyle", "wellness"],
            "lookalike": True,
            "reasoning": "Based on current audience demographics"
        },
        "budget_allocation": {
            "instagram": 70,
            "facebook": 20,
            "google": 10,
            "reasoning": "Instagram should be primary platform with Facebook for extended reach"
        },
        "posting_schedule": {
            "best_days": ["Tuesday", "Thursday", "Saturday"],
            "best_times": ["9:00 AM", "12:00 PM", "6:00 PM"],
            "frequency": "3-5 times per week",
            "reasoning": "Standard optimal posting times for Instagram"
        },
        "content_strategy": {
            "tone": "inspirational",
            "topics": ["lifestyle", "wellness", "motivation"],
            "hashtags": ["#instagood", "#photooftheday", "#motivation", "#wellness", "#lifestyle"],
            "call_to_action": "Click link in bio",
            "reasoning": "Engaging content with clear CTAs performs well"
        },
        "roi_projection": {
            "estimated_reach": 10000,
            "estimated_clicks": 200,
            "estimated_conversions": 10,
            "estimated_revenue": 1000,
            "confidence": "medium",
            "assumptions": "Based on industry averages for similar account size"
        },
        "generated_at": datetime.utcnow().isoformat()
    }


# Singleton instance
_analyzer = None


def get_insights_analyzer() -> InsightsAnalyzer:
    """Get singleton insights analyzer."""
    global _analyzer
    if _analyzer is None:
        _analyzer = InsightsAnalyzer()
    return _analyzer


def analyze_instagram_insights(
    insights_data: Dict[str, Any],
    campaign_goal: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Convenience function to analyze insights.

    Args:
        insights_data: Instagram insights data
        campaign_goal: Optional campaign goal

    Returns:
        AI recommendations
    """
    analyzer = get_insights_analyzer()
    return analyzer.analyze_insights(insights_data, campaign_goal)
