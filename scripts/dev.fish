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
#   scripts/dev.fish restart         # restart backend and recreate web dev server (kills port if busy)
#   scripts/dev.fish --web-port 5174 # override web port (default 5173)

set -g ROOT (cd (dirname (status -f))/..; pwd)
set -g BACKEND_DIR "$ROOT/backend"
set -g WEB_DIR "$ROOT/web"
set -g LOG_DIR "/home/prabhanshu/Programs/logs"
set -g LOG_FILE "$LOG_DIR/habit-backend.log"
set -g PID_FILE "$LOG_DIR/habit-backend.pid"
set -g API_URL "http://127.0.0.1:8081"
set -g WEB_PORT 5173

set -l DO_INGEST 0
set -l CMD "start"

# Parse args
set -l i 1
while test $i -le (count $argv)
    set -l arg $argv[$i]
    switch $arg
        case --ingest
            set DO_INGEST 1
        case start stop status restart
            set CMD $arg
        case --web-port
            set i (math $i + 1)
            if test $i -le (count $argv)
                set WEB_PORT $argv[$i]
            end
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

function _pid_on_port -a port
    set -l pid ""
    if type -q lsof
        set pid (lsof -t -i :$port 2>/dev/null | head -n1)
    end
    if test -z "$pid"; and type -q fuser
        set pid (fuser -n tcp $port 2>/dev/null | string trim)
    end
    if test -z "$pid"; and type -q ss
        set pid (ss -ltnp 2>/dev/null | awk -v p=$port '$4 ~ ":"p"$" {print $NF}' | sed -n 's/.*pid=\([0-9]\+\).*/\1/p' | head -n1)
    end
    if test -n "$pid"
        echo $pid
        return 0
    end
    return 1
end

function stop_web
    set -l pid (_pid_on_port $WEB_PORT)
    if test -n "$pid"
        echo "Stopping web on port $WEB_PORT (PID: $pid)"
        kill $pid 2>/dev/null
        sleep 0.5
        if kill -0 $pid 2>/dev/null
            echo "Force killing web PID $pid"
            kill -9 $pid 2>/dev/null
        end
    else
        echo "Web not running on port $WEB_PORT"
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
    # Ensure port is free; kill any existing process using it
    set -l pid (_pid_on_port $WEB_PORT)
    if test -n "$pid"
        echo "Port $WEB_PORT is busy (PID: $pid). Recreating web server..."
        stop_web
    end
    echo "Web dev server → http://127.0.0.1:$WEB_PORT/"
    # Run Next.js dev on specified port directly
    npx next dev -p $WEB_PORT
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
        stop_web
    case status
        status_backend
        set -l pid (_pid_on_port $WEB_PORT)
        if test -n "$pid"
            echo "Web running on :$WEB_PORT (PID: $pid)"
        else
            echo "Web not running on :$WEB_PORT"
        end
    case restart
        stop_backend
        stop_web
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
end
