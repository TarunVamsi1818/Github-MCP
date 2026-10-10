
import httpx
import pytest
import respx

from repo_intelligence.github_client import (
    GitHubAPIError,
    GitHubClient,
    validate_repo,
)


@pytest.mark.asyncio
@respx.mock
async def test_search_issues_returns_source_urls():
    route = respx.get(
        "https://api.github.com/search/issues"
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "total_count": 1,
                "incomplete_results": False,
                "items": [
                    {
                        "number": 42,
                        "title": "SHA256 regression",
                        "state": "open",
                        "html_url": "https://github.com/example/repo/issues/42",
                        "created_at": "2026-01-01T00:00:00Z",
                        "updated_at": "2026-01-02T00:00:00Z",
                        "labels": [{"name": "bug"}],
                        "body": "Example description",
                    }
                ],
            },
        )
    )

    client = GitHubClient()
    try:
        result = await client.search_issues(
            "example", "repo", "SHA256 is:open", 10
        )
    finally:
        await client.close()

    assert route.called
    assert result["total_count"] == 1
    assert result["items"][0]["number"] == 42
    assert result["items"][0]["labels"] == ["bug"]
    assert result["items"][0]["url"].endswith("/issues/42")


def test_rejects_invalid_repository_names():
    with pytest.raises(ValueError):
        validate_repo("../owner", "repo")


@pytest.mark.asyncio
@respx.mock
async def test_github_404_is_reported_safely():
    respx.get(
        "https://api.github.com/repos/example/repo/issues/999"
    ).mock(return_value=httpx.Response(404, json={}))

    client = GitHubClient()
    try:
        with pytest.raises(GitHubAPIError, match="not found"):
            await client.get_issue("example", "repo", 999)
    finally:
        await client.close()
