"""Configuration settings for the research assistant."""

import os
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# Secrets (from environment variables)
# =============================================================================

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# =============================================================================
# GitHub Profiler Settings
# =============================================================================

# Time window for activity lookback (in days)
PROFILE_DAYS = 14

# Whether to fetch full commit diffs (richer context, more API calls)
INCLUDE_DIFFS = True

# Maximum number of repositories to scan
MAX_REPOS = 20

# Maximum commits to fetch per repository
MAX_COMMITS_PER_REPO = 50

# Maximum PRs to fetch
MAX_PRS = 50

# Maximum issues to fetch
MAX_ISSUES = 50

# =============================================================================
# RSS Feed Settings
# =============================================================================

# Default RSS feeds to search
DEFAULT_FEEDS = [
    ("Hacker News", "https://hnrss.org/frontpage"),
    ("Lobsters", "https://lobste.rs/rss"),
    ("dev.to", "https://dev.to/feed"),
    ("ArXiv CS", "http://arxiv.org/rss/cs"),
    # ("Python Weekly", "https://us2.campaign-archive.com/feed?u=e2e180baf855ac797ef407fc7&id=9e26887fc5"),
    ("Rust Blog", "https://blog.rust-lang.org/feed.xml"),
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
DIGEST_MODEL = "claude-sonnet-4-20250514"

# Maximum tokens for digest output
DIGEST_MAX_TOKENS = 4096
