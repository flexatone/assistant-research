"""Tests for email sending and article list formatting."""

import json
from datetime import datetime

from main import extract_urls_from_text
from src import email_sender
from src.digest_writer import format_article_list
from src.relevance_scorer import ScoredArticle
from src.rss_searcher import Article


class _FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return b"{}"


def test_send_email_posts_to_postmark(monkeypatch):
    captured = {}

    def fake_urlopen(req):
        captured["req"] = req
        return _FakeResponse()

    monkeypatch.setattr(email_sender, "urlopen", fake_urlopen)

    email_sender.send_email(
        "tok", "from@example.com", "to@example.com", "Subj", "<p>hi</p>", "hi"
    )

    req = captured["req"]
    assert req.full_url == "https://api.postmarkapp.com/email"
    assert req.get_method() == "POST"
    assert req.get_header("X-postmark-server-token") == "tok"
    payload = json.loads(req.data)
    assert payload == {
        "From": "from@example.com",
        "To": "to@example.com",
        "Subject": "Subj",
        "HtmlBody": "<p>hi</p>",
        "TextBody": "hi",
        "MessageStream": "outbound",
    }


def test_render_digest_html():
    html = email_sender.render_digest_html(
        "## Top Picks\n\n1. [Title](https://example.com/a)\n"
    )
    assert "<h2>Top Picks</h2>" in html
    assert '<a href="https://example.com/a">Title</a>' in html


def test_format_article_list_round_trips_urls():
    urls = ["https://example.com/a", "https://example.org/b?x=1"]
    scored = [
        ScoredArticle(
            article=Article(
                title=f"Title {i}",
                url=url,
                summary="secret commentary",
                published=datetime(2026, 9, 23) if i == 0 else None,
                source="Src",
            ),
            score=0.8,
            explanation="why it matters",
        )
        for i, url in enumerate(urls)
    ]
    body = format_article_list(scored)
    assert extract_urls_from_text(body) == frozenset(urls)
    assert "2026-09-23" in body
    assert "Unknown" in body
    assert "why it matters" not in body
    assert "secret commentary" not in body
