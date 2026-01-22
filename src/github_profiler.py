'''GitHub API client for fetching user activity data.'''

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from . import config


@dataclass(frozen=True)
class Repo:
    '''Repository metadata.'''

    full_name: str
    description: Optional[str]
    language: Optional[str]
    topics: list[str]
    pushed_at: Optional[datetime]


@dataclass(frozen=True)
class Commit:
    '''Commit data with optional diff.'''

    sha: str
    repo: str
    message: str
    author: str
    date: datetime
    files_changed: int
    additions: int
    deletions: int
    diff: Optional[str] = None  # Full diff if INCLUDE_DIFFS is True


@dataclass(frozen=True)
class PullRequest:
    '''Pull request data.'''

    number: int
    repo: str
    title: str
    body: Optional[str]
    state: str
    author: str
    created_at: datetime
    merged_at: Optional[datetime]


@dataclass(frozen=True)
class Issue:
    '''Issue data.'''

    number: int
    repo: str
    title: str
    body: Optional[str]
    state: str
    author: str
    created_at: datetime
    labels: list[str]


class GitHubProfiler:
    '''Fetches activity data from GitHub API.'''

    BASE_URL = "https://api.github.com"

    def __init__(self, token: Optional[str] = None):
        self.token = token or config.GITHUB_TOKEN
        if not self.token:
            raise ValueError(
                "GitHub token is required. Set GITHUB_TOKEN environment variable."
            )

        self.client = httpx.Client(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.client.close()

    def close(self):
        self.client.close()

    def _get(self, endpoint: str, params: Optional[dict] = None) -> dict | list:
        '''Make a GET request to the GitHub API.'''
        response = self.client.get(endpoint, params=params)
        response.raise_for_status()
        return response.json()

    def _parse_datetime(self, dt_str: Optional[str]) -> Optional[datetime]:
        '''Parse GitHub datetime string to datetime object.'''
        if not dt_str:
            return None
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))

    def get_authenticated_user(self) -> str:
        '''Get the username of the authenticated user.'''
        data = self._get("/user")
        return data["login"]

    def get_user_repos(self, limit: Optional[int] = None) -> list[Repo]:
        '''
        Fetch repositories the user has contributed to recently.

        Args:
            limit: Maximum number of repos to return. Defaults to config.MAX_REPOS.

        Returns:
            List of Repo objects sorted by most recently pushed.
        '''
        limit = limit or config.MAX_REPOS

        repos = []
        page = 1
        per_page = min(limit, 100)

        while len(repos) < limit:
            data = self._get(
                "/user/repos",
                params={
                    "sort": "pushed",
                    "direction": "desc",
                    "per_page": per_page,
                    "page": page,
                    "affiliation": "owner,collaborator,organization_member",
                },
            )

            if not data:
                break

            for repo_data in data:
                repos.append(
                    Repo(
                        full_name=repo_data["full_name"],
                        description=repo_data.get("description"),
                        language=repo_data.get("language"),
                        topics=repo_data.get("topics", []),
                        pushed_at=self._parse_datetime(repo_data.get("pushed_at")),
                    )
                )

            if len(data) < per_page:
                break
            page += 1

        return repos[:limit]

    def get_recent_commits(
        self,
        repo: str,
        days: Optional[int] = None,
        include_diffs: Optional[bool] = None,
        limit: Optional[int] = None,
    ) -> list[Commit]:
        '''
        Fetch recent commits from a repository.

        Args:
            repo: Repository full name (e.g., "owner/repo").
            days: Number of days to look back. Defaults to config.PROFILE_DAYS.
            include_diffs: Whether to fetch full diffs. Defaults to config.INCLUDE_DIFFS.
            limit: Maximum commits to fetch. Defaults to config.MAX_COMMITS_PER_REPO.

        Returns:
            List of Commit objects.
        '''
        days = days or config.PROFILE_DAYS
        include_diffs = (
            include_diffs if include_diffs is not None else config.INCLUDE_DIFFS
        )
        limit = limit or config.MAX_COMMITS_PER_REPO

        since = datetime.now(timezone.utc) - timedelta(days=days)
        username = self.get_authenticated_user()

        commits = []
        page = 1
        per_page = min(limit, 100)

        while len(commits) < limit:
            try:
                data = self._get(
                    f"/repos/{repo}/commits",
                    params={
                        "author": username,
                        "since": since.isoformat(),
                        "per_page": per_page,
                        "page": page,
                    },
                )
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 409:  # Empty repository
                    break
                raise

            if not data:
                break

            for commit_data in data:
                commit_detail = commit_data.get("commit", {})

                # Get detailed commit info if we need diffs or stats
                stats = {"total": 0, "additions": 0, "deletions": 0}
                diff = None

                if include_diffs:
                    try:
                        detailed = self._get(
                            f"/repos/{repo}/commits/{commit_data['sha']}"
                        )
                        stats = detailed.get("stats", stats)

                        # Build diff from files, respecting size limits
                        diff_parts = []
                        total_size = 0
                        for file in detailed.get("files", []):
                            filename = file.get("filename", "unknown")
                            patch = file.get("patch", "")

                            # Truncate individual patch if too large
                            if len(patch) > config.MAX_DIFF_PATCH_SIZE:
                                patch = (
                                    patch[: config.MAX_DIFF_PATCH_SIZE]
                                    + "\n... (truncated)"
                                )

                            # Check if adding this would exceed total limit
                            part = (
                                f"--- {filename}\n{patch}"
                                if patch
                                else f"--- {filename}"
                            )
                            if total_size + len(part) > config.MAX_DIFF_TOTAL_SIZE:
                                diff_parts.append("... (remaining files truncated)")
                                break

                            diff_parts.append(part)
                            total_size += len(part)

                        diff = "\n".join(diff_parts) if diff_parts else None
                    except httpx.HTTPStatusError:
                        pass  # Skip diff if we can't fetch it

                commits.append(
                    Commit(
                        sha=commit_data["sha"],
                        repo=repo,
                        message=commit_detail.get("message", ""),
                        author=commit_detail.get("author", {}).get("name", "unknown"),
                        date=self._parse_datetime(
                            commit_detail.get("author", {}).get("date")
                        ),
                        files_changed=stats.get("total", 0),
                        additions=stats.get("additions", 0),
                        deletions=stats.get("deletions", 0),
                        diff=diff,
                    )
                )

            if len(data) < per_page:
                break
            page += 1

        return commits[:limit]

    def get_recent_prs(
        self, days: Optional[int] = None, limit: Optional[int] = None
    ) -> list[PullRequest]:
        '''
        Fetch recent pull requests authored by the user.

        Args:
            days: Number of days to look back. Defaults to config.PROFILE_DAYS.
            limit: Maximum PRs to fetch. Defaults to config.MAX_PRS.

        Returns:
            List of PullRequest objects.
        '''
        days = days or config.PROFILE_DAYS
        limit = limit or config.MAX_PRS

        since = datetime.now(timezone.utc) - timedelta(days=days)

        # Search for PRs authored by the user
        username = self.get_authenticated_user()
        query = f"author:{username} is:pr created:>={since.strftime('%Y-%m-%d')}"

        prs = []
        page = 1
        per_page = min(limit, 100)

        while len(prs) < limit:
            data = self._get(
                "/search/issues",
                params={
                    "q": query,
                    "sort": "created",
                    "order": "desc",
                    "per_page": per_page,
                    "page": page,
                },
            )

            items = data.get("items", [])
            if not items:
                break

            for pr_data in items:
                # Extract repo from URL
                repo_url = pr_data.get("repository_url", "")
                repo = "/".join(repo_url.split("/")[-2:]) if repo_url else "unknown"

                prs.append(
                    PullRequest(
                        number=pr_data["number"],
                        repo=repo,
                        title=pr_data["title"],
                        body=pr_data.get("body"),
                        state=pr_data["state"],
                        author=pr_data["user"]["login"],
                        created_at=self._parse_datetime(pr_data["created_at"]),
                        merged_at=self._parse_datetime(
                            pr_data.get("pull_request", {}).get("merged_at")
                        ),
                    )
                )

            if len(items) < per_page:
                break
            page += 1

        return prs[:limit]

    def get_recent_issues(
        self, days: Optional[int] = None, limit: Optional[int] = None
    ) -> list[Issue]:
        '''
        Fetch recent issues created by the user.

        Args:
            days: Number of days to look back. Defaults to config.PROFILE_DAYS.
            limit: Maximum issues to fetch. Defaults to config.MAX_ISSUES.

        Returns:
            List of Issue objects.
        '''
        days = days or config.PROFILE_DAYS
        limit = limit or config.MAX_ISSUES

        since = datetime.now(timezone.utc) - timedelta(days=days)

        # Search for issues (not PRs) created by the user
        username = self.get_authenticated_user()
        query = f"author:{username} is:issue created:>={since.strftime('%Y-%m-%d')}"

        # Exclude digest issues repo to avoid feedback loop
        if config.DIGEST_ISSUE_REPO:
            query += f" -repo:{config.DIGEST_ISSUE_REPO}"

        issues = []
        page = 1
        per_page = min(limit, 100)

        while len(issues) < limit:
            data = self._get(
                "/search/issues",
                params={
                    "q": query,
                    "sort": "created",
                    "order": "desc",
                    "per_page": per_page,
                    "page": page,
                },
            )

            items = data.get("items", [])
            if not items:
                break

            for issue_data in items:
                # Extract repo from URL
                repo_url = issue_data.get("repository_url", "")
                repo = "/".join(repo_url.split("/")[-2:]) if repo_url else "unknown"

                issues.append(
                    Issue(
                        number=issue_data["number"],
                        repo=repo,
                        title=issue_data["title"],
                        body=issue_data.get("body"),
                        state=issue_data["state"],
                        author=issue_data["user"]["login"],
                        created_at=self._parse_datetime(issue_data["created_at"]),
                        labels=[
                            label["name"] for label in issue_data.get("labels", [])
                        ],
                    )
                )

            if len(items) < per_page:
                break
            page += 1

        return issues[:limit]

    def create_issue(self, repo: str, title: str, body: str) -> str:
        '''
        Create a new issue in a repository.

        Args:
            repo: Repository full name (e.g., "owner/repo").
            title: Issue title.
            body: Issue body (markdown).

        Returns:
            URL of the created issue.
        '''
        response = self.client.post(
            f"/repos/{repo}/issues",
            json={"title": title, "body": body},
        )
        response.raise_for_status()
        data = response.json()
        return data["html_url"]
