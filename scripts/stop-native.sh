#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PID_FILE="$ROOT_DIR/logs/n8n.pid"
if [[ -f "$PID_FILE" ]]; then
  PID="$(cat "$PID_FILE")"
  if kill -0 "$PID" 2>/dev/null; then
    kill "$PID"
    echo "Stopped n8n pid $PID"
  else
    echo "n8n not running (stale pid file)"
  fi
  rm -f "$PID_FILE"
else
  pkill -f "node_modules/.bin/n8n start" 2>/dev/null || echo "No n8n process found"
fi
