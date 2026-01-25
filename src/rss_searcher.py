"""RSS feed fetching and parsing."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from time import mktime
from typing import Optional

import feedparser

from . import config


@dataclass(frozen=True)
class FeedResult:
    """Result of fetching a single feed."""

    name: str
    url: str
    articles: list["Article"]
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and len(self.articles) > 0


@dataclass(frozen=True)
class Article:
    """An article from an RSS feed."""

    title: str
    url: str
    summary: Optional[str]
    published: Optional[datetime]
    source: str


class RSSSearcher:
    """Fetches and parses RSS feeds."""

    def __init__(self, feeds: list[tuple[str, str, int]]):
        """
        Initialize the RSS searcher.

        Args:
            feeds: List of (name, url, max_articles) tuples.
        """
        self.feeds = feeds

    def _parse_datetime(self, entry) -> Optional[datetime]:
        """Parse the published date from a feed entry."""
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                return datetime.fromtimestamp(mktime(entry.published_parsed))
            except (TypeError, ValueError, OverflowError):
                pass
        if hasattr(entry, "updated_parsed") and entry.updated_parsed:
            try:
                return datetime.fromtimestamp(mktime(entry.updated_parsed))
            except (TypeError, ValueError, OverflowError):
                pass
        return None

    def _get_summary(self, entry) -> Optional[str]:
        """Extract summary from a feed entry."""
        if hasattr(entry, "summary") and entry.summary:
            return entry.summary[:500]  # Truncate long summaries
        if hasattr(entry, "description") and entry.description:
            return entry.description[:500]
        return None

    def fetch_feed(
        self,
        name: str,
        url: str,
        limit: int,
    ) -> list[Article]:
        """
        Fetch and parse a single RSS feed.

        Args:
            name: Display name for the feed source.
            url: URL of the RSS feed.
            limit: Maximum articles to fetch. Defaults to config.MAX_ARTICLES_PER_FEED.

        Returns:
            List of Article objects.
        """
        try:
            feed = feedparser.parse(url)
        except Exception:
            return []

        if feed.bozo and not feed.entries:
            # Feed had errors and no entries
            return []

        articles = []
        for entry in feed.entries[:limit]:
            # Get the link - try multiple common fields
            link = getattr(entry, "link", None)
            if not link:
                link = getattr(entry, "id", None)
            if not link:
                continue

            title = getattr(entry, "title", "Untitled")

            articles.append(
                Article(
                    title=title,
                    url=link,
                    summary=self._get_summary(entry),
                    published=self._parse_datetime(entry),
                    source=name,
                )
            )

        return articles

    def _fetch_feed_safe(
        self,
        name: str,
        url: str,
        limit: int,
    ) -> FeedResult:
        """Fetch a feed and return a FeedResult (never raises)."""
        try:
            articles = self.fetch_feed(name, url, limit)
            if articles:
                return FeedResult(name=name, url=url, articles=articles)
            return FeedResult(
                name=name, url=url, articles=[], error="No articles returned"
            )
        except Exception as e:
            return FeedResult(name=name, url=url, articles=[], error=str(e))

    def fetch_all_feeds_with_results(self) -> list[FeedResult]:
        """
        Fetch all feeds concurrently and return results for each.

        Returns:
            List of FeedResult objects in original feed order.
        """
        results: dict[str, FeedResult] = {}

        with ThreadPoolExecutor(max_workers=len(self.feeds)) as executor:
            futures = {
                executor.submit(
                    self._fetch_feed_safe,
                    name,
                    url,
                    limit,
                ): name
                for name, url, limit in self.feeds
            }
            for future in as_completed(futures):
                result = future.result()
                results[result.name] = result

        # Return in original feed order
        return [results[name] for name, _, _ in self.feeds]

    def fetch_all_feeds(self) -> list[Article]:
        """
        Fetch articles from all configured feeds concurrently.

        Returns:
            List of all Article objects, sorted by publish date (newest first).
        """
        feed_results = self.fetch_all_feeds_with_results()

        all_articles = []
        for result in feed_results:
            all_articles.extend(result.articles)

        # Sort by published date, newest first (None dates go to the end)
        all_articles.sort(
            key=lambda a: (a.published is None, a.published), reverse=True
        )

        return all_articles
