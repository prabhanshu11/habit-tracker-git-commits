from __future__ import annotations

import datetime as dt
import logging
from typing import Iterable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from .config import Window, get_settings
from .db import Commit, Repository, CommitFile
from .github import fetch_commits_since, list_viewer_repositories, fetch_commit_files

log = logging.getLogger(__name__)


async def ensure_allowlisted_repos(session: AsyncSession) -> None:
    settings = get_settings()
    names: list[str]
    meta: dict[str, dict] = {}
    if settings.track_all:
        # Query all repos for viewer
        repos = await list_viewer_repositories()
        names = [r["full_name"] for r in repos]
        meta = {r["full_name"]: r for r in repos}
    else:
        names = settings.repo_list

    for full in names:
        if not full:
            continue
        res = await session.execute(select(Repository).where(Repository.full_name == full))
        repo = res.scalar_one_or_none()
        if repo is None:
            defaults = meta.get(full, {})
            repo = Repository(
                full_name=full,
                default_branch=defaults.get("default_branch", "main"),
                is_private=bool(defaults.get("is_private", False)),
            )
            session.add(repo)
        else:
            if full in meta:
                repo.default_branch = meta[full].get("default_branch", repo.default_branch)
                repo.is_private = bool(meta[full].get("is_private", repo.is_private))
    await session.commit()


async def ingest_repo(session: AsyncSession, repo: Repository) -> int:
    now = dt.datetime.now(dt.timezone.utc)
    since = repo.last_checked_at or (now - dt.timedelta(hours=24))

    try:
        payload = await fetch_commits_since(repo.full_name, since)
    except Exception as e:
        log.exception("Ingestion failed for %s: %s", repo.full_name, e)
        return 0

    repo.default_branch = payload.get("default_branch", repo.default_branch)
    # repo.is_private may update but we keep existing if not provided
    repo.is_private = bool(payload.get("is_private", repo.is_private))

    new = 0
    for c in payload.get("commits", []):
        committed_at = dt.datetime.fromisoformat(c["committed_at"].replace("Z", "+00:00"))
        # Upsert by (repo_id, sha)
        exists = await session.execute(
            select(func.count(Commit.id)).where(Commit.repo_id == repo.id, Commit.sha == c["sha"])  # type: ignore[arg-type]
        )
        if exists.scalar_one() == 0:
            commit = Commit(
                repo_id=repo.id,  # type: ignore[arg-type]
                sha=c["sha"],
                author_name=c.get("author_name"),
                author_login=c.get("author_login"),
                committed_at=committed_at,
                message=c.get("message", ""),
                additions=int(c.get("additions", 0)),
                deletions=int(c.get("deletions", 0)),
                changed_files=int(c.get("changed_files", 0)),
                url=c.get("url"),
            )
            session.add(commit)
            await session.flush()  # assign commit.id

            # Fetch and persist per-file changes (REST)
            try:
                files_payload = await fetch_commit_files(repo.full_name, commit.sha)
                for f in files_payload.get("files", []):
                    session.add(
                        CommitFile(
                            commit_id=commit.id,  # type: ignore[arg-type]
                            path=f.get("path") or "",
                            status=f.get("status"),
                            additions=int(f.get("additions", 0)),
                            deletions=int(f.get("deletions", 0)),
                            patch=f.get("patch"),
                        )
                    )
            except Exception as e:
                log.exception("Failed to fetch files for %s@%s: %s", repo.full_name, commit.sha, e)

            new += 1

    repo.last_checked_at = now
    await session.commit()
    log.info("Ingested %s: %s new commits", repo.full_name, new)
    return new


async def ingest_all(session: AsyncSession) -> int:
    await ensure_allowlisted_repos(session)
    res = await session.execute(select(Repository).where(Repository.enabled == True))  # noqa: E712
    repos = res.scalars().all()
    count = 0
    for r in repos:
        count += await ingest_repo(session, r)
    return count


async def ensure_commit_files(session: AsyncSession, repo: Repository, commit: Commit) -> int:
    """Ensure CommitFile rows exist for the given commit; fetch if missing.

    Returns the number of files added.
    """
    res = await session.execute(select(func.count(CommitFile.id)).where(CommitFile.commit_id == commit.id))
    if int(res.scalar_one() or 0) > 0:
        return 0
    try:
        payload = await fetch_commit_files(repo.full_name, commit.sha)
        added = 0
        for f in payload.get("files", []):
            session.add(
                CommitFile(
                    commit_id=commit.id,  # type: ignore[arg-type]
                    path=f.get("path") or "",
                    status=f.get("status"),
                    additions=int(f.get("additions", 0)),
                    deletions=int(f.get("deletions", 0)),
                    patch=f.get("patch"),
                )
            )
            added += 1
        await session.commit()
        return added
    except Exception as e:
        log.exception("ensure_commit_files failed for %s@%s: %s", repo.full_name, commit.sha, e)
        return 0


def start_scheduler(job_func, session_factory) -> AsyncIOScheduler:
    settings = get_settings()
    sched = AsyncIOScheduler()

    async def _runner():
        async with session_factory() as session:
            await job_func(session)

    if settings.scheduler_enabled:
        sched.add_job(_runner, "interval", minutes=settings.scheduler_interval_minutes, id="ingest")
        sched.start()
    return sched
