"""Tests for retry-safe digest delivery."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import httpx
import pytest

import main
from src import delivery, github_profiler
from src.github_profiler import GitHubProfiler, Issue


def make_issue(number, body):
    return Issue(
        number=number,
        repo="user/repo",
        title="Digest",
        body=body,
        state="open",
        author="user",
        created_at=datetime(2026, 9, 23, tzinfo=timezone.utc),
        labels=[],
    )


class TestMarkers:
    def test_build_and_read(self):
        body = delivery.build_issue_body("- [A](https://a.com)", "123", delivery.PENDING)
        assert delivery.get_run_key(body) == "123"
        assert delivery.get_status(body) == delivery.PENDING
        assert main.extract_urls_from_text(body) == frozenset({"https://a.com"})

    def test_set_status(self):
        body = delivery.build_issue_body("x", "123", delivery.PENDING)
        body = delivery.set_status(body, delivery.SENT)
        assert delivery.get_status(body) == delivery.SENT
        assert body.count("<!-- email:") == 1

    def test_no_markers(self):
        body = delivery.build_issue_body("x", None, None)
        assert delivery.get_run_key(body) is None
        assert delivery.get_status(body) is None

    def test_legacy_issue_has_no_status(self):
        assert delivery.get_status("# Digest\n[a](https://a.com)") is None

    def test_run_status_prefers_sent(self):
        issues = [
            make_issue(3, delivery.build_issue_body("x", "9", delivery.FAILED)),
            make_issue(2, delivery.build_issue_body("x", "9", delivery.PENDING)),
            make_issue(1, delivery.build_issue_body("x", "9", delivery.SENT)),
            make_issue(0, delivery.build_issue_body("x", "8", delivery.SENT)),
        ]
        status, issue = delivery.run_status(issues, "9")
        assert (status, issue.number) == (delivery.SENT, 1)

    def test_run_status_none(self):
        issues = [make_issue(1, delivery.build_issue_body("x", "8", delivery.SENT))]
        assert delivery.run_status(issues, "9") == (None, None)


@pytest.fixture
def delivery_env(monkeypatch):
    monkeypatch.setattr(main.config, "DIGEST_ISSUE_REPO", "user/repo")
    monkeypatch.setattr(main.config, "DIGEST_RUN_KEY", "77")
    monkeypatch.setattr(main.config, "POSTMARK_SERVER_TOKEN", "tok")
    monkeypatch.setattr(main.config, "DIGEST_EMAIL_FROM", "from@example.com")
    monkeypatch.setattr(main.config, "DIGEST_EMAIL_TO", "to@example.com")
    profiler = MagicMock()
    profiler.__enter__.return_value = profiler
    profiler.create_issue.return_value = (5, "https://github.com/user/repo/issues/5")
    profiler.update_issue.return_value = (5, "https://github.com/user/repo/issues/5")
    monkeypatch.setattr(main, "GitHubProfiler", MagicMock(return_value=profiler))
    return profiler


NOW = datetime(2026, 9, 23, 7, 0)


def statuses(profiler):
    return [delivery.get_status(c.args[2]) for c in profiler.update_issue.call_args_list]


class TestDeliverDigest:
    def test_success_records_pending_then_sent(self, delivery_env, monkeypatch):
        order = []
        delivery_env.create_issue.side_effect = lambda *a: order.append("issue") or (5, "u")
        monkeypatch.setattr(main, "send_email", lambda *a: order.append("email"))

        main.deliver_digest("# Digest", [], NOW, None)

        assert order == ["issue", "email"]
        body = delivery_env.create_issue.call_args.args[2]
        assert delivery.get_status(body) == delivery.PENDING
        assert delivery.get_run_key(body) == "77"
        assert statuses(delivery_env) == [delivery.SENT]

    def test_postmark_rejection_marks_failed(self, delivery_env, monkeypatch):
        def reject(*a):
            raise HTTPError("url", 422, "Unprocessable", {}, None)

        monkeypatch.setattr(main, "send_email", reject)
        with pytest.raises(HTTPError):
            main.deliver_digest("# Digest", [], NOW, None)
        assert statuses(delivery_env) == [delivery.FAILED]

    def test_ambiguous_email_error_stays_pending(self, delivery_env, monkeypatch):
        def timeout(*a):
            raise URLError("timed out")

        monkeypatch.setattr(main, "send_email", timeout)
        with pytest.raises(URLError):
            main.deliver_digest("# Digest", [], NOW, None)
        assert statuses(delivery_env) == []

    def test_email_timeout_stays_pending(self, delivery_env, monkeypatch):
        # A timeout while reading the response raises TimeoutError, not URLError
        def stall(*a):
            raise TimeoutError("timed out")

        monkeypatch.setattr(main, "send_email", stall)
        with pytest.raises(TimeoutError):
            main.deliver_digest("# Digest", [], NOW, None)
        assert statuses(delivery_env) == []

    def test_reuses_failed_issue(self, delivery_env, monkeypatch):
        monkeypatch.setattr(main, "send_email", lambda *a: None)
        prior = make_issue(4, delivery.build_issue_body("x", "77", delivery.FAILED))

        main.deliver_digest("# Digest", [], NOW, prior)

        delivery_env.create_issue.assert_not_called()
        first = delivery_env.update_issue.call_args_list[0]
        assert first.args[1] == 4
        assert delivery.get_status(first.args[2]) == delivery.PENDING


class TestFindPriorAttempt:
    def run(self, profiler, body):
        profiler.get_latest_issues.return_value = [make_issue(4, body)]
        return main.find_prior_attempt()

    def test_sent_exits_cleanly(self, delivery_env):
        with pytest.raises(SystemExit) as e:
            self.run(delivery_env, delivery.build_issue_body("x", "77", delivery.SENT))
        assert e.value.code == 0

    def test_pending_exits_with_error(self, delivery_env):
        with pytest.raises(SystemExit) as e:
            self.run(delivery_env, delivery.build_issue_body("x", "77", delivery.PENDING))
        assert e.value.code == 1

    def test_failed_returns_issue(self, delivery_env):
        issue = self.run(delivery_env, delivery.build_issue_body("x", "77", delivery.FAILED))
        assert issue.number == 4

    def test_other_run_ignored(self, delivery_env):
        assert self.run(delivery_env, delivery.build_issue_body("x", "76", delivery.SENT)) is None

    def test_lookup_is_strict(self, delivery_env):
        delivery_env.get_latest_issues.return_value = []
        main.find_prior_attempt()
        assert delivery_env.get_latest_issues.call_args.kwargs["raise_errors"] is True


def status_error(code):
    request = httpx.Request("POST", "https://api.github.com/x")
    return httpx.HTTPStatusError("err", request=request, response=httpx.Response(code, request=request))


class TestWriteRetries:
    @patch("src.github_profiler.time.sleep")
    @patch("src.github_profiler.httpx.Client")
    def test_retries_transient_then_succeeds(self, mock_client_class, _sleep):
        ok = MagicMock()
        ok.json.return_value = {"number": 1, "html_url": "u"}
        bad = MagicMock()
        bad.raise_for_status.side_effect = status_error(502)
        mock_client = MagicMock()
        mock_client.post.side_effect = [httpx.ConnectError("reset"), bad, ok]
        mock_client_class.return_value = mock_client

        with GitHubProfiler(token="t") as profiler:
            assert profiler.create_issue("user/repo", "t", "b") == (1, "u")
        assert mock_client.post.call_count == 3

    @patch("src.github_profiler.time.sleep")
    @patch("src.github_profiler.httpx.Client")
    def test_does_not_retry_client_errors(self, mock_client_class, _sleep):
        bad = MagicMock()
        bad.raise_for_status.side_effect = status_error(422)
        mock_client = MagicMock()
        mock_client.patch.return_value = bad
        mock_client_class.return_value = mock_client

        with GitHubProfiler(token="t") as profiler:
            with pytest.raises(httpx.HTTPStatusError):
                profiler.update_issue("user/repo", 1, "b")
        assert mock_client.patch.call_count == 1

    @patch("src.github_profiler.time.sleep")
    @patch("src.github_profiler.httpx.Client")
    def test_gives_up_after_attempts(self, mock_client_class, _sleep):
        mock_client = MagicMock()
        mock_client.post.side_effect = httpx.ConnectError("down")
        mock_client_class.return_value = mock_client

        with GitHubProfiler(token="t") as profiler:
            with pytest.raises(httpx.ConnectError):
                profiler.create_issue("user/repo", "t", "b")
        assert mock_client.post.call_count == github_profiler.WRITE_ATTEMPTS
