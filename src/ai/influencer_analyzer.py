"""
Influencer Analysis and Benchmarking System
Analyzes successful influencers to identify winning strategies
"""
import logging
from typing import List, Dict, Any, Optional
import anthropic
import os
from datetime import datetime

logger = logging.getLogger(__name__)


class InfluencerAnalyzer:
    """
    Analyze top influencers in a niche to identify success patterns.
    Provides actionable recommendations for content strategy.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize influencer analyzer.

        Args:
            api_key: Anthropic API key
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = "claude-3-5-sonnet-20241022"

    def analyze_influencer_profile(
        self,
        influencer_data: Dict[str, Any],
        user_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Deep analysis of an influencer's strategy and content.

        Args:
            influencer_data: Influencer profile with posts, metrics, etc.
            user_data: Your account data for comparison

        Returns:
            {
                "content_strategy": {...},
                "engagement_tactics": [...],
                "posting_patterns": {...},
                "unique_elements": [...],
                "recommendations": [...],
                "gap_analysis": {...} (if user_data provided)
            }
        """
        username = influencer_data.get("username", "Unknown")
        followers = influencer_data.get("followers", 0)
        posts = influencer_data.get("top_posts", [])

        prompt = f"""Analyze this successful Instagram influencer and identify their winning strategies:

**Influencer:** @{username}
**Followers:** {followers:,}
**Niche:** {influencer_data.get('niche', 'Not specified')}

**Top Performing Posts:**
{self._format_posts(posts[:10])}

**Bio/Description:** {influencer_data.get('bio', 'N/A')}

Provide a comprehensive analysis:

1. **Content Strategy:**
   - Core content themes
   - Content mix (educational, entertaining, promotional)
   - Visual style and branding
   - Unique value proposition

2. **Engagement Tactics:**
   - Caption styles that drive engagement
   - Call-to-action patterns
   - Community interaction methods
   - Hashtag strategy

3. **Posting Patterns:**
   - Optimal posting frequency
   - Content format distribution (reels, carousels, images)
   - Best performing content types

4. **Unique Elements:**
   - What makes them stand out
   - Signature styles or formats
   - Hook strategies
   - Storytelling techniques

5. **Success Factors:**
   - Key elements driving their growth
   - Audience relationship building
   - Brand positioning

6. **Actionable Recommendations:**
   - Specific tactics you can adapt
   - Content ideas inspired by their strategy
   - Engagement techniques to implement
   - What to avoid or differentiate from

{self._add_comparison_context(user_data) if user_data else ""}

Format as JSON with these keys: content_strategy, engagement_tactics, posting_patterns, unique_elements, success_factors, recommendations
{', gap_analysis' if user_data else ''}"""

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=6000,
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

            analysis = json.loads(response_text)

            logger.info(f"Analyzed influencer @{username}")
            return {
                "influencer": username,
                "followers": followers,
                "analysis": analysis,
                "analyzed_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to analyze influencer: {e}")
            return {"error": str(e)}

    def compare_multiple_influencers(
        self,
        influencers: List[Dict[str, Any]],
        niche: str
    ) -> Dict[str, Any]:
        """
        Compare multiple top influencers to identify common patterns.

        Args:
            influencers: List of influencer data dicts
            niche: Industry/niche for context

        Returns:
            {
                "common_strategies": [...],
                "differentiating_factors": [...],
                "niche_best_practices": [...],
                "content_trends": [...],
                "recommendations": [...]
            }
        """
        influencer_summaries = []
        for inf in influencers[:5]:  # Limit to top 5
            influencer_summaries.append({
                "username": inf.get("username"),
                "followers": inf.get("followers"),
                "avg_engagement": inf.get("avg_engagement_rate", 0),
                "top_content_types": inf.get("top_content_types", []),
                "posting_frequency": inf.get("posting_frequency", "Unknown")
            })

        prompt = f"""Analyze these top {niche} influencers to identify winning patterns:

{self._format_influencer_comparison(influencer_summaries)}

**Niche:** {niche}

Identify:

1. **Common Strategies:** What do all successful accounts do?
2. **Differentiating Factors:** How do they stand out from each other?
3. **Niche Best Practices:** Specific tactics that work in {niche}
4. **Content Trends:** Emerging formats and themes
5. **Engagement Patterns:** What drives interactions in this niche
6. **Monetization Strategies:** How are they making money
7. **Audience Building:** Growth tactics that work

Provide:
- Specific examples from the data
- Actionable recommendations
- What to replicate vs. how to differentiate
- Quick wins vs. long-term strategies

Format as JSON."""

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=5000,
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

            analysis = json.loads(response_text)

            logger.info(f"Compared {len(influencers)} influencers in {niche}")
            return {
                "niche": niche,
                "influencers_analyzed": len(influencers),
                "analysis": analysis,
                "analyzed_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to compare influencers: {e}")
            return {"error": str(e)}

    def generate_competitor_report(
        self,
        your_account: Dict[str, Any],
        competitors: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate competitive analysis report.

        Args:
            your_account: Your account data
            competitors: List of competitor accounts

        Returns:
            Comprehensive competitive analysis with recommendations
        """
        prompt = f"""Create a competitive analysis report:

**Your Account:**
- Username: @{your_account.get('username')}
- Followers: {your_account.get('followers', 0):,}
- Avg Engagement: {your_account.get('avg_engagement_rate', 0):.2f}%
- Top Content: {your_account.get('top_content_type', 'Mixed')}

**Competitors:**
{self._format_competitor_list(competitors[:5])}

Provide:

1. **Competitive Positioning:**
   - Where you stand vs competitors
   - Your strengths and weaknesses
   - Market gaps and opportunities

2. **Content Gap Analysis:**
   - What competitors are doing that you're not
   - Untapped content opportunities
   - Audience needs not being met

3. **Strategic Recommendations:**
   - How to differentiate
   - Content to create
   - Engagement tactics to adopt
   - Growth opportunities

4. **Quick Wins:**
   - Immediate actions (next 30 days)
   - Low-hanging fruit
   - Easy optimizations

5. **Long-term Strategy:**
   - 90-day content plan
   - Brand positioning
   - Audience growth tactics

Format as JSON."""

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=6000,
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

            report = json.loads(response_text)

            logger.info("Generated competitive analysis report")
            return {
                "your_username": your_account.get('username'),
                "competitors_analyzed": len(competitors),
                "report": report,
                "generated_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to generate report: {e}")
            return {"error": str(e)}

    # Helper methods
    def _format_posts(self, posts: List[Dict]) -> str:
        """Format posts for analysis."""
        formatted = []
        for i, post in enumerate(posts, 1):
            formatted.append(
                f"{i}. Type: {post.get('media_type', 'Unknown')}, "
                f"Engagement: {post.get('engagement_rate', 0):.2f}%, "
                f"Likes: {post.get('likes', 0):,}, "
                f"Caption: {post.get('caption', '')[:100]}..."
            )
        return "\n".join(formatted)

    def _format_influencer_comparison(self, influencers: List[Dict]) -> str:
        """Format influencer list for comparison."""
        formatted = []
        for inf in influencers:
            formatted.append(
                f"- @{inf['username']}: {inf['followers']:,} followers, "
                f"{inf['avg_engagement']:.2f}% engagement, "
                f"Top formats: {', '.join(inf.get('top_content_types', ['Mixed']))}"
            )
        return "\n".join(formatted)

    def _format_competitor_list(self, competitors: List[Dict]) -> str:
        """Format competitor list."""
        formatted = []
        for comp in competitors:
            formatted.append(
                f"- @{comp.get('username')}: {comp.get('followers', 0):,} followers, "
                f"{comp.get('avg_engagement_rate', 0):.2f}% engagement"
            )
        return "\n".join(formatted)

    def _add_comparison_context(self, user_data: Dict) -> str:
        """Add user comparison context to prompt."""
        return f"""
**Your Account (for comparison):**
- Username: @{user_data.get('username')}
- Followers: {user_data.get('followers', 0):,}
- Avg Engagement: {user_data.get('avg_engagement_rate', 0):.2f}%

Provide a **Gap Analysis** comparing your account to this influencer:
- What they're doing that you're not
- Opportunities to improve
- Tactics you can adapt immediately
"""
