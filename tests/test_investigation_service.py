
import pytest

from repo_intelligence.services.investigation_service import (
    build_issue_investigation,
)


class FakeGitHubClient:
    async def get_issue(self, owner, repo, issue_number):
        return {
            "number": issue_number,
            "title": "SHA256 validation regression",
            "state": "open",
            "url": f"https://github.com/{owner}/{repo}/issues/{issue_number}",
        }

    async def search_issues(self, owner, repo, query, limit=10):
        return {
            "total_count": 2,
            "items": [
                {"number": 42, "title": "SHA256 validation regression"},
                {"number": 43, "title": "SHA256 edge case"},
            ],
        }

    async def list_pull_requests(self, owner, repo, state="all", limit=10):
        return {"items": [{"number": 50, "title": "Validation fix"}]}

    async def list_commits(self, owner, repo, limit=10):
        return {"items": [{"sha": "abc123", "message": "Improve validation"}]}


@pytest.mark.asyncio
async def test_builds_investigation_report():
    report = await build_issue_investigation(
        FakeGitHubClient(), "example", "repo", 42
    )

    assert report["status"] == "complete"
    assert report["issue"]["number"] == 42
    assert all(
        item["number"] != 42
        for item in report["related_issues"]["items"]
    )
    assert report["pull_requests"]["items"]
    assert report["recent_commits"]["items"]
    assert report["conclusions"]["verified_root_cause"] is None


class MissingIssueClient(FakeGitHubClient):
    async def get_issue(self, owner, repo, issue_number):
        from repo_intelligence.github_client import GitHubAPIError
        raise GitHubAPIError("GitHub resource not found")


@pytest.mark.asyncio
async def test_missing_issue_returns_failed_report():
    report = await build_issue_investigation(
        MissingIssueClient(), "example", "repo", 999
    )

    assert report["status"] == "failed"
    assert report["issue"] is None
    assert report["errors"][0]["step"] == "get_issue"
