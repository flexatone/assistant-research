"""Sends email via the Postmark API."""

import json
from urllib.request import Request, urlopen

import markdown

POSTMARK_URL = "https://api.postmarkapp.com/email"


def render_digest_html(markdown_text: str) -> str:
    """Render a markdown digest as HTML for an email body."""
    return markdown.markdown(markdown_text, extensions=["extra", "sane_lists"])


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
    with urlopen(req) as resp:
        resp.read()
