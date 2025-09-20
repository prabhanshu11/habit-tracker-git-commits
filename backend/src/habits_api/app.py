from __future__ import annotations

import datetime as dt
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import Window, get_settings
from .db import Commit, Repository, get_session, init_db, SessionLocal, CommitFile
from .ingest import ingest_all, start_scheduler, ensure_commit_files
from .schemas import CommitOut, RepoMetrics, RepoOut, SummaryOut, SummaryRepo, CommitFileOut, CommitDetail

app = FastAPI(title="Habit Tracker — Git Commits")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _startup():
    await init_db()
    # start scheduler
    start_scheduler(ingest_all, SessionLocal)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/repos", response_model=List[RepoOut])
async def list_repos(session: AsyncSession = Depends(get_session)):
    res = await session.execute(select(Repository))
    repos = res.scalars().all()
    return [
        RepoOut(
            id=r.id,
            full_name=r.full_name,
            default_branch=r.default_branch,
            is_private=r.is_private,
            last_checked_at=r.last_checked_at,
        )
        for r in repos
    ]


@app.post("/admin/ingest")
async def trigger_ingest(session: AsyncSession = Depends(get_session)) -> dict:
    count = await ingest_all(session)
    return {"ingested_new": count}


@app.get("/metrics/summary", response_model=SummaryOut)
async def summary(window: str = Query("24h"), session: AsyncSession = Depends(get_session)):
    w = Window.from_str(window)
    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=w.seconds)

    # per-repo counts
    subq = (
        select(
            Commit.repo_id.label("repo_id"),
            func.count(Commit.id).label("count"),
            func.coalesce(func.sum(Commit.additions + Commit.deletions), 0).label("lines"),
        )
        .where(Commit.committed_at >= since)
        .group_by(Commit.repo_id)
        .subquery()
    )

    res = await session.execute(select(Repository, subq.c.count, subq.c.lines).join(subq, Repository.id == subq.c.repo_id, isouter=True))
    rows = res.all()
    per_repo = []
    total_commits = 0
    total_lines = 0
    repos_updated = 0
    last_checked = None
    for repo, count, lines in rows:
        c = int(count or 0)
        l = int(lines or 0)
        total_commits += c
        total_lines += l
        if c > 0:
            repos_updated += 1
        if not last_checked or (repo.last_checked_at and repo.last_checked_at > last_checked):
            last_checked = repo.last_checked_at
        per_repo.append(SummaryRepo(id=repo.id, full_name=repo.full_name, commits_count=c, is_private=repo.is_private))

    return SummaryOut(
        window=w.value,
        total_commits=total_commits,
        total_lines_updated=total_lines,
        repos_updated_count=repos_updated,
        last_checked_at=last_checked,
        per_repo=per_repo,
    )


@app.get("/repos/{repo_id}/metrics", response_model=RepoMetrics)
async def repo_metrics(repo_id: int, window: str = Query("24h"), session: AsyncSession = Depends(get_session)):
    w = Window.from_str(window)
    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=w.seconds)

    repo = (await session.get(Repository, repo_id))
    if not repo:
        raise HTTPException(404, detail="repo not found")

    res = await session.execute(
        select(
            func.count(Commit.id), func.coalesce(func.sum(Commit.additions), 0), func.coalesce(func.sum(Commit.deletions), 0)
        ).where(Commit.repo_id == repo_id, Commit.committed_at >= since)
    )
    commits, adds, dels = res.one()
    return RepoMetrics(window=w.value, repo_id=repo.id, full_name=repo.full_name, commits_count=int(commits or 0), lines_added=int(adds or 0), lines_deleted=int(dels or 0))


@app.get("/repos/{repo_id}/commits", response_model=List[CommitOut])
async def repo_commits(repo_id: int, window: str = Query("24h"), limit: int = Query(100, ge=1, le=1000), session: AsyncSession = Depends(get_session)):
    w = Window.from_str(window)
    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=w.seconds)
    repo = (await session.get(Repository, repo_id))
    if not repo:
        raise HTTPException(404, detail="repo not found")

    res = await session.execute(
        select(Commit)
        .where(Commit.repo_id == repo_id, Commit.committed_at >= since)
        .order_by(Commit.committed_at.desc())
        .limit(limit)
    )
    commits = res.scalars().all()
    return [
        CommitOut(
            sha=c.sha,
            author_name=c.author_name,
            author_login=c.author_login,
            committed_at=c.committed_at,
            message=c.message,
            additions=c.additions,
            deletions=c.deletions,
            changed_files=c.changed_files,
            url=c.url,
        )
        for c in commits
    ]


@app.get("/repos/{repo_id}/commit/{sha}", response_model=CommitDetail)
async def commit_detail(repo_id: int, sha: str, include_patch: bool = Query(True), session: AsyncSession = Depends(get_session)):
    settings = get_settings()
    repo = await session.get(Repository, repo_id)
    if not repo:
        raise HTTPException(404, detail="repo not found")
    res = await session.execute(select(Commit).where(Commit.repo_id == repo_id, Commit.sha == sha))
    commit = res.scalar_one_or_none()
    if not commit:
        raise HTTPException(404, detail="commit not found")

    # Ensure we have files stored
    await ensure_commit_files(session, repo, commit)

    resf = await session.execute(select(CommitFile).where(CommitFile.commit_id == commit.id))
    files = resf.scalars().all()

    allow_patch = (not repo.is_private) or settings.allow_private_code
    out_files = [
        CommitFileOut(
            path=f.path,
            status=f.status,
            additions=f.additions,
            deletions=f.deletions,
            patch=(f.patch if (allow_patch and include_patch) else None),
        )
        for f in files
    ]

    return CommitDetail(
        sha=commit.sha,
        author_name=commit.author_name,
        author_login=commit.author_login,
        committed_at=commit.committed_at,
        message=commit.message,
        additions=commit.additions,
        deletions=commit.deletions,
        changed_files=commit.changed_files,
        url=commit.url,
        files=out_files,
        repo_id=repo.id,
        full_name=repo.full_name,
        is_private=repo.is_private,
    )
