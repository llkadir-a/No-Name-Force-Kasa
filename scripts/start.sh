#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"
sudo docker compose up -d
echo "n8n → http://localhost:${N8N_PORT:-5678}"
