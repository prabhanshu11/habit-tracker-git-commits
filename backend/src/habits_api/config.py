from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", env_file_encoding="utf-8", extra="ignore")

    github_token: Optional[str] = Field(default=None, alias="GITHUB_TOKEN")
    repo_allowlist: str = Field(default="", alias="REPO_ALLOWLIST")
    database_url: str = Field(default="sqlite+aiosqlite:///./data.db", alias="DATABASE_URL")
    public_view_token: Optional[str] = Field(default=None, alias="PUBLIC_VIEW_TOKEN")
    allow_private_code: bool = Field(default=False, alias="ALLOW_PRIVATE_CODE")
    scheduler_enabled: bool = Field(default=True, alias="SCHEDULER_ENABLED")
    scheduler_interval_minutes: int = Field(default=15, alias="SCHEDULER_INTERVAL_MINUTES")

    @property
    def repo_list(self) -> List[str]:
        parts = [p.strip() for p in self.repo_allowlist.split(",") if p.strip()]
        return list(dict.fromkeys(parts))

    @property
    def track_all(self) -> bool:
        parts = {p.upper() for p in self.repo_list}
        return (not parts) or ("ALL" in parts)


@lru_cache()
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


class Window(BaseModel):
    value: str
    seconds: int

    @staticmethod
    def from_str(s: str) -> "Window":
        mapping = {
            "6h": 6 * 60 * 60,
            "24h": 24 * 60 * 60,
            "7d": 7 * 24 * 60 * 60,
        }
        if s not in mapping:
            s = "24h"
        return Window(value=s, seconds=mapping[s])
