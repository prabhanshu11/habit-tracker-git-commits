# Habit Tracker — Web (Next.js)

Retro, minimal UI consuming the FastAPI backend.

## Run (local)

- cd web
- npm ci
- Set API base if not default: `export NEXT_PUBLIC_API_BASE=http://127.0.0.1:8081`
- npm run dev
- Open: http://127.0.0.1:5173/

The UI expects the backend running at `NEXT_PUBLIC_API_BASE` and exposes two screens:
- Home: total commits (24h) and per-repo cards
- Repo details: metrics and recent commits list

Styling is Tailwind-based with an inked border + parchment look.
