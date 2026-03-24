#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "▸ Setting up Python backend …"
cd "$ROOT/backend"

if [ ! -d "venv" ]; then
  python3 -m venv venv
fi

source venv/bin/activate
pip install -q -r requirements.txt

echo "▸ Starting FastAPI on :8000 …"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

echo "▸ Setting up React frontend …"
cd "$ROOT/frontend"

if [ ! -d "node_modules" ]; then
  npm install
fi

echo "▸ Starting Vite on :5173 …"
npm run dev &
FRONTEND_PID=$!

cleanup() {
  echo ""
  echo "▸ Shutting down …"
  kill $BACKEND_PID 2>/dev/null
  kill $FRONTEND_PID 2>/dev/null
}
trap cleanup EXIT INT TERM

echo ""
echo "  ╔══════════════════════════════════════╗"
echo "  ║   Keychain Generator is running!     ║"
echo "  ║   Frontend → http://localhost:5173   ║"
echo "  ║   Backend  → http://localhost:8000   ║"
echo "  ╚══════════════════════════════════════╝"
echo ""

wait
