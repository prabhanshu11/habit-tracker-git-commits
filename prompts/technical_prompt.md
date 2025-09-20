# Habit Tracker — Git Commits

Authoring prompt for a capable developer AI. The AI is technically strong but needs complete planning and explicit deliverables. Follow this spec exactly unless stated as optional.

## Goal
- Track commit activity across my GitHub repositories (public and private) and surface: 
  - Primary metric: number of commits in the last 24 hours and since last check (server-side snapshot).
  - Secondary metrics: per-commit lines added/removed, changed files, author, message, and links; ability to view diffs and file contents (public repos only by default).
- Provide a fast, flowy, retro, minimal UI (mobile + desktop) inspired by the screenshots in `prompts/`.
- Share read-only metrics with friends without requiring them to log in with my GitHub credentials.

## Non-Goals
- Multi-tenant auth is out of scope. Only one owner account (mine) whose repos are tracked.
- Editing code in the UI is out of scope.

## High-Level Architecture
- Monorepo with two apps:
  - `backend/` — Python FastAPI service + background scheduler.
  - `web/` — Next.js app (React, TypeScript) for the UI.
- Data store: SQLite locally; allow Postgres via `DATABASE_URL`.
- Ingestion: GitHub GraphQL API (v4) primarily; REST fallback for diffs/files.
- Secrets: `.env` loaded only on the server; never sent to clients.
- Public read-only API to serve aggregated metrics; no client secret required.

```
[APScheduler worker] -> GitHub GraphQL -> [DB]
         |                                   ^
         v                                   |
   FastAPI REST  <—— Web (Next.js) ——>  public GET endpoints
```

## Repository Layout
```
habit-tracker-git-commits/
  backend/
    src/habits_api/            # FastAPI app package
    tests/                     # pytest
    alembic/                   # migrations (optional)
    pyproject.toml
  web/
    src/                       # Next.js app code
    public/                    # static assets and starburst SVGs
    package.json
  prompts/                     # design references & this spec
  .env.example
  README.md
```

## Backend Details (FastAPI, Python, uv)
- Use `uv` for environment and dependency management.
- Packages: `fastapi`, `uvicorn[standard]`, `httpx`, `pydantic`, `sqlalchemy`, `alembic`, `apscheduler`, `python-dotenv`, `pytest`.
- Config via `pydantic` settings with these env vars:
  - `GITHUB_TOKEN` (required, classic PAT or GitHub App token)
  - `REPO_ALLOWLIST` (comma-separated `owner/name` values)
  - `DATABASE_URL` (optional; default `sqlite+aiosqlite:///./data.db`)
  - `PUBLIC_VIEW_TOKEN` (optional: if set, include in share links; absence means fully public read)

### Data Model (SQLAlchemy)
- `Repository(id, full_name, default_branch, is_private, enabled, last_checked_at, created_at, updated_at)`
- `Snapshot(id, repo_id, window_start, window_end, commits_count, lines_added, lines_deleted, captured_at)`
- `Commit(id, repo_id, sha, author_name, author_login, committed_at, message, additions, deletions, files_changed)`
- `CommitFile(id, commit_id, path, status, additions, deletions)`

Indexes:
- `Commit.repo_id+committed_at` (desc), `Commit.sha` unique per repo.

### Ingestion Logic
- Scheduler: APScheduler job runs every 15 minutes; also allow manual trigger.
- For each repo in allowlist:
  - Determine `since = max(last_checked_at, now-24h)`. Query commits since `since` on default branch via GraphQL:
    - Use `repository(object(expression: "<branch>") { ... on Commit { history(since: <ISO>) { nodes { oid committedDate message author { name user { login } } additions deletions changedFiles } } } }`.
  - For each commit, request changed files and per-file stats via REST `GET /repos/{owner}/{repo}/commits/{sha}` only if not already cached.
  - Upsert `Commit` and `CommitFile` rows; accumulate totals and write a `Snapshot` per run.
  - Update `Repository.last_checked_at`.
- Rate limits:
  - Respect GraphQL `rateLimit` object; back off with jitter; persist `X-RateLimit-Remaining` and `reset` in logs.
  - Cap REST commit-file fetches per run (e.g., 100 commits) and carry over remainder next run.

### REST API (FastAPI)
- `GET /health` → `{status:"ok"}`
- `GET /repos` → list tracked repos + last_checked_at
- `POST /repos` (owner only) → add repo from URL; validate allowlist (accept hidden admin token in header)
- `GET /metrics/summary?window=24h` → aggregate across repos: total commits, per-repo top lines added/deleted, last_checked_at
- `GET /repos/{id}/metrics?window=24h` → commits_count, lines_added, lines_deleted, sparkline data (hourly bins)
- `GET /repos/{id}/commits?since=ISO&limit=100` → commit objects with file counts
- `GET /repos/{id}/commit/{sha}` → full commit (for public repos serve file contents; for private repos redact contents unless `allowPrivateCode=true` in server config)

Validation & Errors:
- Consistent error envelope `{error:{code,message}}`; never leak tokens.

### Tests (pytest)
- Unit: ingestion transforms, API schemas, time-window binning.
- Integration: mock GitHub (use `respx`), DB fixtures, scheduler dry-run.
- Property: commit aggregation invariants (adds+deletes >= 0, monotonic last_checked).

## Frontend Details (Next.js, TypeScript)
- Tooling: Next.js (App Router), Tailwind CSS, `@tanstack/react-query`, `zod`, `eslint`, `prettier`, `vitest`.
- Data fetching: React Query with stale-while-revalidate; all API URLs configurable via `NEXT_PUBLIC_API_BASE`.

### Aesthetic & Style Guide
Use the screenshots under `prompts/` as reference (Gitinjest-like):
- Warm parchment background, dark ink text, thick 2px inked borders, rounded 8px corners.
- Accent shapes: 2–3 playful starburst SVGs subtly animated in/out of view.
- Components feel tactile: slight drop shadow, short springy transitions.

Design tokens (approximate):
- `--bg: #F7E7D3` (parchment), `--ink: #121212`, `--panel: #FBEEDB`, `--accent: #F4B73B`, `--mint: #C8F3D9`, `--rose: #FFD1D9`.
- Border: 2px solid `var(--ink)`; Shadow: `0 2px 0 var(--ink)`.
- Font stack: `Inter`, ui-sans-serif; code blocks `JetBrains Mono`.

Key screens and interactions:
- Home (Summary)
  - Big headline number: “Commits (24h)”.
  - Slider-like control to choose window (6h, 24h, 7d); default 24h.
  - Repo cards with per-repo counts and tiny sparkline; tap opens repo details.
- Repo Details
  - Two columns (stack on mobile): Summary (counts, last checked) and Commit List.
  - Commit items show message, author, time, additions/deletions chips; tap expands to file list.
  - View Code button opens diff viewer (public repos only by default).
- Diff / Code Viewer
  - Side-by-side on desktop; unified on mobile; copy buttons with inked borders.
  - Keyboard shortcuts: `j/k` to move commits, `o` to toggle files.

Motion:
- Cards pop-in with 120–160ms spring; accent stars float in/out with 4s gentle y-oscillation.
- Buttons depress (translateY(1px)) on active; inputs have subtle 2px focus ring.

Accessibility:
- WCAG AA contrast for text; focus outlines visible; prefers-reduced-motion respected.

### Frontend Testing
- Component tests with Vitest + React Testing Library.
- E2E happy-path with Playwright: loads summary, opens repo, views a commit.

## Security & Privacy
- Only the backend possesses `GITHUB_TOKEN`; the UI never sees it.
- For private repos: by default, serve aggregated metrics and file names; block serving file contents. Allow owner-only flag `ALLOW_PRIVATE_CODE=true` to enable serving diffs to trusted viewers if desired.
- Never store secrets in the repo; provide `.env.example`.

## Observability
- Structured logs (JSON) with request ids; log rate-limit headers and retry events.
- Simple `/metrics` (optional) in Prometheus format: job timings, API latency.

## Build & Run Commands

Backend (fish shell; preferred via `uv`):
```
cd backend
uv sync
uv run uvicorn habits_api.app:app --reload --port 8081
```

Web:
```
cd web
npm ci
npm run dev
```

## Acceptance Criteria
- Displays total commits in last 24h across allowlisted repos with a single number on the home screen.
- “Last checked” timestamp visible and updated after each scheduler run.
- Per-repo view shows commit list with additions/deletions counts.
- Can expand a commit to see changed files and, for public repos, open a code viewer with diff.
- UI matches the referenced aesthetic within a reasonable approximation (colors, borders, motion, copy buttons, star accents).
- Works on mobile and desktop; lighthouse performance score ≥ 90 on a simple dataset.
- No secrets leak to clients or logs.

## Stretch Goals (Optional)
- GitLab support behind a feature flag.
- Desktop tray mini-widget (Tauri) that surfaces the 24h commit count.
- Webhooks to reduce polling where repos are public.

## Notes for the Developer AI
- Keep functions small and pure; write types for DTOs and API schemas.
- Justify any complexity in code comments only where nontrivial.
- Favor GraphQL for batch history pulls; REST for per-commit file details.


