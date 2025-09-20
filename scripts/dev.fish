#!/usr/bin/env fish

# Start Habit Tracker locally:
# - Backend (FastAPI) runs in background and logs to /home/prabhanshu/Programs/logs/habit-backend.log
# - Web (Next.js) runs in foreground
#
# Usage:
#   scripts/dev.fish                 # start backend (bg, logged) + web (fg)
#   scripts/dev.fish --ingest        # also trigger one ingestion after backend is up
#   scripts/dev.fish stop            # stop backend (reads PID)
#   scripts/dev.fish status          # show backend status

set -g ROOT (cd (dirname (status -f))/..; pwd)
set -g BACKEND_DIR "$ROOT/backend"
set -g WEB_DIR "$ROOT/web"
set -g LOG_DIR "/home/prabhanshu/Programs/logs"
set -g LOG_FILE "$LOG_DIR/habit-backend.log"
set -g PID_FILE "$LOG_DIR/habit-backend.pid"
set -g API_URL "http://127.0.0.1:8081"

set -l DO_INGEST 0
set -l CMD "start"

# Parse args
set -l i 1
while test $i -le (count $argv)
    set -l arg $argv[$i]
    switch $arg
        case --ingest
            set DO_INGEST 1
        case start stop status
            set CMD $arg
        case '*'
            # ignore unknown flags
    end
    set i (math $i + 1)
end

function _ensure_logs
    mkdir -p $LOG_DIR
end

function _backend_running
    if test -f $PID_FILE
        set -l pid (cat $PID_FILE 2>/dev/null)
        if test -n "$pid"; and kill -0 $pid 2>/dev/null
            return 0
        end
    end
    return 1
end

function start_backend
    if _backend_running
        echo "Backend already running (PID: (cat $PID_FILE))"
        return 0
    end
    _ensure_logs
    echo "Starting backend → $LOG_FILE"
    cd $BACKEND_DIR
    test -d .venv; or uv sync
    # Fresh log for each start
    : > $LOG_FILE
    nohup env PYTHONPATH=src .venv/bin/python -m uvicorn habits_api.app:app \
        --host 127.0.0.1 --port 8081 \
        >> $LOG_FILE 2>&1 &
    echo $last_pid > $PID_FILE

    # Wait until /health responds or timeout
    for i in (seq 30)
        if curl -sf "$API_URL/health" >/dev/null 2>&1
            echo "Backend is up at $API_URL"
            return 0
        end
        sleep 0.5
    end
    echo "Warning: backend did not become healthy in time; check $LOG_FILE"
end

function stop_backend
    if not test -f $PID_FILE
        echo "No PID file: $PID_FILE"
        return 0
    end
    set -l pid (cat $PID_FILE 2>/dev/null)
    if test -n "$pid"; and kill -0 $pid 2>/dev/null
        echo "Stopping backend (PID: $pid)"
        kill $pid
        rm -f $PID_FILE
    else
        echo "Backend not running; removing stale PID file"
        rm -f $PID_FILE
    end
end

function status_backend
    if _backend_running
        echo "Backend running (PID: (cat $PID_FILE)) — logs: $LOG_FILE"
    else
        echo "Backend not running"
    end
end

function start_web
    cd $WEB_DIR
    if test -d node_modules
        echo 'node_modules present'
    else if test -f package-lock.json
        npm ci
    else
        npm install
    end
    set -x NEXT_PUBLIC_API_BASE $API_URL
    echo "Web dev server → http://127.0.0.1:5173/"
    npm run dev
end

switch $CMD
    case start
        start_backend
        if test $DO_INGEST -eq 1
            echo "Triggering ingestion once..."
            if curl -sf -X POST "$API_URL/admin/ingest" >/dev/null 2>&1
                echo "Ingestion triggered."
            else
                echo "Ingestion failed (check $LOG_FILE)."
            end
        end
        start_web
    case stop
        stop_backend
    case status
        status_backend
end
