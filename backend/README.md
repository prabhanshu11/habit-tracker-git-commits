# Habit Tracker — Backend (FastAPI)

Local API to ingest GitHub commit history for selected repositories and serve summary metrics.

## Quick Start

fish shell with uv is recommended.

- cd backend
- uv sync
- Copy `../.env.example` to `../.env` and fill values (at least `GITHUB_TOKEN` and `REPO_ALLOWLIST`).
- Run API: `PYTHONPATH=src uv run uvicorn habits_api.app:app --reload --port 8081`
- Trigger ingestion once (in another terminal): `curl -X POST http://127.0.0.1:8081/admin/ingest`
- Open docs: http://127.0.0.1:8081/docs

## Env Vars

- `GITHUB_TOKEN` — GitHub PAT or App token with `repo` scope (private read if needed)
- `REPO_ALLOWLIST` — comma-separated list like `owner1/repo1,owner2/repo2` or `ALL` to track all repos visible to the token
- `DATABASE_URL` — optional; default `sqlite+aiosqlite:///./data.db`
- `PUBLIC_VIEW_TOKEN` — optional; include as query `?token=...` when set
- `ALLOW_PRIVATE_CODE` — `true/false` for serving code content (default false)

## Endpoints

- `GET /health` — health check
- `GET /repos` — list repositories
- `GET /metrics/summary?window=24h` — aggregate across repos
- `GET /repos/{id}/metrics?window=24h` — per-repo metric summary
- `GET /repos/{id}/commits?window=24h&limit=100` — commit list
- `POST /admin/ingest` — run ingestion now

## Notes

- Scheduler runs every 15 minutes by default.
- Ingestion uses GitHub GraphQL for commit history (fast) and avoids diffs content to keep requests light.
- Tables are created automatically on startup.
