#!/usr/bin/env python3
"""CLI for the research assistant."""

import argparse
import re
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from src.github_profiler import GitHubProfiler
from src.profile_builder import ProfileBuilder
from src.rss_searcher import RSSSearcher
from src.relevance_scorer import RelevanceScorer
from src.digest_writer import DigestWriter, format_article_list
from src.email_sender import render_digest_html, send_email
from src import config


def extract_urls_from_text(text: str) -> frozenset[str]:
    """Extract all URLs from markdown or plain text."""
    if not text:
        return frozenset()
    # Match URLs in markdown links [text](url) and plain URLs
    url_pattern = r'https?://[^\s\)\]>"\']+'
    return frozenset(re.findall(url_pattern, text))


def cmd_profile(args):
    """Generate and display the GitHub activity profile."""
    print(f"Building activity profile (last {config.PROFILE_DAYS} days)...")
    print(f"Include diffs: {config.INCLUDE_DIFFS}")
    print()

    try:
        with GitHubProfiler(config.GITHUB_TOKEN) as profiler:
            builder = ProfileBuilder(profiler)
            profile = builder.build_profile()

            print(f"Found {len(profile.active_repos)} active repos")
            print(f"Found {len(profile.recent_commits)} commits")
            print(f"Found {len(profile.recent_prs)} PRs")
            print(f"Found {len(profile.recent_issues)} issues")
            print()

            if args.output:
                summary = builder.summarize_for_llm(config.INCLUDE_DIFFS)
                with open(args.output, "w") as f:
                    f.write(summary)
                print(f"Profile written to {args.output}")
            else:
                print(builder.summarize_for_llm(config.INCLUDE_DIFFS))

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_search(args):
    """Search RSS feeds for relevant articles based on GitHub profile."""
    print(f"Building activity profile (last {config.PROFILE_DAYS} days)...")

    try:
        # Build the profile first
        with GitHubProfiler(config.GITHUB_TOKEN) as profiler:
            builder = ProfileBuilder(profiler)
            profile = builder.build_profile()
            # heading_level=2 since relevance_scorer prompt uses # for section headers
            profile_summary = builder.summarize_for_llm(
                config.INCLUDE_DIFFS, heading_level=2
            )

        print(
            f"Profile built: {len(profile.active_repos)} repos, {len(profile.recent_commits)} commits"
        )
        print()

        # Fetch articles from RSS feeds
        print(f"Fetching articles from {len(config.DEFAULT_FEEDS)} feeds...")
        searcher = RSSSearcher(config.DEFAULT_FEEDS)
        articles = searcher.fetch_all_feeds()
        print(f"Found {len(articles)} articles")
        print()

        if not articles:
            print("No articles found in feeds.")
            return

        # Score articles for relevance
        print(
            f"Scoring articles for relevance (threshold: {config.RELEVANCE_THRESHOLD})..."
        )
        scorer = RelevanceScorer(config.ANTHROPIC_API_KEY)
        scored_articles = scorer.score_articles(profile_summary, articles)
        print(f"Found {len(scored_articles)} relevant articles")
        print()

        if not scored_articles:
            print("No articles matched your interests above the relevance threshold.")
            return

        # Format output
        output_lines = [
            "# Relevant Articles",
            f"Based on your GitHub activity profile ({profile.username})",
            "",
        ]

        for scored in scored_articles:
            article = scored.article
            date_str = (
                article.published.strftime("%Y-%m-%d")
                if article.published
                else "Unknown date"
            )
            output_lines.append(f"## [{article.title}]({article.url})")
            output_lines.append(
                f"**Source:** {article.source} | **Date:** {date_str} | **Relevance:** {scored.score:.2f}"
            )
            output_lines.append(f"**Why relevant:** {scored.explanation}")
            if article.summary:
                output_lines.append(f"\n{article.summary}")
            output_lines.append("")

        output = "\n".join(output_lines)

        if args.output:
            with open(args.output, "w") as f:
                f.write(output)
            print(f"Results written to {args.output}")
        else:
            print(output)

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_test_feeds(_args):
    """Test all configured RSS feeds and report which are parsable."""
    searcher = RSSSearcher(config.DEFAULT_FEEDS)
    print(f"Testing {len(searcher.feeds)} feeds...\n")

    results = searcher.fetch_all_feeds_with_results()

    # Print results
    max_name_len = max(len(r.name) for r in results)
    for result in results:
        if result.ok:
            print(
                f"  {result.name:<{max_name_len}}  OK ({len(result.articles)} articles)"
            )
        else:
            print(f"  {result.name:<{max_name_len}}  FAIL - {result.error}")

    # Summary
    ok_count = sum(1 for r in results if r.ok)
    print(f"\n{ok_count}/{len(results)} feeds working")


def cmd_digest(args):
    """Generate a full digest: profile + search + summarize."""
    print(f"Building activity profile (last {config.PROFILE_DAYS} days)...")

    try:
        # Build the profile first
        with GitHubProfiler(config.GITHUB_TOKEN) as profiler:
            builder = ProfileBuilder(profiler)
            profile = builder.build_profile()
            # heading_level=3 since digest_writer prompt uses ## for section headers
            profile_summary = builder.summarize_for_llm(
                config.INCLUDE_DIFFS, heading_level=3
            )

        print(
            f"Profile built: {len(profile.active_repos)} repos, {len(profile.recent_commits)} commits"
        )
        print()

        # Fetch articles from RSS feeds
        print(f"Fetching articles from {len(config.DEFAULT_FEEDS)} feeds...")
        searcher = RSSSearcher(config.DEFAULT_FEEDS)
        articles = searcher.fetch_all_feeds()
        print(f"Found {len(articles)} articles")
        print()

        if not articles:
            print("No articles found in feeds.")
            return

        # Deduplicate: remove articles that were in recent digests
        if config.DIGEST_ISSUE_REPO:
            with GitHubProfiler(config.GITHUB_TOKEN) as profiler:
                recent_issues = profiler.get_latest_issues(
                    config.DIGEST_ISSUE_REPO, limit=config.DIGEST_LOOKBACK
                )
                if recent_issues:
                    previous_urls: set[str] = set()
                    for issue in recent_issues:
                        if issue.body:
                            previous_urls |= extract_urls_from_text(issue.body)
                    original_count = len(articles)
                    articles = [a for a in articles if a.url not in previous_urls]
                    deduped = original_count - len(articles)
                    if deduped > 0:
                        print(
                            f"Removed {deduped} articles from last {len(recent_issues)} digests"
                        )
                        print()

        # Score articles for relevance
        print(
            f"Scoring articles for relevance (threshold: {config.RELEVANCE_THRESHOLD})..."
        )
        scorer = RelevanceScorer(config.ANTHROPIC_API_KEY)
        scored_articles = scorer.score_articles(profile_summary, articles)
        print(f"Found {len(scored_articles)} relevant articles")
        print()

        # Generate digest
        print("Generating digest...")
        writer = DigestWriter(config.ANTHROPIC_API_KEY)
        digest = writer.generate_digest(profile_summary, scored_articles)
        print()

        if args.output:
            with open(args.output, "w") as f:
                f.write(digest)
            print(f"Digest written to {args.output}")

        pacific = ZoneInfo("America/Los_Angeles")
        now = datetime.now(pacific)

        # Email first: if sending fails, no issue is recorded, so articles are not deduped
        if args.send_email:
            if not (
                config.POSTMARK_SERVER_TOKEN
                and config.DIGEST_EMAIL_FROM
                and config.DIGEST_EMAIL_TO
            ):
                print(
                    "Error: POSTMARK_SERVER_TOKEN, DIGEST_EMAIL_FROM, and DIGEST_EMAIL_TO must be set",
                    file=sys.stderr,
                )
                sys.exit(1)

            print(f"Emailing digest to {config.DIGEST_EMAIL_TO}...")
            send_email(
                config.POSTMARK_SERVER_TOKEN,
                config.DIGEST_EMAIL_FROM,
                config.DIGEST_EMAIL_TO,
                now.strftime("Digest: %A, %Y-%m-%d"),
                render_digest_html(digest),
                digest,
            )
            print("Email sent")

        # Record only the selected articles (no commentary) for later deduplication
        if args.post_issue:
            if not config.DIGEST_ISSUE_REPO:
                print("Error: DIGEST_ISSUE_REPO not configured", file=sys.stderr)
                sys.exit(1)

            if scored_articles:
                print(f"Recording articles as issue in {config.DIGEST_ISSUE_REPO}...")
                title = now.strftime("Digest: %A, %Y-%m-%d, %H:%M")
                with GitHubProfiler(config.GITHUB_TOKEN) as profiler:
                    issue_url = profiler.create_issue(
                        config.DIGEST_ISSUE_REPO,
                        title,
                        format_article_list(scored_articles),
                    )
                print(f"Issue created: {issue_url}")
            else:
                print("No articles to record; skipping issue")

        if not args.output and not args.post_issue and not args.send_email:
            print(digest)

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Research assistant - profile GitHub activity and find relevant articles"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Profile command
    profile_parser = subparsers.add_parser(
        "profile", help="Generate GitHub activity profile"
    )
    profile_parser.add_argument(
        "-o", "--output", help="Write profile to file instead of stdout"
    )
    profile_parser.set_defaults(func=cmd_profile)

    # Search command
    search_parser = subparsers.add_parser(
        "search", help="Search RSS feeds for relevant articles"
    )
    search_parser.add_argument(
        "-o", "--output", help="Write results to file instead of stdout"
    )
    search_parser.set_defaults(func=cmd_search)

    # Digest command
    digest_parser = subparsers.add_parser(
        "digest", help="Generate full digest (profile + search + summarize)"
    )
    digest_parser.add_argument(
        "-o", "--output", help="Write digest to file instead of stdout"
    )
    digest_parser.add_argument(
        "--post-issue",
        action="store_true",
        help="Record selected articles (no commentary) as a GitHub issue for deduplication (requires DIGEST_ISSUE_REPO config)",
    )
    digest_parser.add_argument(
        "--send-email",
        action="store_true",
        help="Email the digest via Postmark (requires POSTMARK_SERVER_TOKEN, DIGEST_EMAIL_FROM, DIGEST_EMAIL_TO)",
    )
    digest_parser.set_defaults(func=cmd_digest)

    # Test feeds command
    test_feeds_parser = subparsers.add_parser(
        "test-feeds", help="Test all RSS feeds for connectivity"
    )
    test_feeds_parser.set_defaults(func=cmd_test_feeds)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
