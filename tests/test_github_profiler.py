'''Tests for GitHubProfiler.'''

from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from src.github_profiler import GitHubProfiler, Repo, Commit, PullRequest, Issue


def mock_response(json_data, status_code=200):
    '''Create a mock httpx response.'''
    response = MagicMock()
    response.json.return_value = json_data
    response.status_code = status_code
    response.raise_for_status = MagicMock()
    return response


class TestGetAuthenticatedUser:
    '''Tests for get_authenticated_user method.'''

    @patch("src.github_profiler.httpx.Client")
    def test_returns_username(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.get.return_value = mock_response({"login": "testuser"})

        with GitHubProfiler(token="fake-token") as profiler:
            username = profiler.get_authenticated_user()

        assert username == "testuser"


class TestGetUserRepos:
    '''Tests for get_user_repos method.'''

    @patch("src.github_profiler.httpx.Client")
    def test_returns_repos(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.get.return_value = mock_response(
            [
                {
                    "full_name": "user/repo1",
                    "description": "Test repo",
                    "language": "Python",
                    "topics": ["cli", "tool"],
                    "pushed_at": "2024-01-15T10:00:00Z",
                },
                {
                    "full_name": "user/repo2",
                    "description": None,
                    "language": "Rust",
                    "topics": [],
                    "pushed_at": "2024-01-14T10:00:00Z",
                },
            ]
        )

        with GitHubProfiler(token="fake-token") as profiler:
            repos = profiler.get_user_repos(limit=10)

        assert len(repos) == 2
        assert repos[0].full_name == "user/repo1"
        assert repos[0].language == "Python"
        assert repos[0].topics == ["cli", "tool"]
        assert repos[1].full_name == "user/repo2"

    @patch("src.github_profiler.httpx.Client")
    def test_respects_limit(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.get.return_value = mock_response(
            [
                {
                    "full_name": f"user/repo{i}",
                    "description": None,
                    "language": None,
                    "topics": [],
                    "pushed_at": None,
                }
                for i in range(10)
            ]
        )

        with GitHubProfiler(token="fake-token") as profiler:
            repos = profiler.get_user_repos(limit=3)

        assert len(repos) == 3


class TestGetRecentCommits:
    '''Tests for get_recent_commits method.'''

    @patch("src.github_profiler.httpx.Client")
    def test_returns_commits(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        def get_side_effect(endpoint, params=None):
            if endpoint == "/user":
                return mock_response({"login": "testuser"})
            elif endpoint == "/repos/user/repo/commits":
                # List commits endpoint
                return mock_response(
                    [
                        {
                            "sha": "abc123",
                            "commit": {
                                "message": "Fix bug",
                                "author": {
                                    "name": "Test User",
                                    "date": "2024-01-15T10:00:00Z",
                                },
                            },
                        },
                    ]
                )
            elif endpoint == "/repos/user/repo/commits/abc123":
                # Single commit detail endpoint
                return mock_response(
                    {
                        "stats": {"total": 5, "additions": 10, "deletions": 3},
                        "files": [{"filename": "test.py", "patch": "+line1\n-line2"}],
                    }
                )
            return mock_response([])

        mock_client.get.side_effect = get_side_effect

        with GitHubProfiler(token="fake-token") as profiler:
            commits = profiler.get_recent_commits("user/repo", include_diffs=True)

        assert len(commits) == 1
        assert commits[0].sha == "abc123"
        assert commits[0].message == "Fix bug"
        assert commits[0].additions == 10
        assert commits[0].deletions == 3
        assert "test.py" in commits[0].diff

    @patch("src.github_profiler.httpx.Client")
    def test_without_diffs(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        def get_side_effect(endpoint, params=None):
            if endpoint == "/user":
                return mock_response({"login": "testuser"})
            elif "/commits" in endpoint:
                return mock_response(
                    [
                        {
                            "sha": "abc123",
                            "commit": {
                                "message": "Fix bug",
                                "author": {
                                    "name": "Test User",
                                    "date": "2024-01-15T10:00:00Z",
                                },
                            },
                        },
                    ]
                )
            return mock_response([])

        mock_client.get.side_effect = get_side_effect

        with GitHubProfiler(token="fake-token") as profiler:
            commits = profiler.get_recent_commits("user/repo", include_diffs=False)

        assert len(commits) == 1
        assert commits[0].diff is None


class TestGetRecentPRs:
    '''Tests for get_recent_prs method.'''

    @patch("src.github_profiler.httpx.Client")
    def test_returns_prs(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        def get_side_effect(endpoint, params=None):
            if endpoint == "/user":
                return mock_response({"login": "testuser"})
            elif endpoint == "/search/issues":
                return mock_response(
                    {
                        "items": [
                            {
                                "number": 42,
                                "title": "Add feature",
                                "body": "This PR adds...",
                                "state": "open",
                                "user": {"login": "testuser"},
                                "created_at": "2024-01-15T10:00:00Z",
                                "repository_url": "https://api.github.com/repos/user/repo",
                                "pull_request": {"merged_at": None},
                            },
                        ]
                    }
                )
            return mock_response([])

        mock_client.get.side_effect = get_side_effect

        with GitHubProfiler(token="fake-token") as profiler:
            prs = profiler.get_recent_prs()

        assert len(prs) == 1
        assert prs[0].number == 42
        assert prs[0].title == "Add feature"
        assert prs[0].repo == "user/repo"


class TestGetRecentIssues:
    '''Tests for get_recent_issues method.'''

    @patch("src.github_profiler.httpx.Client")
    def test_returns_issues(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        def get_side_effect(endpoint, params=None):
            if endpoint == "/user":
                return mock_response({"login": "testuser"})
            elif endpoint == "/search/issues":
                return mock_response(
                    {
                        "items": [
                            {
                                "number": 99,
                                "title": "Bug report",
                                "body": "Found a bug...",
                                "state": "open",
                                "user": {"login": "testuser"},
                                "created_at": "2024-01-15T10:00:00Z",
                                "repository_url": "https://api.github.com/repos/user/repo",
                                "labels": [{"name": "bug"}, {"name": "urgent"}],
                            },
                        ]
                    }
                )
            return mock_response([])

        mock_client.get.side_effect = get_side_effect

        with GitHubProfiler(token="fake-token") as profiler:
            issues = profiler.get_recent_issues()

        assert len(issues) == 1
        assert issues[0].number == 99
        assert issues[0].title == "Bug report"
        assert issues[0].labels == ["bug", "urgent"]


class TestCreateIssue:
    '''Tests for create_issue method.'''

    @patch("src.github_profiler.httpx.Client")
    def test_creates_issue(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.post.return_value = mock_response(
            {"html_url": "https://github.com/user/repo/issues/123"}
        )

        with GitHubProfiler(token="fake-token") as profiler:
            url = profiler.create_issue("user/repo", "Test Issue", "Issue body")

        assert url == "https://github.com/user/repo/issues/123"
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "/repos/user/repo/issues"
        assert call_args[1]["json"]["title"] == "Test Issue"
        assert call_args[1]["json"]["body"] == "Issue body"


class TestTokenRequired:
    '''Tests for token validation.'''

    def test_raises_without_token(self):
        with patch.dict("os.environ", {}, clear=True):
            with patch("src.github_profiler.config.GITHUB_TOKEN", None):
                try:
                    GitHubProfiler(token=None)
                    assert False, "Should have raised ValueError"
                except ValueError as e:
                    assert "token is required" in str(e).lower()
