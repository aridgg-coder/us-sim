#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_DIR="$ROOT_DIR/.pids"

stop_pid_file() {
  local pid_file="$1"
  local label="$2"

  if [[ ! -f "$pid_file" ]]; then
    echo "$label PID file not found"
    return
  fi

  local pid
  pid="$(cat "$pid_file")"

  if kill -0 "$pid" >/dev/null 2>&1; then
    echo "Stopping $label (PID $pid)"
    kill "$pid"
  else
    echo "$label PID $pid is not running"
  fi

  rm -f "$pid_file"
}

stop_pid_file "$PID_DIR/backend.pid" "Backend"
stop_pid_file "$PID_DIR/frontend.pid" "Frontend"

kill_by_port() {
  local port="$1"
  local label="$2"
  local pids
  pids="$(ss -ltnp "sport = :$port" 2>/dev/null | sed -n 's/.*pid=\([0-9]\+\).*/\1/p' | sort -u)"

  if [[ -z "$pids" ]]; then
    return
  fi

  for pid in $pids; do
    if kill -0 "$pid" >/dev/null 2>&1; then
      echo "Stopping $label by port :$port (PID $pid)"
      kill "$pid" || true
    fi
  done
}

kill_by_port 8000 "Backend"
kill_by_port 3000 "Frontend"

echo "Services stop check complete."
