"""Configuration settings for the research assistant."""

import os
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# Secrets (from environment variables)
# =============================================================================

GITHUB_TOKEN = os.getenv("USER_GITHUB_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Comma-separated list of GitHub organizations whose repos should be excluded
EXCLUDED_ORGS_STR = os.getenv("EXCLUDED_ORGS", "")
EXCLUDED_ORGS = [org.strip() for org in EXCLUDED_ORGS_STR.split(",") if org.strip()]

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
MAX_COMMITS_PER_REPO = 10

# Maximum PRs to fetch
MAX_PRS = 50

# Maximum issues to fetch
MAX_ISSUES = 50

# Maximum size (in characters) for a single file's diff patch
# Patches larger than this will be truncated
MAX_DIFF_PATCH_SIZE = 1000   # was 2000

# Maximum total diff size per commit (sum of all file patches)
MAX_DIFF_TOTAL_SIZE = 8000  # was 10000

# =============================================================================
# Profile Sources
# =============================================================================

# Default RSS feeds: (name, url, max_articles)
DEFAULT_FEEDS = [
    ("Hacker News", "https://hnrss.org/frontpage", 20),
    ("Lobsters", "https://lobste.rs/rss", 20),
    ("dev.to", "https://dev.to/feed", 20),
    ("Krebs on Security", "https://krebsonsecurity.com/feed", 20),
    ("The Hacker News", "https://feeds.feedburner.com/TheHackersNews?format=xml", 20),
    ("Real Python", "https://realpython.com/atom.xml", 20),
    ("MIT Research News", "https://news.mit.edu/rss/research", 20),
    ("LWN.net", "https://lwn.net/headlines/rss", 20),
    ("HackerNoon", "https://hackernoon.com/feed", 20),
    ("O'Reilly Radar", "https://www.oreilly.com/radar/feed", 20),
    ("Rust Blog", "https://blog.rust-lang.org/feed.xml", 4),
    ("Python Insider", "https://blog.python.org/feeds/posts/default?alt=rss", 2),
    ("ACM News", "https://cacm.acm.org/section/news/feed", 20),
    ("ACM Research", "https://cacm.acm.org/section/research/feed", 20),
]

PROFILE_CONTEXT = [
    ("Articles Published", "https://www.flexatone.net/api/articles", 20),
    ("Code & Systems", "https://www.flexatone.net/api/code", 20),
    ("Talks & Presentations", "https://www.flexatone.net/api/talks", 20),
]


# =============================================================================
# Relevance Scoring Settings
# =============================================================================

# Minimum relevance score (0-1) to include an article
RELEVANCE_THRESHOLD = 0.6

# Model to use for relevance scoring (fast and cheap)
SCORING_MODEL = "claude-sonnet-4-5-20250929"

# Maximum articles to score in a single batch
SCORING_BATCH_SIZE = 20

# =============================================================================
# Digest Generation Settings
# =============================================================================

# Model to use for digest generation (more capable for synthesis)
DIGEST_MODEL = "claude-opus-4-6"

# Maximum tokens for digest output; 32k is max for opus
DIGEST_MAX_TOKENS = 4096

# Number of top picks to highlight in the digest
DIGEST_TOP_PICKS = 8

# Repository to post digest issues to (owner/repo format)
# If None, --post-issue will fail
DIGEST_ISSUE_REPO: str | None = "flexatone/assistant-research"

# Number of past digest issues to check for deduplication
DIGEST_LOOKBACK = 6
