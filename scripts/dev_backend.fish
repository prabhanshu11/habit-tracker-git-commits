#!/usr/bin/env fish

# Launch FastAPI backend for Habit Tracker
set -l ROOT (cd (dirname (status -f))/..; pwd)
set -l BACKEND_DIR "$ROOT/backend"

cd $BACKEND_DIR
test -d .venv; or uv sync
env PYTHONPATH=src uv run uvicorn habits_api.app:app --host 127.0.0.1 --port 8081 --reload

