"""Generates digests combining user profile and relevant articles."""

from anthropic.types import TextBlock

from . import config
from .anthropic_client import AnthropicClientBase
from .relevance_scorer import ScoredArticle


class DigestWriter(AnthropicClientBase):
    """Uses Anthropic API to generate a digest from profile and articles."""

    def _build_digest_prompt(
        self,
        profile_summary: str,
        scored_articles: list[ScoredArticle],
    ) -> str:
        """Build the prompt for digest generation."""
        articles_text = []
        for scored in scored_articles:
            article = scored.article
            date_str = (
                article.published.strftime("%Y-%m-%d")
                if article.published
                else "Unknown"
            )
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
Create a concise, well-organized digest.

Do not include language or package version updates (e.g. Python, Rust) in the Executive Summary or Top Picks sections; only put them in the Updates & Releases section.

1. **Executive Summary** (2-6 sentences): What's most important for this developer now?

2. **Top Picks** (up to {config.DIGEST_TOP_PICKS} articles): The most relevant articles with a brief explanation (1-3 sentences) of why each matters to their current work. Order by relevance; do not categorize by topic. Use this format:

    Number. Title
    URL
    Relevance Score
    Explanation (1-2 sentences)

3. **Worth a Look** (remaining articles): Quick one-line mentions of other relevant articles, grouped by theme. Use this format:

    Theme
        * Title as link (relevance): mention

4. **Updates & Releases**: Updates to languages or packages the developer uses (based on their profile). Use this format:

    Language or Package
        * Title as link (relevance): mention

5. **Trends & Insights**: Patterns across the articles that relate to the developer's work (e.g., "Several articles about X which connects to your work on Y").

6. **Next Steps**: What should the developer prioritize, explore further, or create new?

Write in a professional, concise tone. Use markdown formatting. Focus on actionable insights."""

    def generate_digest(
        self,
        profile_summary: str,
        scored_articles: list[ScoredArticle],
    ) -> str:
        """
        Args:
            profile_summary: LLM-formatted summary of user's GitHub activity.
            scored_articles: List of scored articles, sorted by relevance.
        """
        if not scored_articles:
            return "# Your Digest\n\nNo relevant articles were found matching your recent activity."

        prompt = self._build_digest_prompt(profile_summary, scored_articles)

        response = self.client.messages.create(
            model=config.DIGEST_MODEL,
            max_tokens=config.DIGEST_MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )

        block = response.content[0]
        assert isinstance(block, TextBlock)
        return block.text
