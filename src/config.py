"""Configuration settings for the research assistant."""

import os
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# Secrets (from environment variables)
# =============================================================================

GITHUB_TOKEN = os.getenv("USER_GITHUB_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# =============================================================================
# GitHub Profiler Settings
# =============================================================================

# Time window for activity lookback (in days)
PROFILE_DAYS = 30

# Whether to fetch full commit diffs (richer context, more API calls)
INCLUDE_DIFFS = True

# Maximum number of repositories to scan
MAX_REPOS = 40

# Maximum commits to fetch per repository
MAX_COMMITS_PER_REPO = 50

# Maximum PRs to fetch
MAX_PRS = 50

# Maximum issues to fetch
MAX_ISSUES = 50

# Maximum size (in characters) for a single file's diff patch
# Patches larger than this will be truncated
MAX_DIFF_PATCH_SIZE = 2000

# Maximum total diff size per commit (sum of all file patches)
MAX_DIFF_TOTAL_SIZE = 10000

# =============================================================================
# RSS Feed Settings
# =============================================================================

# Default RSS feeds to search
DEFAULT_FEEDS = [
    ("Hacker News", "https://hnrss.org/frontpage"),
    ("Lobsters", "https://lobste.rs/rss"),
    ("dev.to", "https://dev.to/feed"),
    ("Rust Blog", "https://blog.rust-lang.org/feed.xml"),
    ("Krebs on Security", "https://krebsonsecurity.com/feed"),
    ("The Hacker News", "https://feeds.feedburner.com/TheHackersNews?format=xml"),
    ("Real Python", "https://realpython.com/atom.xml"),
    ("Python Insider", "https://blog.python.org/feeds/posts/default?alt=rss"),
    ("MIT Research News", "https://news.mit.edu/rss/research"),
    ("LWN.net", "https://lwn.net/headlines/rss"),
    ("HackerNoon", "https://hackernoon.com/feed"),
]

# User-added custom feeds (name, url) tuples
CUSTOM_FEEDS: list[tuple[str, str]] = []

# Maximum articles to fetch per feed
MAX_ARTICLES_PER_FEED = 20

# =============================================================================
# Relevance Scoring Settings
# =============================================================================

# Minimum relevance score (0-1) to include an article
RELEVANCE_THRESHOLD = 0.6

# Model to use for relevance scoring (fast and cheap)
SCORING_MODEL = "claude-sonnet-4-20250514"

# Maximum articles to score in a single batch
SCORING_BATCH_SIZE = 10

# =============================================================================
# Digest Generation Settings
# =============================================================================

# Model to use for digest generation (more capable for synthesis)
DIGEST_MODEL = "claude-opus-4-5-20250514"

# Maximum tokens for digest output; 32k is max for opus
DIGEST_MAX_TOKENS = 4096

# Number of top picks to highlight in the digest
DIGEST_TOP_PICKS = 10

# Repository to post digest issues to (owner/repo format)
# If None, --post-issue will fail
DIGEST_ISSUE_REPO: str | None = "flexatone/assistant-research"
