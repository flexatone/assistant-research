"""Hidden markers in digest issue bodies that make emailing and recording retry-safe.

Each digest issue carries HTML comments (not shown when rendered):
    <!-- digest-run: <run key> -->         the workflow run that created it
    <!-- email: pending|sent|failed -->    whether the digest email went out

The issue is created as pending before the email is sent, then marked sent (or
failed if Postmark rejected the email). A rerun of the same workflow run finds
its issue by run key and does not email again unless the status is failed.
"""

import re
from typing import Optional

from .github_profiler import Issue

PENDING = "pending"
SENT = "sent"
FAILED = "failed"

_STATUS_RE = re.compile(r"<!-- email: (pending|sent|failed) -->")
_RUN_RE = re.compile(r"<!-- digest-run: (\S+) -->")


def build_issue_body(
    article_list: str, run_key: Optional[str], status: Optional[str]
) -> str:
    """Append run and email-status markers to an issue body."""
    lines = [article_list or "_No articles selected._", ""]
    if run_key:
        lines.append(f"<!-- digest-run: {run_key} -->")
    if status:
        lines.append(f"<!-- email: {status} -->")
    return "\n".join(lines)


def set_status(body: str, status: str) -> str:
    return _STATUS_RE.sub(f"<!-- email: {status} -->", body)


def get_status(body: Optional[str]) -> Optional[str]:
    m = _STATUS_RE.search(body or "")
    return m.group(1) if m else None


def get_run_key(body: Optional[str]) -> Optional[str]:
    m = _RUN_RE.search(body or "")
    return m.group(1) if m else None


def run_status(
    issues: list[Issue], run_key: str
) -> tuple[Optional[str], Optional[Issue]]:
    """Return the status and issue recorded for run_key, if any.

    If several issues share the run key, sent wins over pending over failed, so a
    delivered email is never sent again.
    """
    matches = [i for i in issues if get_run_key(i.body) == run_key]
    for status in (SENT, PENDING, FAILED):
        for issue in matches:
            if get_status(issue.body) == status:
                return status, issue
    return None, None
