"""Tests for RSSSearcher."""

from datetime import datetime
from time import mktime
from unittest.mock import patch, MagicMock

import pytest

from src.rss_searcher import RSSSearcher, Article, FeedResult


def make_entry(title: str, link: str, summary: str = None, published: datetime = None):
    """Create a mock feed entry."""
    entry = MagicMock()
    entry.title = title
    entry.link = link
    entry.summary = summary
    entry.description = None
    # feedparser returns time.struct_time, not a timestamp
    entry.published_parsed = published.timetuple() if published else None
    entry.updated_parsed = None
    return entry


def make_feed(entries: list, bozo: bool = False):
    """Create a mock feed response."""
    feed = MagicMock()
    feed.entries = entries
    feed.bozo = bozo
    return feed


class TestFetchFeed:
    """Tests for fetch_feed method."""

    @patch("src.rss_searcher.feedparser.parse")
    def test_fetch_feed_success(self, mock_parse):
        mock_parse.return_value = make_feed([
            make_entry("Article 1", "https://example.com/1", "Summary 1", datetime(2024, 1, 15)),
            make_entry("Article 2", "https://example.com/2", "Summary 2", datetime(2024, 1, 14)),
        ])

        searcher = RSSSearcher(feeds=[])
        articles = searcher.fetch_feed("Test Feed", "https://test.com/feed")

        assert len(articles) == 2
        assert articles[0].title == "Article 1"
        assert articles[0].url == "https://example.com/1"
        assert articles[0].summary == "Summary 1"
        assert articles[0].source == "Test Feed"

    @patch("src.rss_searcher.feedparser.parse")
    def test_fetch_feed_empty(self, mock_parse):
        mock_parse.return_value = make_feed([])

        searcher = RSSSearcher(feeds=[])
        articles = searcher.fetch_feed("Empty Feed", "https://test.com/feed")

        assert len(articles) == 0

    @patch("src.rss_searcher.feedparser.parse")
    def test_fetch_feed_limit(self, mock_parse):
        mock_parse.return_value = make_feed([
            make_entry(f"Article {i}", f"https://example.com/{i}")
            for i in range(10)
        ])

        searcher = RSSSearcher(feeds=[])
        articles = searcher.fetch_feed("Test Feed", "https://test.com/feed", limit=3)

        assert len(articles) == 3

    @patch("src.rss_searcher.feedparser.parse")
    def test_fetch_feed_bozo_with_entries(self, mock_parse):
        """Bozo feeds with entries should still return articles."""
        mock_parse.return_value = make_feed(
            [make_entry("Article 1", "https://example.com/1")],
            bozo=True
        )

        searcher = RSSSearcher(feeds=[])
        articles = searcher.fetch_feed("Bozo Feed", "https://test.com/feed")

        assert len(articles) == 1

    @patch("src.rss_searcher.feedparser.parse")
    def test_fetch_feed_bozo_no_entries(self, mock_parse):
        """Bozo feeds without entries should return empty."""
        mock_parse.return_value = make_feed([], bozo=True)

        searcher = RSSSearcher(feeds=[])
        articles = searcher.fetch_feed("Bozo Feed", "https://test.com/feed")

        assert len(articles) == 0

    @patch("src.rss_searcher.feedparser.parse")
    def test_fetch_feed_skips_entries_without_link(self, mock_parse):
        entry_no_link = MagicMock()
        entry_no_link.title = "No Link"
        entry_no_link.link = None
        entry_no_link.id = None

        mock_parse.return_value = make_feed([
            entry_no_link,
            make_entry("Has Link", "https://example.com/1"),
        ])

        searcher = RSSSearcher(feeds=[])
        articles = searcher.fetch_feed("Test Feed", "https://test.com/feed")

        assert len(articles) == 1
        assert articles[0].title == "Has Link"


class TestFetchAllFeeds:
    """Tests for fetch_all_feeds method."""

    @patch("src.rss_searcher.feedparser.parse")
    def test_fetch_all_feeds(self, mock_parse):
        mock_parse.return_value = make_feed([
            make_entry("Article 1", "https://example.com/1", published=datetime(2024, 1, 15)),
        ])

        searcher = RSSSearcher(feeds=[
            ("Feed A", "https://a.com/feed"),
            ("Feed B", "https://b.com/feed"),
        ])
        articles = searcher.fetch_all_feeds()

        assert len(articles) == 2
        assert mock_parse.call_count == 2

    @patch("src.rss_searcher.feedparser.parse")
    def test_fetch_all_feeds_sorted_by_date(self, mock_parse):
        def side_effect(url):
            if "a.com" in url:
                return make_feed([make_entry("Old", "https://a.com/1", published=datetime(2024, 1, 1))])
            else:
                return make_feed([make_entry("New", "https://b.com/1", published=datetime(2024, 1, 15))])

        mock_parse.side_effect = side_effect

        searcher = RSSSearcher(feeds=[
            ("Feed A", "https://a.com/feed"),
            ("Feed B", "https://b.com/feed"),
        ])
        articles = searcher.fetch_all_feeds()

        assert articles[0].title == "New"
        assert articles[1].title == "Old"


class TestFetchAllFeedsWithResults:
    """Tests for fetch_all_feeds_with_results method."""

    @patch("src.rss_searcher.feedparser.parse")
    def test_returns_feed_results(self, mock_parse):
        mock_parse.return_value = make_feed([
            make_entry("Article 1", "https://example.com/1"),
        ])

        searcher = RSSSearcher(feeds=[
            ("Feed A", "https://a.com/feed"),
        ])
        results = searcher.fetch_all_feeds_with_results()

        assert len(results) == 1
        assert isinstance(results[0], FeedResult)
        assert results[0].name == "Feed A"
        assert results[0].ok is True
        assert len(results[0].articles) == 1

    @patch("src.rss_searcher.feedparser.parse")
    def test_handles_empty_feed(self, mock_parse):
        mock_parse.return_value = make_feed([])

        searcher = RSSSearcher(feeds=[("Empty", "https://empty.com/feed")])
        results = searcher.fetch_all_feeds_with_results()

        assert results[0].ok is False
        assert results[0].error == "No articles returned"

    def test_handles_fetch_feed_exception(self):
        """Exception in fetch_feed is caught and reported."""
        searcher = RSSSearcher(feeds=[("Bad", "https://bad.com/feed")])

        # Patch fetch_feed to raise an exception
        with patch.object(searcher, "fetch_feed", side_effect=Exception("Network error")):
            results = searcher.fetch_all_feeds_with_results()

        assert results[0].ok is False
        assert "Network error" in results[0].error

    @patch("src.rss_searcher.feedparser.parse")
    def test_maintains_feed_order(self, mock_parse):
        mock_parse.return_value = make_feed([make_entry("Art", "https://x.com/1")])

        searcher = RSSSearcher(feeds=[
            ("Feed C", "https://c.com/feed"),
            ("Feed A", "https://a.com/feed"),
            ("Feed B", "https://b.com/feed"),
        ])
        results = searcher.fetch_all_feeds_with_results()

        assert [r.name for r in results] == ["Feed C", "Feed A", "Feed B"]
