#!/usr/bin/env fish

# Start the Habit Tracker (backend + web) in a tmux session.
# - Backend: FastAPI via uvicorn (uv)
# - Web: Next.js dev server
#
# Usage:
#   ./dev.tmux.fish            # start (or attach if already running)
#   ./dev.tmux.fish --restart  # kill existing session and start fresh
#   ./dev.tmux.fish --ingest   # also open a window to trigger one-time ingestion
#   ./dev.tmux.fish --session habits-dev  # custom session name

set -l SESSION "habits"
set -l DO_RESTART 0
set -l DO_INGEST 0

# Parse args robustly
set -l i 1
while test $i -le (count $argv)
    set -l arg $argv[$i]
    switch $arg
        case --restart
            set DO_RESTART 1
        case --ingest
            set DO_INGEST 1
        case --session
            if test (math $i + 1) -le (count $argv)
                set SESSION $argv[(math $i + 1)]
                set i (math $i + 1)
            end
        case '*'
            # ignore unknown flags
    end
    set i (math $i + 1)
end

if not type -q tmux
    echo "tmux not found. Please install tmux and retry." >&2
    exit 1
end

# Derive repo root as this script's directory
set -l ROOT (dirname (status -f))
set -l BACKEND_DIR "$ROOT/backend"
set -l WEB_DIR "$ROOT/web"

if test $DO_RESTART -eq 1
    tmux kill-session -t $SESSION 2>/dev/null
end

# If already running, just attach/switch
if tmux has-session -t $SESSION 2>/dev/null
    echo "Attaching to existing tmux session: $SESSION"
    if set -q TMUX
        exec tmux switch-client -t $SESSION
    else
        exec tmux attach -t $SESSION
    end
end

echo "Creating tmux session: $SESSION"
tmux new-session -d -s $SESSION -n backend

# Some tmux setups start at index 0; target by name for reliability
# Backend window — run dedicated script
tmux send-keys -t $SESSION:backend "fish $ROOT/scripts/dev_backend.fish" C-m

# Web window
tmux new-window -t $SESSION -n web
tmux send-keys -t $SESSION:web "cd $WEB_DIR" C-m
# Web window — run dedicated script
tmux send-keys -t $SESSION:web "fish $ROOT/scripts/dev_web.fish" C-m

if test $DO_INGEST -eq 1
    # Optional seed window to trigger ingestion once
    tmux new-window -t $SESSION -n ingest
    tmux send-keys -t $SESSION:ingest "sleep 2; curl -X POST http://127.0.0.1:8081/admin/ingest; echo ''; echo 'Ingestion trigger sent.'" C-m
end

# Arrange: select web window by default
tmux select-window -t $SESSION:web
if set -q TMUX
    tmux switch-client -t $SESSION
else
    tmux attach -t $SESSION
end
