import pytest
import respx
from httpx import Response

from habits_api.github import fetch_commit_files, split_repo


def test_split_repo():
    owner, name = split_repo("openai/codex")
    assert owner == "openai"
    assert name == "codex"


@pytest.mark.anyio
async def test_fetch_commit_files_rest():
    full = "alice/project"
    sha = "abc123"
    url = f"https://api.github.com/repos/alice/project/commits/{sha}"
    payload = {
        "sha": sha,
        "stats": {"additions": 10, "deletions": 4, "total": 14},
        "files": [
            {"filename": "README.md", "status": "modified", "additions": 5, "deletions": 2, "patch": "@@ -1 +1 @@"},
            {"filename": "app.py", "status": "added", "additions": 5, "deletions": 2, "patch": "@@ -0 +1 @@"},
        ],
    }
    with respx.mock(assert_all_called=True) as rsx:
        rsx.get(url).mock(return_value=Response(200, json=payload))
        data = await fetch_commit_files(full, sha)

    assert "files" in data
    assert len(data["files"]) == 2
    assert data["files"][0]["path"] == "README.md"
    assert data["files"][0]["status"] == "modified"
    assert data["files"][0]["additions"] == 5
    assert data["files"][0]["deletions"] == 2
    assert data["files"][0]["patch"].startswith("@@")
