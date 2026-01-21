"""Generates digests combining user profile and relevant articles."""

from typing import Optional

import anthropic

from . import config
from .relevance_scorer import ScoredArticle


class DigestWriter:
    """Uses Anthropic API to generate a digest from profile and articles."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the digest writer.

        Args:
            api_key: Anthropic API key. Defaults to config.ANTHROPIC_API_KEY.
        """
        self.api_key = api_key or config.ANTHROPIC_API_KEY
        if not self.api_key:
            raise ValueError("Anthropic API key is required. Set ANTHROPIC_API_KEY environment variable.")

        self.client = anthropic.Anthropic(api_key=self.api_key)

    def _build_digest_prompt(
        self,
        profile_summary: str,
        scored_articles: list[ScoredArticle],
    ) -> str:
        """Build the prompt for digest generation."""
        articles_text = []
        for scored in scored_articles:
            article = scored.article
            date_str = article.published.strftime("%Y-%m-%d") if article.published else "Unknown"
            summary_part = f"\n   Summary: {article.summary}" if article.summary else ""
            articles_text.append(
                f"- **{article.title}** ({article.source}, {date_str})\n"
                f"  URL: {article.url}\n"
                f"  Relevance: {scored.score:.2f} - {scored.explanation}{summary_part}"
            )

        return f"""You are a research assistant creating a personalized digest for a software developer.

## Developer's Recent Activity Profile
{profile_summary}

## Relevant Articles Found
{chr(10).join(articles_text)}

## Task
Create a concise, well-organized digest that:

1. **Executive Summary** (2-3 sentences): What's most important for this developer this week?

2. **Top Picks** (3-5 articles): The most relevant articles with a brief explanation of why each matters to their current work. Include the article URL.

3. **Worth a Look** (remaining articles): Quick one-line mentions of other relevant articles, grouped by theme if possible. Include URLs.

4. **Trends & Insights**: Any patterns you notice across the articles that relate to the developer's work (e.g., "Several articles about X which connects to your work on Y").

Write in a friendly, concise tone. Use markdown formatting. Focus on actionable insights - what should they read and why it matters to their specific work."""

    def generate_digest(
        self,
        profile_summary: str,
        scored_articles: list[ScoredArticle],
    ) -> str:
        """
        Generate a digest combining the profile and relevant articles.

        Args:
            profile_summary: LLM-formatted summary of user's GitHub activity.
            scored_articles: List of scored articles, sorted by relevance.

        Returns:
            Formatted digest as a markdown string.
        """
        if not scored_articles:
            return "# Your Weekly Digest\n\nNo relevant articles were found matching your recent activity."

        prompt = self._build_digest_prompt(profile_summary, scored_articles)

        response = self.client.messages.create(
            model=config.DIGEST_MODEL,
            max_tokens=config.DIGEST_MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text
