# assistant-research

A personalized research assistant that generates article digests based on your GitHub activity.

## Environment Variables

### Required
- `USER_GITHUB_TOKEN`: GitHub personal access token for API access
- `ANTHROPIC_API_KEY`: Anthropic API key for LLM-based features

### Optional
- `POSTMARK_SERVER_TOKEN`: Postmark server API token (needed for `digest --send-email`)
- `DIGEST_EMAIL_FROM`: From address for the digest email; must be a Postmark-verified sender
- `DIGEST_EMAIL_TO`: Recipient address for the digest email
- `EXCLUDED_ORGS`: Comma-separated list of GitHub organization names whose repositories should be excluded from your activity profile. Example: `EXCLUDED_ORGS="org1,org2,org3"`

## Features

### Digest Delivery
The daily GitHub Action runs `python main.py digest --send-email --post-issue`:
- `--send-email` sends the full digest (summaries and commentary) by email through Postmark.
- `--post-issue` creates a GitHub issue in `DIGEST_ISSUE_REPO` that lists only the selected articles (title, source, date, relevance), with no commentary. Later runs read the URLs in recent issues to avoid repeating articles.

### Organization Filtering
When building your activity profile, you can exclude repositories belonging to specific organizations by setting the `EXCLUDED_ORGS` environment variable. This is useful for:
- Excluding work-related repositories from personal profiles
- Filtering out repositories from organizations you contribute to but don't want in your digest
- Keeping your activity profile focused on specific projects

Example:
```bash
export EXCLUDED_ORGS="mycompany,another-org"
```