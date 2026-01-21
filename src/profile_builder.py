"""Aggregates GitHub data into a structured activity profile."""

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from .github_profiler import GitHubProfiler, Commit, PullRequest, Issue, Repo
from . import config


@dataclass(frozen=True)
class CommitSummary:
    """Summary of a commit for the profile."""

    sha: str
    repo: str
    message: str
    date: datetime
    additions: int
    deletions: int
    diff: str | None = None


@dataclass(frozen=True)
class PRSummary:
    """Summary of a pull request for the profile."""

    number: int
    repo: str
    title: str
    body: str | None
    state: str
    created_at: datetime


@dataclass(frozen=True)
class IssueSummary:
    """Summary of an issue for the profile."""

    number: int
    repo: str
    title: str
    body: str | None
    state: str
    labels: list[str]
    created_at: datetime


@dataclass(frozen=True)
class RepoSummary:
    """Summary of a repository for the profile."""

    full_name: str
    description: str | None
    language: str | None
    topics: list[str]
    commit_count: int = 0


@dataclass(frozen=True)
class ActivityProfile:
    """Aggregated activity profile from GitHub."""

    username: str
    time_range: tuple[datetime, datetime]
    languages: dict[str, int] = field(default_factory=dict)
    topics: list[str] = field(default_factory=list)
    recent_commits: list[CommitSummary] = field(default_factory=list)
    recent_prs: list[PRSummary] = field(default_factory=list)
    recent_issues: list[IssueSummary] = field(default_factory=list)
    active_repos: list[RepoSummary] = field(default_factory=list)


class ProfileBuilder:
    """Aggregates GitHub data into a structured profile."""

    def __init__(self, profiler: GitHubProfiler):
        self.profiler = profiler
        self._profile: ActivityProfile | None = None

    def build_profile(self) -> ActivityProfile:
        """
        Build an activity profile from GitHub data.

        Uses config.PROFILE_DAYS and config.INCLUDE_DIFFS for settings.

        Returns:
            ActivityProfile with aggregated data.
        """
        days = config.PROFILE_DAYS
        now = datetime.now(timezone.utc)
        since = now - timedelta(days=days)

        username = self.profiler.get_authenticated_user()

        # Fetch repos first to know where to look for commits
        repos = self.profiler.get_user_repos()

        # Filter to repos with recent activity
        active_repos = [r for r in repos if r.pushed_at and r.pushed_at >= since]

        # Fetch commits from active repos
        all_commits: list[Commit] = []
        repo_commit_counts: dict[str, int] = {}

        for repo in active_repos:
            commits = self.profiler.get_recent_commits(repo.full_name)
            all_commits.extend(commits)
            repo_commit_counts[repo.full_name] = len(commits)

        # Fetch PRs and issues
        prs = self.profiler.get_recent_prs()
        issues = self.profiler.get_recent_issues()

        # Aggregate languages (count repos per language)
        language_counts = Counter(r.language for r in active_repos if r.language)

        # Aggregate topics
        all_topics = []
        for repo in active_repos:
            all_topics.extend(repo.topics)
        topic_counts = Counter(all_topics)
        top_topics = [topic for topic, _ in topic_counts.most_common(20)]

        # Build summaries
        commit_summaries = [
            CommitSummary(
                sha=c.sha[:7],
                repo=c.repo,
                message=c.message.split("\n")[0],  # First line only
                date=c.date,
                additions=c.additions,
                deletions=c.deletions,
                diff=c.diff,
            )
            for c in sorted(all_commits, key=lambda x: x.date, reverse=True)
        ]

        pr_summaries = [
            PRSummary(
                number=pr.number,
                repo=pr.repo,
                title=pr.title,
                body=pr.body[:500] if pr.body else None,  # Truncate long bodies
                state=pr.state,
                created_at=pr.created_at,
            )
            for pr in prs
        ]

        issue_summaries = [
            IssueSummary(
                number=issue.number,
                repo=issue.repo,
                title=issue.title,
                body=issue.body[:500] if issue.body else None,
                state=issue.state,
                labels=issue.labels,
                created_at=issue.created_at,
            )
            for issue in issues
        ]

        repo_summaries = [
            RepoSummary(
                full_name=r.full_name,
                description=r.description,
                language=r.language,
                topics=r.topics,
                commit_count=repo_commit_counts.get(r.full_name, 0),
            )
            for r in active_repos
            if repo_commit_counts.get(r.full_name, 0) > 0
        ]

        self._profile = ActivityProfile(
            username=username,
            time_range=(since, now),
            languages=dict(language_counts),
            topics=top_topics,
            recent_commits=commit_summaries,
            recent_prs=pr_summaries,
            recent_issues=issue_summaries,
            active_repos=repo_summaries,
        )

        return self._profile

    def summarize_for_llm(self, include_diffs: bool | None = None) -> str:
        """
        Format the profile as a text summary suitable for an LLM.

        Args:
            include_diffs: Whether to include code diffs. Defaults to config.INCLUDE_DIFFS.

        Returns:
            Formatted string summary of the activity profile.
        """
        if self._profile is None:
            self.build_profile()

        profile = self._profile
        include_diffs = (
            include_diffs if include_diffs is not None else config.INCLUDE_DIFFS
        )

        lines = [
            f"# GitHub Activity Profile for {profile.username}",
            f"Period: {profile.time_range[0].strftime('%Y-%m-%d')} to {profile.time_range[1].strftime('%Y-%m-%d')}",
            "",
        ]

        # Languages
        if profile.languages:
            lines.append("## Languages")
            for lang, count in sorted(profile.languages.items(), key=lambda x: -x[1]):
                lines.append(f"- {lang}: {count} repos")
            lines.append("")

        # Topics
        if profile.topics:
            lines.append("## Topics/Tags")
            lines.append(", ".join(profile.topics))
            lines.append("")

        # Active repositories
        if profile.active_repos:
            lines.append("## Active Repositories")
            for repo in profile.active_repos:
                desc = f" - {repo.description}" if repo.description else ""
                lines.append(
                    f"- **{repo.full_name}** ({repo.commit_count} commits){desc}"
                )
                if repo.topics:
                    lines.append(f"  Topics: {', '.join(repo.topics)}")
            lines.append("")

        # Recent commits
        if profile.recent_commits:
            lines.append("## Recent Commits")
            for commit in profile.recent_commits[:30]:  # Limit for LLM context
                lines.append(f"### {commit.repo} - {commit.sha}")
                lines.append(f"Date: {commit.date.strftime('%Y-%m-%d %H:%M')}")
                lines.append(f"Message: {commit.message}")
                lines.append(f"Changes: +{commit.additions}/-{commit.deletions}")

                if include_diffs and commit.diff:
                    lines.append("```diff")
                    # Truncate very long diffs
                    diff = commit.diff
                    if len(diff) > 2000:
                        diff = diff[:2000] + "\n... (truncated)"
                    lines.append(diff)
                    lines.append("```")
                lines.append("")

        # Pull requests
        if profile.recent_prs:
            lines.append("## Recent Pull Requests")
            for pr in profile.recent_prs:
                status = "merged" if pr.state == "closed" else pr.state
                lines.append(f"### {pr.repo}#{pr.number}: {pr.title}")
                lines.append(
                    f"Status: {status} | Created: {pr.created_at.strftime('%Y-%m-%d')}"
                )
                if pr.body:
                    lines.append(f"Description: {pr.body}")
                lines.append("")

        # Issues
        if profile.recent_issues:
            lines.append("## Recent Issues")
            for issue in profile.recent_issues:
                labels = f" [{', '.join(issue.labels)}]" if issue.labels else ""
                lines.append(f"### {issue.repo}#{issue.number}: {issue.title}{labels}")
                lines.append(
                    f"Status: {issue.state} | Created: {issue.created_at.strftime('%Y-%m-%d')}"
                )
                if issue.body:
                    lines.append(f"Description: {issue.body}")
                lines.append("")

        return "\n".join(lines)
