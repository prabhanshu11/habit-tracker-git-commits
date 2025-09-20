# Habit Tracker — Web (Next.js)

Retro, minimal UI consuming the FastAPI backend.

## Run (local)

- Default: run from repo root with `scripts/dev.fish` (fish shell). It starts backend + web, frees the port if busy, and supports `--ingest`, `restart`, `stop`, and `--web-port`.

### Manual web only

- cd web
- npm ci
- Set API base if not default: `export NEXT_PUBLIC_API_BASE=http://127.0.0.1:8081`
- npm run dev
- Open: http://127.0.0.1:5173/

The UI expects the backend running at `NEXT_PUBLIC_API_BASE` and exposes two screens:
- Home: lines updated (24h), repos updated, and per-repo cards. Includes a "Refresh now" button to trigger ingestion.
- Repo details: metrics and recent commits list

Styling is Tailwind-based with an inked border + parchment look.
