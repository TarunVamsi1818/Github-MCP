
from typing import Any

from mcp.server.fastmcp import FastMCP

from repo_intelligence.github_client import GitHubClient

mcp = FastMCP("Repo Intelligence MCP")


async def _execute(method_name: str, *args: Any, **kwargs: Any) -> Any:
    """Create and close an API client for each tool invocation."""
    client = GitHubClient()
    try:
        method = getattr(client, method_name)
        return await method(*args, **kwargs)
    finally:
        await client.close()


@mcp.tool()
async def search_repository_issues(
    owner: str,
    repo: str,
    query: str,
    limit: int = 10,
) -> dict:
    """Search regular GitHub issues in a repository.

    query can include terms such as is:open, is:closed, label:bug,
    or words from an error message. Results include source URLs.
    """
    return await _execute("search_issues", owner, repo, query, limit)


@mcp.tool()
async def get_repository_issue(
    owner: str,
    repo: str,
    issue_number: int,
) -> dict:
    """Retrieve details of a regular issue by its number."""
    return await _execute("get_issue", owner, repo, issue_number)


@mcp.tool()
async def list_repository_pull_requests(
    owner: str,
    repo: str,
    state: str = "all",
    limit: int = 10,
) -> dict:
    """List repository pull requests and their head commit SHAs."""
    return await _execute(
        "list_pull_requests", owner, repo, state, limit
    )


@mcp.tool()
async def list_recent_repository_commits(
    owner: str,
    repo: str,
    limit: int = 10,
) -> dict:
    """List recent commits with their messages, dates, and source URLs."""
    return await _execute("list_commits", owner, repo, limit)


@mcp.resource("repo-intelligence://capabilities")
def capabilities() -> str:
    """Describe the capabilities and limitations of this MCP server."""
    return (
        "Repo Intelligence MCP provides read-only GitHub issue search, "
        "issue details, pull request listing, and recent commit listing. "
        "It does not prove root cause, edit source code, or merge PRs. "
        "Use returned URLs as evidence and distinguish facts from hypotheses."
    )


@mcp.prompt()
def investigate_issue(owner: str, repo: str, issue_number: int) -> str:
    """Create a reusable evidence-driven issue investigation prompt."""
    return f"""
Investigate issue #{issue_number} in {owner}/{repo}.

1. Retrieve the issue using get_repository_issue.
2. Search for similar issues using search_repository_issues.
3. Inspect relevant pull requests and recent commits when useful.
4. Separate verified facts from hypotheses.
5. Link every repository claim to a source URL.
6. If code evidence is unavailable, explicitly say so.
7. Recommend a minimal fix and regression test plan.
8. Do not claim to have tested a fix unless tests were actually run.
"""


if __name__ == "__main__":
    mcp.run()
