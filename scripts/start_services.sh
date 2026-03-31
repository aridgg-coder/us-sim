#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_ARTIFACTS_DIR="$ROOT_DIR/run_artifacts"
PID_DIR="$ROOT_DIR/.pids"

mkdir -p "$RUN_ARTIFACTS_DIR" "$PID_DIR"

is_port_listening() {
  local port="$1"
  ss -ltn "sport = :$port" | grep -q ":$port"
}

start_backend() {
  if is_port_listening 8000; then
    echo "Backend already running on :8000"
    return
  fi

  if [[ ! -x "$ROOT_DIR/.venv/bin/uvicorn" ]]; then
    echo "Missing backend dependency: $ROOT_DIR/.venv/bin/uvicorn"
    echo "Install backend deps first in the workspace virtualenv."
    return 1
  fi

  echo "Starting backend on :8000"
  nohup "$ROOT_DIR/.venv/bin/uvicorn" backend.app.main:app --host 0.0.0.0 --port 8000 --app-dir "$ROOT_DIR" \
    > "$RUN_ARTIFACTS_DIR/backend.log" 2>&1 &
  echo $! > "$PID_DIR/backend.pid"
}

start_frontend() {
  if is_port_listening 3000; then
    echo "Frontend already running on :3000"
    return
  fi

  if ! command -v npm >/dev/null 2>&1; then
    echo "npm not found in PATH"
    return 1
  fi

  echo "Starting frontend on :3000"
  (
    cd "$ROOT_DIR/frontend"
    nohup npm run dev -- --hostname 0.0.0.0 --port 3000 \
      > "$RUN_ARTIFACTS_DIR/frontend.log" 2>&1 &
    echo $! > "$PID_DIR/frontend.pid"
  )
}

start_backend
start_frontend

echo "Services startup check complete."
