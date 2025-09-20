from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

import httpx

from .config import get_settings


GQL_URL = "https://api.github.com/graphql"


def _auth_headers(token: Optional[str]) -> Dict[str, str]:
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def split_repo(full_name: str) -> Tuple[str, str]:
    owner, name = full_name.split("/", 1)
    return owner, name


async def fetch_commits_since(full_name: str, since: dt.datetime) -> Dict[str, Any]:
    """Fetch commit history on the default branch since timestamp via GitHub GraphQL.

    Returns a dict with keys: default_branch, is_private, commits: [ ... ].
    Each commit includes oid, committedDate, message, author, additions, deletions, changedFiles, url.
    """
    settings = get_settings()
    owner, name = split_repo(full_name)

    query = """
    query($owner:String!, $name:String!, $since:GitTimestamp!) {
      repository(owner:$owner, name:$name) {
        isPrivate
        nameWithOwner
        defaultBranchRef {
          name
          target {
            ... on Commit {
              history(since:$since, first: 100) {
                nodes {
                  oid
                  committedDate
                  message
                  additions
                  deletions
                  changedFiles
                  url
                  author {
                    name
                    user { login }
                  }
                }
              }
            }
          }
        }
      }
      rateLimit { remaining resetAt }
    }
    """

    variables = {
        "owner": owner,
        "name": name,
        "since": since.isoformat(),
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(GQL_URL, json={"query": query, "variables": variables}, headers=_auth_headers(settings.github_token))
        resp.raise_for_status()
        data = resp.json()
        if "errors" in data:
            raise RuntimeError(f"GitHub GraphQL error: {data['errors']}")

    repo = data["data"]["repository"]
    default_branch = repo["defaultBranchRef"]["name"] if repo and repo.get("defaultBranchRef") else "main"
    nodes = repo["defaultBranchRef"]["target"]["history"]["nodes"] if repo and repo.get("defaultBranchRef") else []

    commits = []
    for n in nodes:
        commits.append(
            {
                "sha": n["oid"],
                "committed_at": n["committedDate"],
                "message": n.get("message", ""),
                "author_name": (n.get("author") or {}).get("name"),
                "author_login": ((n.get("author") or {}).get("user") or {}).get("login"),
                "additions": n.get("additions", 0),
                "deletions": n.get("deletions", 0),
                "changed_files": n.get("changedFiles", 0),
                "url": n.get("url"),
            }
        )

    return {
        "default_branch": default_branch,
        "is_private": bool(repo.get("isPrivate")) if repo else False,
        "commits": commits,
    }


async def list_viewer_repositories() -> List[Dict[str, Any]]:
    """Return all repositories visible to the token's user with minimal fields.

    Each dict: {full_name, default_branch, is_private}
    """
    settings = get_settings()
    query = """
    query($cursor:String) {
      viewer {
        repositories(
          first: 100,
          after: $cursor,
          affiliations: [OWNER, COLLABORATOR, ORGANIZATION_MEMBER],
          orderBy: {field: UPDATED_AT, direction: DESC}
        ) {
          pageInfo { hasNextPage endCursor }
          nodes {
            nameWithOwner
            isPrivate
            defaultBranchRef { name }
          }
        }
      }
    }
    """
    repos: List[Dict[str, Any]] = []
    cursor: Optional[str] = None
    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            payload = {"query": query, "variables": {"cursor": cursor}}
            resp = await client.post(GQL_URL, json=payload, headers=_auth_headers(settings.github_token))
            resp.raise_for_status()
            data = resp.json()
            if "errors" in data:
                raise RuntimeError(f"GitHub GraphQL error: {data['errors']}")
            repo_conn = data["data"]["viewer"]["repositories"]
            for n in repo_conn["nodes"]:
                repos.append(
                    {
                        "full_name": n["nameWithOwner"],
                        "default_branch": (n.get("defaultBranchRef") or {}).get("name") or "main",
                        "is_private": bool(n.get("isPrivate")),
                    }
                )
            if not repo_conn["pageInfo"]["hasNextPage"]:
                break
            cursor = repo_conn["pageInfo"]["endCursor"]
    return repos
