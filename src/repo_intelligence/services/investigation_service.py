
import re
from typing import Any

from repo_intelligence.github_client import (
    GitHubAPIError,
    GitHubClient,
)

_STOP_WORDS = {
    "about", "after", "again", "also", "because", "being", "could",
    "does", "from", "have", "into", "issue", "more", "should",
    "that", "their", "there", "these", "this", "using", "when",
    "where", "which", "with", "would",
}


def _title_search_terms(title: str, limit: int = 3) -> str:
    """Extract a few distinctive words for related-issue search."""
    words = re.findall(r"[A-Za-z0-9_+#.-]+", title)

    selected = []
    for word in words:
        if len(word) < 3 or word.lower() in _STOP_WORDS:
            continue
        if word.lower() not in {item.lower() for item in selected}:
            selected.append(word)

        if len(selected) == limit:
            break

    # Fall back to the first meaningful title word when possible.
    if not selected and words:
        selected = [words[0]]

    return " ".join(f'"{word}"' for word in selected)


async def build_issue_investigation(
    client: GitHubClient,
    owner: str,
    repo: str,
    issue_number: int,
) -> dict[str, Any]:
    """Gather GitHub evidence for an issue without guessing root cause."""
    report: dict[str, Any] = {
        "repository": f"{owner}/{repo}",
        "issue_number": issue_number,
        "status": "complete",
        "issue": None,
        "related_issues": None,
        "pull_requests": None,
        "recent_commits": None,
        "errors": [],
        "conclusions": {
            "verified_root_cause": None,
            "limitations": [
                "Repository metadata alone does not prove root cause.",
                "A matching title or commit message is not proof of a fix.",
                "Local source code has not yet been analyzed.",
                "No tests have been executed by this service.",
            ],
        },
    }

    try:
        issue = await client.get_issue(owner, repo, issue_number)
        report["issue"] = issue
    except (GitHubAPIError, ValueError) as exc:
        report["status"] = "failed"
        report["errors"].append({
            "step": "get_issue",
            "message": str(exc),
        })
        return report

    # Each supporting lookup can fail independently.
    title = issue.get("title", "")
    search_terms = _title_search_terms(title)

    if search_terms:
        try:
            related = await client.search_issues(
                owner,
                repo,
                search_terms,
                limit=5,
            )
            related["items"] = [
                item for item in related["items"]
                if item["number"] != issue_number
            ]
            report["related_issues"] = related
        except (GitHubAPIError, ValueError) as exc:
            report["errors"].append({
                "step": "related_issues",
                "message": str(exc),
            })
    else:
        report["related_issues"] = {
            "items": [],
            "note": "No useful search terms could be extracted.",
        }

    try:
        report["pull_requests"] = await client.list_pull_requests(
            owner, repo, state="all", limit=5
        )
    except (GitHubAPIError, ValueError) as exc:
        report["errors"].append({
            "step": "pull_requests",
            "message": str(exc),
        })

    try:
        report["recent_commits"] = await client.list_commits(
            owner, repo, limit=5
        )
    except (GitHubAPIError, ValueError) as exc:
        report["errors"].append({
            "step": "recent_commits",
            "message": str(exc),
        })

    if report["errors"]:
        report["status"] = "partial"

    return report
