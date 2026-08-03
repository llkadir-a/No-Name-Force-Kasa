#!/usr/bin/env bash
# Import both Green API workflows into the running n8n container.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CONTAINER="${N8N_CONTAINER:-ototext-n8n}"

if ! sudo docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
  echo "ERROR: Container '$CONTAINER' is not running. Start with: ./scripts/setup.sh"
  exit 1
fi

import_one() {
  local file="$1"
  local base
  base="$(basename "$file")"
  echo "→ Importing $base"
  sudo docker exec -u node "$CONTAINER" n8n import:workflow --input="/workflows/$base"
}

import_one "$ROOT_DIR/n8n-workflows/ototext-bot-commands.json"
import_one "$ROOT_DIR/n8n-workflows/scenario-1-scheduled-group-broadcast.json"
import_one "$ROOT_DIR/n8n-workflows/scenario-2-sync-group-participants.json"

echo
echo "Imported workflows:"
sudo docker exec -u node "$CONTAINER" n8n list:workflow || true
echo
echo "Done. Open http://localhost:${N8N_PORT:-5678} and activate workflows after setting real Green API credentials in .env"
