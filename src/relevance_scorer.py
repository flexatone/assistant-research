"""LLM-based relevance scoring for articles."""

import json
from dataclasses import dataclass
from typing import Optional

import anthropic

from . import config
from .rss_searcher import Article


@dataclass
class ScoredArticle:
    """An article with its relevance score and explanation."""
    article: Article
    score: float  # 0-1
    explanation: str


class RelevanceScorer:
    """Uses Anthropic API to score article relevance to a user profile."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the relevance scorer.

        Args:
            api_key: Anthropic API key. Defaults to config.ANTHROPIC_API_KEY.
        """
        self.api_key = api_key or config.ANTHROPIC_API_KEY
        if not self.api_key:
            raise ValueError("Anthropic API key is required. Set ANTHROPIC_API_KEY environment variable.")

        self.client = anthropic.Anthropic(api_key=self.api_key)

    def _build_scoring_prompt(self, profile_summary: str, articles: list[Article]) -> str:
        """Build the prompt for scoring articles."""
        articles_text = []
        for i, article in enumerate(articles):
            summary_part = f"\n   Summary: {article.summary}" if article.summary else ""
            articles_text.append(
                f"{i + 1}. [{article.source}] {article.title}{summary_part}"
            )

        return f"""You are evaluating articles for relevance to a software developer's interests based on their recent GitHub activity.

## Developer Profile
{profile_summary}

## Articles to Score
{chr(10).join(articles_text)}

## Task
Score each article from 0.0 to 1.0 based on how relevant it is to this developer's interests:
- 0.0-0.3: Not relevant (different domain, technology, or focus area)
- 0.4-0.5: Marginally relevant (tangentially related topics)
- 0.6-0.7: Relevant (related to their technologies or interests)
- 0.8-1.0: Highly relevant (directly related to their active work)

Respond with a JSON array of objects, one per article, in order:
[
  {{"index": 1, "score": 0.8, "explanation": "Brief reason for score"}},
  ...
]

Only output the JSON array, no other text."""

    def _parse_scores(self, response_text: str, articles: list[Article]) -> list[ScoredArticle]:
        """Parse the LLM response into scored articles."""
        # Extract JSON from the response
        text = response_text.strip()

        # Try to find JSON array in the response
        start = text.find("[")
        end = text.rfind("]") + 1
        if start == -1 or end == 0:
            # No JSON array found, return empty scores
            return []

        try:
            scores_data = json.loads(text[start:end])
        except json.JSONDecodeError:
            return []

        scored = []
        for item in scores_data:
            idx = item.get("index", 0) - 1  # Convert to 0-indexed
            if 0 <= idx < len(articles):
                scored.append(ScoredArticle(
                    article=articles[idx],
                    score=float(item.get("score", 0)),
                    explanation=item.get("explanation", ""),
                ))

        return scored

    def score_batch(self, profile_summary: str, articles: list[Article]) -> list[ScoredArticle]:
        """
        Score a batch of articles for relevance.

        Args:
            profile_summary: LLM-formatted summary of user's GitHub activity.
            articles: List of articles to score.

        Returns:
            List of ScoredArticle objects with scores and explanations.
        """
        if not articles:
            return []

        prompt = self._build_scoring_prompt(profile_summary, articles)

        response = self.client.messages.create(
            model=config.SCORING_MODEL,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = response.content[0].text
        return self._parse_scores(response_text, articles)

    def score_articles(
        self,
        profile_summary: str,
        articles: list[Article],
        threshold: Optional[float] = None,
    ) -> list[ScoredArticle]:
        """
        Score all articles and filter by relevance threshold.

        Args:
            profile_summary: LLM-formatted summary of user's GitHub activity.
            articles: List of articles to score.
            threshold: Minimum score to include. Defaults to config.RELEVANCE_THRESHOLD.

        Returns:
            List of ScoredArticle objects above the threshold, sorted by score descending.
        """
        threshold = threshold if threshold is not None else config.RELEVANCE_THRESHOLD
        batch_size = config.SCORING_BATCH_SIZE

        all_scored = []

        # Process in batches
        for i in range(0, len(articles), batch_size):
            batch = articles[i:i + batch_size]
            scored = self.score_batch(profile_summary, batch)
            all_scored.extend(scored)

        # Filter by threshold and sort by score
        filtered = [s for s in all_scored if s.score >= threshold]
        filtered.sort(key=lambda s: s.score, reverse=True)

        return filtered
