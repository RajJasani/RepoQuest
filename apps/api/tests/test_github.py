import httpx
import pytest
import respx

from app.core.errors import GitHubError, NotFoundError, RateLimitedError, ValidationError
from app.services.github import GitHubClient, validate_github_repo_url


def test_url_validator():
    # Valid URLs
    assert validate_github_repo_url("https://github.com/facebook/react") == ("facebook", "react")
    assert validate_github_repo_url("https://github.com/fastapi/fastapi/") == ("fastapi", "fastapi")
    assert validate_github_repo_url("https://github.com/my-org/my_repo.v2") == ("my-org", "my_repo.v2")
    assert validate_github_repo_url("https://github.com/owner/repo.git") == ("owner", "repo")
    assert validate_github_repo_url("  https://github.com/google/gemma-2/  ") == ("google", "gemma-2")

    # Invalid URLs
    invalid_cases = [
        "http://github.com/owner/repo",  # Not https
        "https://gitlab.com/owner/repo",  # Wrong host
        "https://github.com/owner",  # Missing repo
        "https://github.com/owner/repo/pull/1",  # Extra subpaths
        "https://github.com//repo",  # Empty owner
        "not a url",
        "",
        None,
    ]
    for invalid in invalid_cases:
        with pytest.raises(ValidationError):
            validate_github_repo_url(invalid)


@pytest.mark.asyncio
@respx.mock
async def test_github_get_repo_metadata():
    client = GitHubClient(token="ghp_testToken123")

    respx.get("https://api.github.com/repos/octocat/Hello-World").respond(
        status_code=200,
        json={"name": "Hello-World", "owner": {"login": "octocat"}, "stargazers_count": 42},
    )

    repo_data = await client.get_repo("octocat", "Hello-World")
    assert repo_data["name"] == "Hello-World"
    assert repo_data["stargazers_count"] == 42


@pytest.mark.asyncio
@respx.mock
async def test_github_get_open_issues_excludes_pull_requests():
    client = GitHubClient()

    # GitHub issues API returns both issues and PRs (PRs contain 'pull_request' key)
    raw_items = [
        {"number": 1, "title": "Real issue 1", "state": "open"},
        {"number": 2, "title": "PR presented as issue", "state": "open", "pull_request": {"url": "..."}},
        {"number": 3, "title": "Real issue 2", "state": "open"},
    ]

    respx.get("https://api.github.com/repos/owner/repo/issues").respond(
        status_code=200,
        json=raw_items,
    )

    issues = await client.get_open_issues("owner", "repo")
    assert len(issues) == 2
    assert [i["number"] for i in issues] == [1, 3]


@pytest.mark.asyncio
@respx.mock
async def test_github_get_pull_request_diff():
    client = GitHubClient()

    diff_content = "diff --git a/file.py b/file.py\n--- a/file.py\n+++ b/file.py\n@@ -1 +1 @@\n-old\n+new"
    route = respx.get("https://api.github.com/repos/owner/repo/pulls/10").respond(
        status_code=200,
        text=diff_content,
    )

    diff = await client.get_pull_request_diff("owner", "repo", 10)
    assert diff == diff_content
    assert route.calls.last.request.headers.get("accept") == "application/vnd.github.v3.diff"


@pytest.mark.asyncio
@respx.mock
async def test_github_download_tarball():
    client = GitHubClient()
    tarball_bytes = b"\x1f\x8b\x08\x00fake-gzip-data"

    respx.get("https://api.github.com/repos/owner/repo/tarball/main").respond(
        status_code=200,
        content=tarball_bytes,
    )

    downloaded = await client.download_tarball("owner", "repo", "main")
    assert downloaded == tarball_bytes


@pytest.mark.asyncio
@respx.mock
async def test_github_post_comment_and_labels():
    client = GitHubClient(token="ghp_token")

    respx.post("https://api.github.com/repos/owner/repo/issues/5/comments").respond(
        status_code=201,
        json={"id": 100, "body": "Thank you for reporting!"},
    )
    respx.post("https://api.github.com/repos/owner/repo/issues/5/labels").respond(
        status_code=200,
        json=[{"name": "bug"}, {"name": "triage"}],
    )
    respx.delete("https://api.github.com/repos/owner/repo/issues/5/labels/triage").respond(
        status_code=204,
    )

    comment = await client.post_issue_comment("owner", "repo", 5, "Thank you for reporting!")
    assert comment["id"] == 100

    labels = await client.add_labels("owner", "repo", 5, ["bug", "triage"])
    assert len(labels) == 2

    # Should complete without error
    await client.remove_label("owner", "repo", 5, "triage")


@pytest.mark.asyncio
@respx.mock
async def test_github_create_pr_review():
    client = GitHubClient(token="ghp_token")

    comments = [
        {"path": "main.py", "position": 10, "body": "Missing null check here"}
    ]

    respx.post("https://api.github.com/repos/owner/repo/pulls/12/reviews").respond(
        status_code=200,
        json={"id": 999, "state": "COMMENTED", "body": "Review summary"},
    )

    review = await client.create_pull_request_review(
        owner="owner",
        repo="repo",
        pull_number=12,
        body="Review summary",
        event="COMMENT",
        comments=comments,
    )
    assert review["id"] == 999


@pytest.mark.asyncio
@respx.mock
async def test_github_not_found_mapping():
    client = GitHubClient()

    respx.get("https://api.github.com/repos/owner/nonexistent").respond(
        status_code=404,
        json={"message": "Not Found"},
    )

    with pytest.raises(NotFoundError) as exc:
        await client.get_repo("owner", "nonexistent")
    assert exc.value.code == "not_found"


@pytest.mark.asyncio
@respx.mock
async def test_github_backoff_and_retry_after():
    client = GitHubClient(backoff_factor=0.01, max_retries=2)

    # Attempt 1: 429 with Retry-After: 0
    # Attempt 2: 200 OK
    respx.get("https://api.github.com/repos/owner/repo").mock(
        side_effect=[
            httpx.Response(429, headers={"retry-after": "0"}),
            httpx.Response(200, json={"name": "repo"}),
        ]
    )

    data = await client.get_repo("owner", "repo")
    assert data["name"] == "repo"


@pytest.mark.asyncio
@respx.mock
async def test_github_server_error_mapping():
    client = GitHubClient(backoff_factor=0.01, max_retries=1)

    respx.get("https://api.github.com/repos/owner/repo").respond(
        status_code=500,
        text="Internal Server Error",
    )

    with pytest.raises(GitHubError) as exc:
        await client.get_repo("owner", "repo")
    assert exc.value.code == "github_error"


@pytest.mark.asyncio
@respx.mock
async def test_github_rate_limited_exhaustion():
    client = GitHubClient(backoff_factor=0.01, max_retries=1)

    # Always rate limited
    respx.get("https://api.github.com/repos/owner/repo").respond(
        status_code=429,
        headers={"retry-after": "0", "x-ratelimit-remaining": "0"},
    )

    with pytest.raises(RateLimitedError) as exc:
        await client.get_repo("owner", "repo")
    assert exc.value.code == "rate_limited"
