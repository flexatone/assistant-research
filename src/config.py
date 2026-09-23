"""Configuration settings for the research assistant."""

import os
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# Secrets (from environment variables)
# =============================================================================

GITHUB_TOKEN = os.getenv("USER_GITHUB_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Postmark token and addresses for emailing the digest
POSTMARK_SERVER_TOKEN = os.getenv("POSTMARK_SERVER_TOKEN")
DIGEST_EMAIL_FROM = os.getenv("DIGEST_EMAIL_FROM")
DIGEST_EMAIL_TO = os.getenv("DIGEST_EMAIL_TO")

# Identifies a workflow run; reruns of the same run share it (unset outside Actions)
DIGEST_RUN_KEY = os.getenv("GITHUB_RUN_ID")

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

# Maximum concurrent requests while building the profile; bursts of dozens of
# simultaneous connections to api.github.com can fail during the TLS handshake
MAX_PROFILE_WORKERS = 8

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
    ("404 Media", "https://www.404media.co/rss", 10),
    ("ACM News", "https://cacm.acm.org/section/news/feed", 10),
    ("ACM Research", "https://cacm.acm.org/section/research/feed", 10),
    ("Ars Technica", "http://feeds.arstechnica.com/arstechnica/index", 10),
    ("Bleeping Computer", "https://www.bleepingcomputer.com/feed", 10),
    ("Dark Reading", "https://www.darkreading.com/rss.xml", 10),
    ("dev.to", "https://dev.to/feed", 10),
    ("Google Deepmind", "https://deepmind.google/blog/rss.xml", 10),
    ("Hacker News", "https://hnrss.org/frontpage", 10),
    ("HackerNoon", "https://hackernoon.com/feed", 10),
    ("Hugging Face", "https://huggingface.co/blog/feed.xml", 10),
    ("Krebs on Security", "https://krebsonsecurity.com/feed", 10),
    ("Lobsters", "https://lobste.rs/rss", 10),
    ("LWN.net", "https://lwn.net/headlines/rss", 10),
    ("MIT Research News", "https://news.mit.edu/rss/research", 10),
    ("MIT Technology Review", "http://www.technologyreview.com/feed", 10),
    ("O'Reilly Radar", "https://www.oreilly.com/radar/feed", 10),
    ("OpenAI", "https://openai.com/news/rss.xml", 10),
    ("Python Insider", "https://blog.python.org/feeds/posts/default?alt=rss", 2),
    ("Real Python", "https://realpython.com/atom.xml", 10),
    ("Rust Blog", "https://blog.rust-lang.org/feed.xml", 4),
    ("Tech Crunch", "https://techcrunch.com/feed", 10),
    ("The Hacker News", "https://feeds.feedburner.com/TheHackersNews?format=xml", 10),
    ("The Verge", "http://www.theverge.com/rss/full.xml", 10),
    ("Wired: AI", "https://www.wired.com/feed/tag/ai/latest/rss", 10),
    ("Wired: Science", "https://www.wired.com/feed/category/science/latest/rss", 10),
    ("Wired: Security", "https://www.wired.com/feed/category/security/latest/rss", 10),
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
RELEVANCE_THRESHOLD = 0.65

# Model to use for relevance scoring (fast and cheap)
SCORING_MODEL = "claude-sonnet-5"

# Maximum articles to score in a single batch
SCORING_BATCH_SIZE = 20

# Maximum output tokens per scoring request; the model thinks by default and
# thinking counts toward this limit
SCORING_MAX_TOKENS = 16000

# =============================================================================
# Digest Generation Settings
# =============================================================================

# Model to use for digest generation (more capable for synthesis)
DIGEST_MODEL = "claude-opus-5-5"

# Maximum output tokens for the digest, including thinking (on by default)
DIGEST_MAX_TOKENS = 16000

# Number of top picks to highlight in the digest
DIGEST_TOP_PICKS = 6

# Repository to post digest issues to (owner/repo format)
# If None, --post-issue will fail
DIGEST_ISSUE_REPO: str | None = "flexatone/assistant-research"

# Number of past digest issues to check for deduplication
DIGEST_LOOKBACK = 6

# Number of recent issues to search for this run's issue when a run is retried
DIGEST_RUN_LOOKUP = 30
