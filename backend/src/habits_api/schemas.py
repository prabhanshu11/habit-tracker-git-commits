from __future__ import annotations

import datetime as dt
from typing import List, Optional

from pydantic import BaseModel


class RepoOut(BaseModel):
    id: int
    full_name: str
    default_branch: str
    is_private: bool
    last_checked_at: dt.datetime | None


class SummaryRepo(BaseModel):
    id: int
    full_name: str
    commits_count: int
    is_private: bool


class SummaryOut(BaseModel):
    window: str
    total_commits: int
    last_checked_at: dt.datetime | None
    per_repo: List[SummaryRepo]


class RepoMetrics(BaseModel):
    window: str
    repo_id: int
    full_name: str
    commits_count: int
    lines_added: int
    lines_deleted: int


class CommitOut(BaseModel):
    sha: str
    author_name: Optional[str]
    author_login: Optional[str]
    committed_at: dt.datetime
    message: str
    additions: int
    deletions: int
    changed_files: int
    url: Optional[str]
