from __future__ import annotations

import datetime as dt
from typing import AsyncIterator

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.ext.asyncio import AsyncAttrs, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from .config import get_settings


class Base(AsyncAttrs, DeclarativeBase):
    pass


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    default_branch: Mapped[str] = mapped_column(String(128), default="main")
    is_private: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_checked_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=lambda: dt.datetime.now(dt.timezone.utc))
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=lambda: dt.datetime.now(dt.timezone.utc), onupdate=lambda: dt.datetime.now(dt.timezone.utc))

    commits: Mapped[list["Commit"]] = relationship(back_populates="repo", cascade="all, delete-orphan")


class Commit(Base):
    __tablename__ = "commits"
    __table_args__ = (
        UniqueConstraint("repo_id", "sha", name="uq_commits_repo_sha"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repo_id: Mapped[int] = mapped_column(ForeignKey("repositories.id", ondelete="CASCADE"), index=True)
    sha: Mapped[str] = mapped_column(String(64), index=True)
    author_name: Mapped[str | None] = mapped_column(String(200))
    author_login: Mapped[str | None] = mapped_column(String(200))
    committed_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), index=True)
    message: Mapped[str] = mapped_column(Text)
    additions: Mapped[int] = mapped_column(Integer, default=0)
    deletions: Mapped[int] = mapped_column(Integer, default=0)
    changed_files: Mapped[int] = mapped_column(Integer, default=0)
    url: Mapped[str | None] = mapped_column(String(512))

    repo: Mapped[Repository] = relationship(back_populates="commits")


class CommitFile(Base):
    __tablename__ = "commit_files"
    __table_args__ = (
        UniqueConstraint("commit_id", "path", name="uq_commit_files_commit_path"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    commit_id: Mapped[int] = mapped_column(ForeignKey("commits.id", ondelete="CASCADE"), index=True)
    path: Mapped[str] = mapped_column(String(1024))
    status: Mapped[str | None] = mapped_column(String(32))
    additions: Mapped[int] = mapped_column(Integer, default=0)
    deletions: Mapped[int] = mapped_column(Integer, default=0)
    patch: Mapped[str | None] = mapped_column(Text)

    commit: Mapped[Commit] = relationship()


settings = get_settings()
engine = create_async_engine(settings.database_url, echo=False, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
