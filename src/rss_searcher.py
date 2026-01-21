"""RSS feed fetching and parsing."""

from dataclasses import dataclass
from datetime import datetime
from time import mktime
from typing import Optional

import feedparser

from . import config


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

    def __init__(self, feeds: Optional[list[tuple[str, str]]] = None):
        """
        Initialize the RSS searcher.

        Args:
            feeds: List of (name, url) tuples. Defaults to config feeds.
        """
        self.feeds = feeds or (config.DEFAULT_FEEDS + config.CUSTOM_FEEDS)

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

    def fetch_feed(self, name: str, url: str, limit: Optional[int] = None) -> list[Article]:
        """
        Fetch and parse a single RSS feed.

        Args:
            name: Display name for the feed source.
            url: URL of the RSS feed.
            limit: Maximum articles to fetch. Defaults to config.MAX_ARTICLES_PER_FEED.

        Returns:
            List of Article objects.
        """
        limit = limit or config.MAX_ARTICLES_PER_FEED

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

            articles.append(Article(
                title=title,
                url=link,
                summary=self._get_summary(entry),
                published=self._parse_datetime(entry),
                source=name,
            ))

        return articles

    def fetch_all_feeds(self, limit_per_feed: Optional[int] = None) -> list[Article]:
        """
        Fetch articles from all configured feeds.

        Args:
            limit_per_feed: Maximum articles per feed. Defaults to config.MAX_ARTICLES_PER_FEED.

        Returns:
            List of all Article objects, sorted by publish date (newest first).
        """
        all_articles = []

        for name, url in self.feeds:
            articles = self.fetch_feed(name, url, limit_per_feed)
            all_articles.extend(articles)

        # Sort by published date, newest first (None dates go to the end)
        all_articles.sort(
            key=lambda a: (a.published is None, a.published),
            reverse=True
        )

        return all_articles
