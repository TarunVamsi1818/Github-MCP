
import re
from typing import Any

import httpx

from repo_intelligence.config import get_settings

_REPO_PART = re.compile(r"^[A-Za-z0-9_.-]+$")


class GitHubAPIError(RuntimeError):
    """A GitHub API request failed."""


def validate_repo(owner: str, repo: str) -> None:
    for value in (owner, repo):
        if (
            not value
            or value in {".", ".."}
            or not _REPO_PART.fullmatch(value)
        ):
            raise ValueError("Invalid GitHub owner or repository name")


class GitHubClient:
    def __init__(self) -> None:
        settings = get_settings()
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        if settings.github_token:
            headers["Authorization"] = f"Bearer {settings.github_token}"

        self._client = httpx.AsyncClient(
            base_url=str(settings.github_api_base_url).rstrip("/"),
            headers=headers,
            timeout=settings.request_timeout_seconds,
            follow_redirects=False,
        )
        self._max_results = settings.max_search_results

    async def close(self) -> None:
        await self._client.aclose()

    async def _get(
        self, path: str, params: dict[str, Any] | None = None
    ) -> Any:
        try:
            response = await self._client.get(path, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status == 401:
                message = "GitHub authentication failed. Check GITHUB_TOKEN."
            elif status == 403 or status == 429:
                message = "GitHub rate limit or access restriction reached."
            elif status == 404:
                message = (
                    "GitHub resource not found or inaccessible. "
                    "Check the repository and token permissions."
                )
            else:
                message = f"GitHub returned HTTP {status}."
            raise GitHubAPIError(message) from exc
        except httpx.RequestError as exc:
            raise GitHubAPIError(
                f"GitHub request failed: {type(exc).__name__}"
            ) from exc

    async def search_issues(
        self, owner: str, repo: str, query: str, limit: int = 10
    ) -> dict[str, Any]:
        validate_repo(owner, repo)

        if not query.strip():
            raise ValueError("Search query must not be empty")
        if not 1 <= limit <= self._max_results:
            raise ValueError(
                f"limit must be between 1 and {self._max_results}"
            )

        data = await self._get(
            "/search/issues",
            params={
                "q": f"repo:{owner}/{repo} is:issue {query}",
                "per_page": limit,
                "page": 1,
            },
        )

        items = [
            {
                "number": item["number"],
                "title": item["title"],
                "state": item["state"],
                "url": item["html_url"],
                "created_at": item["created_at"],
                "updated_at": item["updated_at"],
                "labels": [
                    label["name"] for label in item.get("labels", [])
                ],
                "body": (item.get("body") or "")[:4000],
            }
            for item in data.get("items", [])
            if "pull_request" not in item
        ]

        return {
            "repository": f"{owner}/{repo}",
            "query": query,
            "total_count": data.get("total_count", 0),
            "incomplete_results": data.get("incomplete_results", False),
            "items": items,
        }

    async def get_issue(
        self, owner: str, repo: str, issue_number: int
    ) -> dict[str, Any]:
        validate_repo(owner, repo)
        if issue_number < 1:
            raise ValueError("issue_number must be positive")

        item = await self._get(
            f"/repos/{owner}/{repo}/issues/{issue_number}"
        )

        if "pull_request" in item:
            raise ValueError(
                f"#{issue_number} is a pull request, not a regular issue"
            )

        return {
            "repository": f"{owner}/{repo}",
            "number": item["number"],
            "title": item["title"],
            "state": item["state"],
            "body": (item.get("body") or "")[:8000],
            "url": item["html_url"],
            "created_at": item["created_at"],
            "updated_at": item["updated_at"],
            "labels": [
                label["name"] for label in item.get("labels", [])
            ],
            "comments_url": item["comments_url"],
        }

    async def list_pull_requests(
        self, owner: str, repo: str, state: str = "all", limit: int = 10
    ) -> dict[str, Any]:
        validate_repo(owner, repo)
        if state not in {"open", "closed", "all"}:
            raise ValueError("state must be open, closed, or all")
        if not 1 <= limit <= self._max_results:
            raise ValueError(
                f"limit must be between 1 and {self._max_results}"
            )

        items = await self._get(
            f"/repos/{owner}/{repo}/pulls",
            params={"state": state, "per_page": limit, "page": 1},
        )

        return {
            "repository": f"{owner}/{repo}",
            "state": state,
            "items": [
                {
                    "number": item["number"],
                    "title": item["title"],
                    "state": item["state"],
                    "url": item["html_url"],
                    "head_sha": item["head"]["sha"],
                    "base_ref": item["base"]["ref"],
                    "head_ref": item["head"]["ref"],
                }
                for item in items
            ],
        }

    async def list_commits(
        self, owner: str, repo: str, limit: int = 10
    ) -> dict[str, Any]:
        validate_repo(owner, repo)
        if not 1 <= limit <= self._max_results:
            raise ValueError(
                f"limit must be between 1 and {self._max_results}"
            )

        items = await self._get(
            f"/repos/{owner}/{repo}/commits",
            params={"per_page": limit, "page": 1},
        )

        return {
            "repository": f"{owner}/{repo}",
            "items": [
                {
                    "sha": item["sha"],
                    "message": item["commit"]["message"][:1000],
                    "author": (
                        item["commit"].get("author") or {}
                    ).get("name"),
                    "date": (
                        item["commit"].get("author") or {}
                    ).get("date"),
                    "url": item["html_url"],
                }
                for item in items
            ],
        }
