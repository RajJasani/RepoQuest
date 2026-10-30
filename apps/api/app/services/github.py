from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Optional

import httpx

from app.core.errors import GitHubError, NotFoundError, RateLimitedError, ValidationError

logger = logging.getLogger("app.services.github")

# Section 11 regex: repo URL must match ^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/?$
REPO_URL_REGEX = re.compile(r"^https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/?$")


def validate_github_repo_url(url: str) -> tuple[str, str]:
    """
    Validates a repository URL against PRD §11 rules.
    Returns (owner, repo) tuple or raises ValidationError.
    """
    if not url or not isinstance(url, str):
        raise ValidationError("Repository URL must be a non-empty string", details={"url": url})

    cleaned = url.strip()
    match = REPO_URL_REGEX.match(cleaned)
    if not match:
        raise ValidationError(
            "Invalid GitHub repository URL. Must match format https://github.com/owner/repo",
            details={"url": cleaned},
        )

    owner, repo = match.groups()
    if repo.endswith(".git"):
        repo = repo[:-4]
    return owner, repo


class GitHubClient:
    """
    HTTP client for api.github.com with exponential backoff and rate limit handling.
    This is the only module allowed to call api.github.com.
    """

    def __init__(
        self,
        token: Optional[str] = None,
        base_url: str = "https://api.github.com",
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        client: Optional[httpx.AsyncClient] = None,
    ):
        self.token = token.strip() if token else None
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self._external_client = client

    def _build_headers(self, custom_accept: Optional[str] = None) -> dict[str, str]:
        headers = {
            "Accept": custom_accept or "application/vnd.github+json",
            "User-Agent": "RepoQuest-App",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict[str, Any]] = None,
        json: Optional[Any] = None,
        custom_accept: Optional[str] = None,
        follow_redirects: bool = True,
    ) -> httpx.Response:
        url = f"{self.base_url}/{path.lstrip('/')}"
        headers = self._build_headers(custom_accept)

        attempt = 0
        last_exception: Optional[Exception] = None

        while attempt <= self.max_retries:
            try:
                client = self._external_client or httpx.AsyncClient(timeout=30.0, follow_redirects=follow_redirects)
                try:
                    response = await client.request(
                        method=method,
                        url=url,
                        headers=headers,
                        params=params,
                        json=json,
                    )
                finally:
                    if self._external_client is None:
                        await client.aclose()

                # Check rate limiting
                remaining = response.headers.get("x-ratelimit-remaining")
                retry_after = response.headers.get("retry-after")

                is_rate_limited = response.status_code == 429 or (
                    response.status_code == 403 and remaining == "0"
                )

                if is_rate_limited:
                    wait_sec = float(retry_after) if retry_after and retry_after.isdigit() else (self.backoff_factor * (2**attempt))
                    logger.warning(
                        "GitHub rate limit hit on %s %s. Attempt %d/%d. Waiting %.2fs",
                        method,
                        url,
                        attempt + 1,
                        self.max_retries,
                        wait_sec,
                    )
                    if attempt < self.max_retries:
                        await asyncio.sleep(wait_sec)
                        attempt += 1
                        continue
                    raise RateLimitedError(
                        message="GitHub API rate limit exceeded",
                        details={"url": url, "remaining": remaining, "retry_after": retry_after},
                    )

                if response.status_code == 404:
                    raise NotFoundError(
                        message=f"GitHub resource not found at {path}",
                        details={"url": url, "status_code": 404},
                    )

                if 500 <= response.status_code < 600:
                    if attempt < self.max_retries:
                        wait_sec = self.backoff_factor * (2**attempt)
                        await asyncio.sleep(wait_sec)
                        attempt += 1
                        continue
                    raise GitHubError(
                        message=f"GitHub server error: {response.status_code}",
                        details={"url": url, "status_code": response.status_code},
                    )

                if response.status_code >= 400:
                    error_msg = "GitHub API error"
                    try:
                        err_data = response.json()
                        error_msg = err_data.get("message", error_msg)
                    except Exception:
                        pass
                    raise GitHubError(
                        message=f"GitHub API error: {error_msg}",
                        details={"url": url, "status_code": response.status_code},
                    )

                return response

            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
                last_exception = exc
                if attempt < self.max_retries:
                    wait_sec = self.backoff_factor * (2**attempt)
                    await asyncio.sleep(wait_sec)
                    attempt += 1
                    continue
                raise GitHubError(
                    message=f"Failed to connect to GitHub API: {exc}",
                    details={"url": url},
                ) from exc

        if last_exception:
            raise GitHubError(f"GitHub request failed after retries: {last_exception}")
        raise GitHubError("GitHub request failed")

    async def get_repo(self, owner: str, repo: str) -> dict[str, Any]:
        """Fetches repository metadata."""
        res = await self._request("GET", f"/repos/{owner}/{repo}")
        return res.json()

    async def get_labels(self, owner: str, repo: str) -> list[dict[str, Any]]:
        """Fetches allowed repository labels."""
        res = await self._request("GET", f"/repos/{owner}/{repo}/labels", params={"per_page": 100})
        return res.json()

    async def get_open_issues(self, owner: str, repo: str) -> list[dict[str, Any]]:
        """Fetches open issues (strictly excluding pull requests)."""
        res = await self._request(
            "GET",
            f"/repos/{owner}/{repo}/issues",
            params={"state": "open", "per_page": 100},
        )
        issues = res.json()
        # GitHub's issues endpoint returns PRs as issues; exclude them!
        return [issue for issue in issues if "pull_request" not in issue]

    async def get_open_pull_requests(self, owner: str, repo: str) -> list[dict[str, Any]]:
        """Fetches open pull requests."""
        res = await self._request(
            "GET",
            f"/repos/{owner}/{repo}/pulls",
            params={"state": "open", "per_page": 100},
        )
        return res.json()

    async def get_pull_request_files(self, owner: str, repo: str, pull_number: int) -> list[dict[str, Any]]:
        """Fetches the list of files modified in a pull request."""
        res = await self._request(
            "GET",
            f"/repos/{owner}/{repo}/pulls/{pull_number}/files",
            params={"per_page": 100},
        )
        return res.json()

    async def get_pull_request_diff(self, owner: str, repo: str, pull_number: int) -> str:
        """Fetches raw diff text for a pull request."""
        res = await self._request(
            "GET",
            f"/repos/{owner}/{repo}/pulls/{pull_number}",
            custom_accept="application/vnd.github.v3.diff",
        )
        return res.text

    async def download_tarball(self, owner: str, repo: str, ref: str = "main") -> bytes:
        """Downloads tarball snapshot of the repository at the given branch or commit ref."""
        res = await self._request("GET", f"/repos/{owner}/{repo}/tarball/{ref}", follow_redirects=True)
        return res.content

    async def post_issue_comment(self, owner: str, repo: str, issue_number: int, body: str) -> dict[str, Any]:
        """Posts a comment on an issue or PR."""
        res = await self._request("POST", f"/repos/{owner}/{repo}/issues/{issue_number}/comments", json={"body": body})
        return res.json()

    async def add_labels(self, owner: str, repo: str, issue_number: int, labels: list[str]) -> list[dict[str, Any]]:
        """Adds labels to an issue or PR."""
        res = await self._request("POST", f"/repos/{owner}/{repo}/issues/{issue_number}/labels", json={"labels": labels})
        return res.json()

    async def remove_label(self, owner: str, repo: str, issue_number: int, label_name: str) -> None:
        """Removes a label from an issue or PR."""
        await self._request("DELETE", f"/repos/{owner}/{repo}/issues/{issue_number}/labels/{label_name}")

    async def create_pull_request_review(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        body: str,
        event: str = "COMMENT",
        comments: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """Creates a PR review with summary and inline file comments."""
        payload: dict[str, Any] = {
            "body": body,
            "event": event,
        }
        if comments:
            payload["comments"] = comments

        res = await self._request("POST", f"/repos/{owner}/{repo}/pulls/{pull_number}/reviews", json=payload)
        return res.json()

    async def verify_token(self) -> dict[str, Any]:
        """Verifies the token against the authenticated user endpoint."""
        res = await self._request("GET", "/user")
        return res.json()


async def verify_github_token(token: str, client: Optional[httpx.AsyncClient] = None) -> dict[str, Any]:
    """Standalone helper to verify a GitHub personal access token."""
    gh = GitHubClient(token=token, client=client)
    return await gh.verify_token()
