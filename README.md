# Repo Intelligence MCP

Repo Intelligence MCP is a read-only [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
server for evidence-based investigations of GitHub repositories. It retrieves GitHub issues,
pull requests, and recent commits, and returns source links so findings can be checked against
their original records.

## Features

- Search regular repository issues with GitHub search qualifiers such as `is:open`, `is:closed`,
  and `label:bug`. Pull requests are excluded from issue search results.
- Retrieve an issue by number.
- List pull requests by state (`open`, `closed`, or `all`).
- List recent commits with commit messages, authors, dates, and links.
- Build an evidence bundle for an issue with related-issue candidates, recent
  pull requests, and recent commits.
- Expose a capabilities resource and an `investigate_issue` prompt for evidence-driven workflows.

The server does not change repositories, merge pull requests, or determine root cause. Treat
retrieved issue and commit records as evidence, and clearly label any further conclusions as
interpretation.

## Requirements

- Python 3.12 or newer
- A GitHub token is optional for public repositories. Authentication is recommended to increase
  API rate limits and is needed for repositories the token must access.

## Install

From the project directory, create and activate a virtual environment, then install the project:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

The development extra includes the test and lint tools.

## Configure

The included [VS Code MCP configuration](.vscode/mcp.json) starts the server with the current
workspace virtual environment and prompts for a GitHub token. Open the project in VS Code and
provide the token when prompted.

For other MCP clients, run the server with the project installed in the active environment:

```powershell
python -m repo_intelligence.server
```

The server reads these optional settings from environment variables or a `.env` file in the
working directory:

| Variable | Default | Description |
| --- | --- | --- |
| `GITHUB_TOKEN` | unset | GitHub personal access token |
| `GITHUB_API_BASE_URL` | `https://api.github.com` | GitHub API base URL |
| `REQUEST_TIMEOUT_SECONDS` | `20` | HTTP request timeout; must be greater than 0 and at most 120 |
| `MAX_SEARCH_RESULTS` | `10` | Maximum results requested per tool call; must be between 1 and 30 |

See [.env-example](.env-example) for a template. Keep credentials in your local `.env`; it is
excluded from Git.

## Available MCP tools

| Tool | Purpose |
| --- | --- |
| `search_repository_issues(owner, repo, query, limit=10)` | Search regular issues and return matching records with source URLs |
| `get_repository_issue(owner, repo, issue_number)` | Retrieve a regular issue by number |
| `list_repository_pull_requests(owner, repo, state="all", limit=10)` | List pull requests and their branches and head SHAs |
| `list_recent_repository_commits(owner, repo, limit=10)` | List recent commits and their source URLs |
| `investigate_repository_issue(owner, repo, issue_number)` | Retrieve an issue and gather related issue candidates, recent pull requests, and recent commits |

For example, search open issues mentioning SHA256 with:

```text
owner = "bcgit"
repo = "bc-java"
query = "SHA256 is:open"
limit = 10
```

The `limit` is constrained by `MAX_SEARCH_RESULTS`. Search results come from the first GitHub
Search API page; the server does not automatically paginate through all matches. The issue-detail
tool returns issue details and a comments URL, but does not fetch comments.

### Issue investigation evidence bundle

`investigate_repository_issue` retrieves the specified regular issue, searches for up to five
related issue candidates using distinctive words from its title, and lists up to five repository
pull requests and five recent commits. Related issues are search candidates, not confirmed
duplicates or causal explanations. Pull requests and commits are recent repository-wide results;
they are not guaranteed to be associated with the issue.

The result has a `status` of `complete`, `partial`, or `failed`. If the target issue cannot be
retrieved, the result is `failed`; if a supporting lookup fails after the issue is retrieved, the
result is `partial` and includes per-step errors. Successful reports set
`conclusions.verified_root_cause` to `null` and list evidence limitations. The tool does not
inspect source code or run tests, and a matching title or commit message is not proof that a
change fixed the issue.

The `repo-intelligence://capabilities` resource describes the server's scope. The
`investigate_issue` prompt provides a reusable checklist for researching an issue while separating
verified facts from hypotheses.

## Development

Run the test suite and linter from the project root:

```powershell
pytest
ruff check .
```
