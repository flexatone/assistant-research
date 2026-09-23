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

    def fake_urlopen(req, timeout=None):
        captured["req"] = req
        captured["timeout"] = timeout
        return _FakeResponse()

    monkeypatch.setattr(email_sender, "urlopen", fake_urlopen)

    email_sender.send_email(
        "tok", "from@example.com", "to@example.com", "Subj", "<p>hi</p>", "hi"
    )

    assert captured["timeout"] == email_sender.POSTMARK_TIMEOUT
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


class TestRenderDigestHtmlSanitizes:
    def render(self, text):
        return email_sender.render_digest_html(text)

    def test_raw_html_script_removed(self):
        html = self.render("hi <script>alert(1)</script> there")
        assert "<script" not in html
        assert "alert(1)" not in html

    def test_raw_img_removed(self):
        html = self.render('<img src="https://tracker.example/p.gif">text')
        assert "<img" not in html
        assert "tracker.example" not in html

    def test_markdown_image_removed(self):
        html = self.render("![x](https://tracker.example/p.gif)")
        assert "<img" not in html
        assert "tracker.example" not in html

    def test_event_handler_and_style_removed(self):
        html = self.render(
            '<p onclick="steal()" style="background:url(https://t.example/x)">hi</p>'
        )
        assert "onclick" not in html
        assert "style" not in html
        assert "t.example" not in html

    def test_unsafe_link_schemes_removed(self):
        html = self.render(
            "[a](javascript:alert(1)) [b](data:text/html,x) "
            '<a href="vbscript:x">c</a> [d](/relative)'
        )
        assert "javascript:" not in html
        assert "data:" not in html
        assert "vbscript:" not in html
        assert 'href="/relative"' not in html

    def test_iframe_and_form_removed(self):
        html = self.render(
            '<iframe src="https://evil.example"></iframe>'
            '<form action="https://evil.example"><input name="p"></form>'
        )
        assert "evil.example" not in html
        assert "<iframe" not in html
        assert "<form" not in html
        assert "<input" not in html

    def test_safe_links_kept(self):
        html = self.render(
            "[w](https://en.wikipedia.org/wiki/Foo_(bar)) [m](mailto:a@example.com)"
        )
        assert 'href="https://en.wikipedia.org/wiki/Foo_(bar)"' in html
        assert 'href="mailto:a@example.com"' in html
        assert 'rel="noopener noreferrer"' in html

    def test_digest_structure_kept(self):
        html = self.render(
            "## Top Picks\n\n1. **Bold** and *em*\n2. `code`\n\n"
            "| a | b |\n|---|---|\n| 1 | 2 |\n\n> quote\n\n---\n"
        )
        for tag in ("<h2>", "<ol>", "<li>", "<strong>", "<em>", "<code>",
                    "<table>", "<td>", "<blockquote>", "<hr>"):
            assert tag in html


def test_render_digest_html():
    html = email_sender.render_digest_html(
        "## Top Picks\n\n1. [Title](https://example.com/a)\n"
    )
    assert "<h2>Top Picks</h2>" in html
    assert 'href="https://example.com/a"' in html
    assert ">Title</a>" in html


def test_format_article_list_round_trips_urls():
    urls = [
        "https://example.com/a",
        "https://example.org/b?x=1",
        "https://en.wikipedia.org/wiki/Rust_(programming_language)",
        "https://example.com/a_(b)_(c)",
        "https://example.com/unbalanced)",
        "https://example.com/open(",
    ]
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


class TestExtractUrls:
    def test_markdown_link(self):
        assert extract_urls_from_text("[t](https://a.com/x)") == {"https://a.com/x"}

    def test_markdown_link_with_parentheses(self):
        text = "[Rust](https://en.wikipedia.org/wiki/Rust_(programming_language))"
        assert extract_urls_from_text(text) == {
            "https://en.wikipedia.org/wiki/Rust_(programming_language)"
        }

    def test_text_directly_after_link(self):
        assert extract_urls_from_text("[t](https://a.com/x): note") == {"https://a.com/x"}
        assert extract_urls_from_text("[t](https://a.com/(y)):") == {"https://a.com/(y)"}

    def test_parenthesized_bare_url(self):
        text = "(see https://en.wikipedia.org/wiki/Foo_(bar))"
        assert extract_urls_from_text(text) == {"https://en.wikipedia.org/wiki/Foo_(bar)"}

    def test_angle_bracket_url_is_verbatim(self):
        text = "[t](<https://a.com/x)y>) and [u](<https://b.com/(z>)"
        assert extract_urls_from_text(text) == {"https://a.com/x)y", "https://b.com/(z"}

    def test_plain_urls(self):
        text = "https://a.com/x and https://b.com/y\n[t](https://c.com)"
        assert extract_urls_from_text(text) == {
            "https://a.com/x",
            "https://b.com/y",
            "https://c.com",
        }

    def test_empty(self):
        assert extract_urls_from_text("") == frozenset()
