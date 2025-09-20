#!/usr/bin/env fish

# Launch Next.js dev server for Habit Tracker web
set -l ROOT (cd (dirname (status -f))/..; pwd)
set -l WEB_DIR "$ROOT/web"

cd $WEB_DIR
if test -d node_modules
    echo 'node_modules present'
else if test -f package-lock.json
    npm ci
else
    npm install
end

set -x NEXT_PUBLIC_API_BASE http://127.0.0.1:8081
npm run dev

