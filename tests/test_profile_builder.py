"""Tests for ProfileBuilder."""

from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
import re

from src.profile_builder import ProfileBuilder
from src.github_profiler import GitHubProfiler, Repo, Commit


class TestBuildProfile:
    """Tests for build_profile method with organization filtering."""

    @patch("src.github_profiler.httpx.Client")
    @patch("src.config.EXCLUDED_ORGS", [])
    @patch("src.config.PROFILE_CONTEXT", [])
    @patch("src.config.INCLUDE_DIFFS", False)  # Disable diffs to simplify mocking
    def test_no_excluded_orgs(self, mock_client_class):
        """Test that all active repos are included when no orgs are excluded."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        now = datetime.now(timezone.utc)
        recent = now - timedelta(days=1)
        
        # Mock responses
        def get_side_effect(endpoint, params=None):
            if endpoint == "/user":
                return MagicMock(json=lambda: {"login": "testuser"})
            elif endpoint == "/user/repos":
                return MagicMock(
                    json=lambda: [
                        {
                            "full_name": "testuser/repo1",
                            "description": "Test repo 1",
                            "language": "Python",
                            "topics": ["test"],
                            "pushed_at": recent.isoformat(),
                        },
                        {
                            "full_name": "org1/repo2",
                            "description": "Test repo 2",
                            "language": "Python",
                            "topics": ["test"],
                            "pushed_at": recent.isoformat(),
                        },
                    ]
                )
            elif "/repos/" in endpoint and "/commits" in endpoint:
                # Return one commit for each repo
                return MagicMock(
                    json=lambda: [
                        {
                            "sha": "abc123",
                            "commit": {
                                "message": "Test commit",
                                "author": {
                                    "name": "testuser",
                                    "date": recent.isoformat(),
                                },
                            },
                        }
                    ]
                )
            elif endpoint == "/search/issues":
                return MagicMock(json=lambda: {"items": []})
            return MagicMock(json=lambda: [])

        mock_client.get.side_effect = get_side_effect
        mock_client.post = MagicMock()
        mock_client.close = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with GitHubProfiler(token="fake-token") as profiler:
            builder = ProfileBuilder(profiler)
            profile = builder.build_profile()

        # Both repos should be included
        assert len(profile.active_repos) == 2
        repo_names = [r.full_name for r in profile.active_repos]
        assert "testuser/repo1" in repo_names
        assert "org1/repo2" in repo_names

    @patch("src.github_profiler.httpx.Client")
    @patch("src.config.EXCLUDED_ORGS", ["org1"])
    @patch("src.config.PROFILE_CONTEXT", [])
    @patch("src.config.INCLUDE_DIFFS", False)  # Disable diffs to simplify mocking
    def test_excluded_orgs_filters_repos(self, mock_client_class):
        """Test that repos from excluded orgs are filtered out."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        now = datetime.now(timezone.utc)
        recent = now - timedelta(days=1)
        
        # Mock responses
        def get_side_effect(endpoint, params=None):
            if endpoint == "/user":
                return MagicMock(json=lambda: {"login": "testuser"})
            elif endpoint == "/user/repos":
                return MagicMock(
                    json=lambda: [
                        {
                            "full_name": "testuser/repo1",
                            "description": "Test repo 1",
                            "language": "Python",
                            "topics": ["test"],
                            "pushed_at": recent.isoformat(),
                        },
                        {
                            "full_name": "org1/repo2",
                            "description": "Test repo 2",
                            "language": "Python",
                            "topics": ["test"],
                            "pushed_at": recent.isoformat(),
                        },
                        {
                            "full_name": "org2/repo3",
                            "description": "Test repo 3",
                            "language": "Python",
                            "topics": ["test"],
                            "pushed_at": recent.isoformat(),
                        },
                    ]
                )
            elif "/repos/" in endpoint and "/commits" in endpoint:
                # Return one commit for each repo
                return MagicMock(
                    json=lambda: [
                        {
                            "sha": "abc123",
                            "commit": {
                                "message": "Test commit",
                                "author": {
                                    "name": "testuser",
                                    "date": recent.isoformat(),
                                },
                            },
                        }
                    ]
                )
            elif endpoint == "/search/issues":
                return MagicMock(json=lambda: {"items": []})
            return MagicMock(json=lambda: [])

        mock_client.get.side_effect = get_side_effect
        mock_client.post = MagicMock()
        mock_client.close = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with GitHubProfiler(token="fake-token") as profiler:
            builder = ProfileBuilder(profiler)
            profile = builder.build_profile()

        # Only repos from testuser and org2 should be included (org1 is excluded)
        assert len(profile.active_repos) == 2
        repo_names = [r.full_name for r in profile.active_repos]
        assert "testuser/repo1" in repo_names
        assert "org2/repo3" in repo_names
        assert "org1/repo2" not in repo_names

    @patch("src.github_profiler.httpx.Client")
    @patch("src.config.EXCLUDED_ORGS", ["org1", "org2"])
    @patch("src.config.PROFILE_CONTEXT", [])
    @patch("src.config.INCLUDE_DIFFS", False)  # Disable diffs to simplify mocking
    def test_multiple_excluded_orgs(self, mock_client_class):
        """Test that multiple orgs can be excluded."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        now = datetime.now(timezone.utc)
        recent = now - timedelta(days=1)
        
        # Mock responses
        def get_side_effect(endpoint, params=None):
            if endpoint == "/user":
                return MagicMock(json=lambda: {"login": "testuser"})
            elif endpoint == "/user/repos":
                return MagicMock(
                    json=lambda: [
                        {
                            "full_name": "testuser/repo1",
                            "description": "Test repo 1",
                            "language": "Python",
                            "topics": ["test"],
                            "pushed_at": recent.isoformat(),
                        },
                        {
                            "full_name": "org1/repo2",
                            "description": "Test repo 2",
                            "language": "Python",
                            "topics": ["test"],
                            "pushed_at": recent.isoformat(),
                        },
                        {
                            "full_name": "org2/repo3",
                            "description": "Test repo 3",
                            "language": "Python",
                            "topics": ["test"],
                            "pushed_at": recent.isoformat(),
                        },
                    ]
                )
            elif "/repos/" in endpoint and "/commits" in endpoint:
                # Return one commit for each repo
                return MagicMock(
                    json=lambda: [
                        {
                            "sha": "abc123",
                            "commit": {
                                "message": "Test commit",
                                "author": {
                                    "name": "testuser",
                                    "date": recent.isoformat(),
                                },
                            },
                        }
                    ]
                )
            elif endpoint == "/search/issues":
                return MagicMock(json=lambda: {"items": []})
            return MagicMock(json=lambda: [])

        mock_client.get.side_effect = get_side_effect
        mock_client.post = MagicMock()
        mock_client.close = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with GitHubProfiler(token="fake-token") as profiler:
            builder = ProfileBuilder(profiler)
            profile = builder.build_profile()

        # Only testuser repo should be included (both org1 and org2 are excluded)
        assert len(profile.active_repos) == 1
        assert profile.active_repos[0].full_name == "testuser/repo1"
