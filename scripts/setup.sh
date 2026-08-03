#!/usr/bin/env bash
# Full local setup: .env → docker compose up → wait healthy → import workflows
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "=== Green API + n8n setup ==="

if [[ ! -f .env ]]; then
  echo "Creating .env from .env.example ..."
  cp .env.example .env
  ENC="$(openssl rand -hex 24)"
  JWT="$(openssl rand -hex 24)"
  sed -i "s/change-me-to-a-long-random-encryption-key/$ENC/" .env
  sed -i "s/change-me-to-a-long-random-jwt-secret/$JWT/" .env
  echo "Generated N8N_ENCRYPTION_KEY and JWT secret."
fi

get_env() {
  local key="$1"
  local line
  line="$(grep -E "^${key}=" .env | tail -n1 || true)"
  echo "${line#*=}"
}

ID_INSTANCE="$(get_env ID_INSTANCE)"
API_TOKEN="$(get_env API_TOKEN)"
N8N_PORT="$(get_env N8N_PORT)"
N8N_PORT="${N8N_PORT:-5678}"
N8N_OWNER_EMAIL="$(get_env N8N_OWNER_EMAIL)"
N8N_OWNER_PASSWORD="$(get_env N8N_OWNER_PASSWORD)"
N8N_OWNER_FIRST_NAME="$(get_env N8N_OWNER_FIRST_NAME)"
N8N_OWNER_LAST_NAME="$(get_env N8N_OWNER_LAST_NAME)"
export N8N_PORT

if [[ "${ID_INSTANCE}" == "YOUR_INSTANCE_ID" || "${API_TOKEN}" == "YOUR_API_TOKEN_INSTANCE" ]]; then
  echo
  echo "WARNING: ID_INSTANCE / API_TOKEN still placeholders in .env"
  echo "         Edit .env with real Green API values, then: docker compose up -d --force-recreate"
  echo
fi

echo "-> Pulling n8n image and starting stack..."
sudo docker compose pull
sudo docker compose up -d

echo "-> Waiting for n8n health..."
ATTEMPTS=60
for i in $(seq 1 "$ATTEMPTS"); do
  if curl -sf "http://127.0.0.1:${N8N_PORT}/healthz" >/dev/null 2>&1; then
    echo "n8n is healthy (attempt $i)."
    break
  fi
  if [[ "$i" -eq "$ATTEMPTS" ]]; then
    echo "ERROR: n8n did not become healthy in time."
    sudo docker compose logs --tail=80 n8n || true
    exit 1
  fi
  sleep 2
done

sleep 3

echo "-> Importing workflows..."
bash "$ROOT_DIR/scripts/import-workflows.sh"

if [[ -n "${N8N_OWNER_EMAIL}" && -n "${N8N_OWNER_PASSWORD}" ]]; then
  echo "-> Attempting owner account bootstrap (if not already set)..."
  SETUP_PAYLOAD="$(
    N8N_OWNER_EMAIL="$N8N_OWNER_EMAIL" \
    N8N_OWNER_PASSWORD="$N8N_OWNER_PASSWORD" \
    N8N_OWNER_FIRST_NAME="${N8N_OWNER_FIRST_NAME:-Admin}" \
    N8N_OWNER_LAST_NAME="${N8N_OWNER_LAST_NAME:-User}" \
    python3 -c 'import json,os; print(json.dumps({"email":os.environ["N8N_OWNER_EMAIL"],"password":os.environ["N8N_OWNER_PASSWORD"],"firstName":os.environ.get("N8N_OWNER_FIRST_NAME","Admin"),"lastName":os.environ.get("N8N_OWNER_LAST_NAME","User")}))'
  )"
  HTTP_CODE=$(curl -sS -o /tmp/n8n-owner-setup.json -w "%{http_code}" \
    -X POST "http://127.0.0.1:${N8N_PORT}/rest/owner/setup" \
    -H "Content-Type: application/json" \
    -d "$SETUP_PAYLOAD" || true)
  echo "Owner setup HTTP $HTTP_CODE — $(head -c 200 /tmp/n8n-owner-setup.json 2>/dev/null || true)"
fi

echo
echo "============================================"
echo " n8n UI:  http://localhost:${N8N_PORT}"
echo " Email:   ${N8N_OWNER_EMAIL}"
echo
echo " Next steps:"
echo "  1. Put real ID_INSTANCE / API_TOKEN in .env"
echo "  2. Fill SOURCE_GROUP_ID / TARGET_GROUP_ID"
echo "  3. Update 20 chatId values in Scenario 1 Code node"
echo "  4. docker compose up -d --force-recreate"
echo "  5. Activate workflows in the UI"
echo "============================================"
