"""Tests for reading text from Claude responses."""

import json
from unittest.mock import MagicMock

import pytest
from anthropic.types import Message

from src import config
from src.anthropic_client import AnthropicClientBase
from src.digest_writer import DigestWriter
from src.relevance_scorer import RelevanceScorer, ScoredArticle
from src.rss_searcher import Article

THINKING = {"type": "thinking", "thinking": "", "signature": "sig"}


def make_message(content, stop_reason="end_turn", model="claude-sonnet-5"):
    return Message.model_validate(
        {
            "id": "msg_1",
            "type": "message",
            "role": "assistant",
            "model": model,
            "content": content,
            "stop_reason": stop_reason,
            "stop_sequence": None,
            "usage": {"input_tokens": 10, "output_tokens": 20},
        }
    )


def text(value):
    return {"type": "text", "text": value}


@pytest.fixture(autouse=True)
def no_shunt(monkeypatch):
    # Keep the client unwrapped (the shunt pipe is for local runs only)
    monkeypatch.setenv("CI", "true")


class TestResponseText:
    def test_skips_leading_thinking_block(self):
        message = make_message([THINKING, text("hello")])
        assert AnthropicClientBase.response_text(message) == "hello"

    def test_joins_text_blocks(self):
        message = make_message([text("a"), THINKING, text("b")])
        assert AnthropicClientBase.response_text(message) == "ab"

    def test_max_tokens_raises(self):
        message = make_message([THINKING, text('[{"index": 1')], stop_reason="max_tokens")
        with pytest.raises(RuntimeError, match="max_tokens"):
            AnthropicClientBase.response_text(message)

    def test_refusal_raises(self):
        message = make_message([], stop_reason="refusal")
        with pytest.raises(RuntimeError, match="declined"):
            AnthropicClientBase.response_text(message)


def make_articles(n):
    return [
        Article(title=f"T{i}", url=f"https://a.com/{i}", summary=None, published=None, source="S")
        for i in range(n)
    ]


class TestScorerWithThinking:
    def test_scores_parsed_after_thinking_block(self):
        scorer = RelevanceScorer("key")
        scorer.client = MagicMock()
        scores = [{"index": 1, "score": 0.9, "explanation": "x"}]
        scorer.client.messages.create.return_value = make_message(
            [THINKING, text(json.dumps(scores))]
        )

        scored = scorer.score_batch("profile", make_articles(1))

        assert [s.score for s in scored] == [0.9]
        kwargs = scorer.client.messages.create.call_args.kwargs
        assert kwargs["max_tokens"] == config.SCORING_MAX_TOKENS

    def test_truncated_batch_raises_instead_of_dropping(self):
        scorer = RelevanceScorer("key")
        scorer.client = MagicMock()
        scorer.client.messages.create.return_value = make_message(
            [THINKING, text('[{"index": 1, "sc')], stop_reason="max_tokens"
        )
        with pytest.raises(RuntimeError):
            scorer.score_batch("profile", make_articles(1))


class TestDigestWithThinking:
    def test_digest_text_after_thinking_block(self):
        writer = DigestWriter("key")
        writer.client = MagicMock()
        writer.client.messages.create.return_value = make_message(
            [THINKING, text("# Digest")], model="claude-opus-5-5"
        )
        article = make_articles(1)[0]
        digest = writer.generate_digest(
            "profile", [ScoredArticle(article=article, score=0.8, explanation="e")]
        )
        assert digest == "# Digest"
