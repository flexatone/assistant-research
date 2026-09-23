"""Sends email via the Postmark API."""

import json
from urllib.request import Request, urlopen

import markdown
import nh3

POSTMARK_URL = "https://api.postmarkapp.com/email"

# Seconds to wait on the Postmark connection before failing, so a stalled
# request cannot hang the scheduled job
POSTMARK_TIMEOUT = 30.0

# The digest is model output shaped by RSS content, so the rendered HTML is
# reduced to an allowlist. No images (tracking pixels), no style or class
# attributes, and links only to absolute http(s)/mailto URLs.
_ALLOWED_TAGS = {
    "a", "abbr", "b", "blockquote", "br", "code", "dd", "del", "dl", "dt", "em",
    "h1", "h2", "h3", "h4", "h5", "h6", "hr", "i", "li", "ol", "p", "pre", "s",
    "strong", "sub", "sup", "table", "tbody", "td", "th", "thead", "tr", "ul",
}
_ALLOWED_ATTRIBUTES = {
    "a": {"href", "title"},
    "abbr": {"title"},
    "ol": {"start"},
}
_ALLOWED_URL_SCHEMES = {"http", "https", "mailto"}


def render_digest_html(markdown_text: str) -> str:
    """Render a markdown digest as sanitized HTML for an email body."""
    html = markdown.markdown(markdown_text, extensions=["extra", "sane_lists"])
    return nh3.clean(
        html,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRIBUTES,
        url_schemes=_ALLOWED_URL_SCHEMES,
        url_relative="deny",
    )


def send_email(
    token: str,
    from_email: str,
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str,
) -> None:
    """Send an email through Postmark; raises on failure."""
    payload = json.dumps(
        {
            "From": from_email,
            "To": to_email,
            "Subject": subject,
            "HtmlBody": html_body,
            "TextBody": text_body,
            "MessageStream": "outbound",
        }
    ).encode()

    req = Request(
        POSTMARK_URL,
        data=payload,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Postmark-Server-Token": token,
        },
        method="POST",
    )
    with urlopen(req, timeout=POSTMARK_TIMEOUT) as resp:
        resp.read()
