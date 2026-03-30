#!/bin/bash
# Starts FastAPI (port 8000) and Panel dashboard (port 5006) together.
# React dev server runs separately: cd frontend && npm run dev

set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
source "$ROOT/venv/bin/activate"

echo "Starting FastAPI on http://localhost:8000 ..."
cd "$ROOT/backend"
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload &
FASTAPI_PID=$!

echo "Starting Panel dashboard on http://localhost:5006 ..."
panel serve dashboard/gdp_dashboard.py \
  --port 5006 \
  --allow-websocket-origin localhost:5173 \
  --allow-websocket-origin localhost:3000 \
  --allow-websocket-origin localhost:8000 \
  --allow-websocket-origin localhost:5006 \
  &
PANEL_PID=$!

echo ""
echo "  FastAPI API  → http://localhost:8000/api/health"
echo "  Panel board  → http://localhost:5006/gdp_dashboard"
echo "  React (dev)  → cd frontend && npm run dev"
echo ""
echo "Press Ctrl+C to stop all servers."

trap "kill $FASTAPI_PID $PANEL_PID 2>/dev/null; exit 0" INT TERM
wait
