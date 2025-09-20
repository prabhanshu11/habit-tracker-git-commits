# Habit Tracker — Git Commits

Track daily commit activity across your GitHub repositories with a playful, retro UI. This repo currently contains planning docs and design references. See `prompts/technical_prompt.md` for the full build spec the developer AI should implement.

## Status
- Planning: complete first-pass spec and visual references
- Code: not yet scaffolded (backend and web to be created per spec)

## Purpose
- Primary metric: number of commits in the last 24 hours and since the last server-side check.
- Secondary metrics: lines added/removed per commit, changed files, and code view for public repos.
- Share read-only metrics publicly without requiring viewer login.

## Structure (intended)
- `backend/` FastAPI + scheduler (Python, uv)
- `web/` Next.js UI (TypeScript)
- `prompts/` Design screenshots and the technical prompt

## Run Locally
- Backend (fish, via uv):
  - `cd backend`
  - `uv sync`
  - Copy `.env.example` (at repo root) to `.env`, set `GITHUB_TOKEN` and `REPO_ALLOWLIST`.
  - `PYTHONPATH=backend/src uv run uvicorn habits_api.app:app --reload --port 8081`
  - Seed data: `curl -X POST http://127.0.0.1:8081/admin/ingest`
- Web:
  - `cd web`
  - `npm ci && npm run dev`
  - Open: http://127.0.0.1:5173/
- Tests:
  - Python: `uv run pytest -q`
  - Web: `npm test`

## Troubleshooting & Logs
- Logs live under `/home/prabhanshu/Programs/logs`.
- Quick checks:
  - Size: `ls -lh /home/prabhanshu/Programs/logs/habit-backend.log`
  - Lines: `wc -l /home/prabhanshu/Programs/logs/habit-backend.log`
  - Tail last lines: `tail -n 100 /home/prabhanshu/Programs/logs/habit-backend.log`
- If a log grows large, prefer reading only the tail; you can safely trim with:
  - `truncate -s 0 /home/prabhanshu/Programs/logs/habit-backend.log`
- If the dev shell kills background servers, run them in their own terminal (or tmux) rather than backgrounding.

## Notes (fish + tooling specifics)
- With a global venv active, `uv run` warns but still uses the project `.venv`. You can ignore it or run `uv run --active ...` or `deactivate` first.
- Quote URLs containing `?` in fish: `curl 'http://127.0.0.1:8081/metrics/summary?window=24h'`.
- If `package-lock.json` is missing, prefer `npm install` over `npm ci`.

### One-liner start/stop (manual)
- Start backend in background and capture PID correctly:
  - `cd habit-tracker-git-commits/backend && (nohup env PYTHONPATH=src .venv/bin/python -m uvicorn habits_api.app:app --host 127.0.0.1 --port 8081 > /home/prabhanshu/Programs/logs/habit-backend.log 2>&1 & echo $! > /home/prabhanshu/Programs/logs/habit-backend.pid)`
- Stop backend:
  - `kill \$(cat /home/prabhanshu/Programs/logs/habit-backend.pid) && rm /home/prabhanshu/Programs/logs/habit-backend.pid`

## Configuration
Copy `.env.example` to `.env` and set values (server-side only):
- `GITHUB_TOKEN` — personal access token or GitHub App token for ingestion
- `REPO_ALLOWLIST` — comma-separated `owner/name` repositories to track, or `ALL` to auto-track everything visible to the token
- `PUBLIC_VIEW_TOKEN` — optional share token; if omitted, metrics API is public read-only

## Next Steps
- Scaffold `backend/` and `web/` per `prompts/technical_prompt.md`.
- Implement ingestion for allowlisted repos and expose public summary endpoints.
- Build the Summary, Repo Details, and Diff views with the specified aesthetic.

## Integration (personal-website)
- The personal website can consume the summary at `GET {API_BASE}/metrics/summary?window=24h`.
- A simple section can render the total commits and a link to this app (or embed via iframe `src={WEB_URL}` once hosted).

---
Notes: Follow repo-wide guidelines in `/home/prabhanshu/Programs/AGENTS.md` (uv for Python, no secrets committed, tests via `pytest` and `vitest`).
