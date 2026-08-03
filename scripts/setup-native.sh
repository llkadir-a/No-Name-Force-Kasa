#!/usr/bin/env bash
# Native (non-Docker) n8n setup — uses local ./node_modules/.bin/n8n
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"
N8N_BIN="$ROOT_DIR/node_modules/.bin/n8n"
N8N_USER_FOLDER="${N8N_USER_FOLDER:-$ROOT_DIR/.n8n-data}"
mkdir -p "$N8N_USER_FOLDER" "$ROOT_DIR/logs"

get_env() {
  local key="$1"
  local line
  line="$(grep -E "^${key}=" .env | tail -n1 || true)"
  echo "${line#*=}"
}

if [[ ! -f .env ]]; then
  cp .env.example .env
fi

echo "-> License check..."
if ! python3 "$ROOT_DIR/scripts/check-license.py"; then
  echo "ERROR: Geçerli lisans yok. Satıcı paketini kullan veya LICENSE_SKIP=1 (sadece geliştirici)."
  exit 1
fi

if [[ ! -x "$N8N_BIN" ]]; then
  echo "-> Installing n8n locally..."
  npm install n8n --save
fi

ID_INSTANCE="$(get_env ID_INSTANCE)"
API_TOKEN="$(get_env API_TOKEN)"
N8N_PORT="$(get_env N8N_PORT)"; N8N_PORT="${N8N_PORT:-5678}"
N8N_HOST="$(get_env N8N_HOST)"; N8N_HOST="${N8N_HOST:-localhost}"
N8N_PROTOCOL="$(get_env N8N_PROTOCOL)"; N8N_PROTOCOL="${N8N_PROTOCOL:-http}"
WEBHOOK_URL="$(get_env WEBHOOK_URL)"; WEBHOOK_URL="${WEBHOOK_URL:-http://localhost:5678/}"
GENERIC_TIMEZONE="$(get_env GENERIC_TIMEZONE)"; GENERIC_TIMEZONE="${GENERIC_TIMEZONE:-Europe/Istanbul}"
TZ_VAL="$(get_env TZ)"; TZ_VAL="${TZ_VAL:-Europe/Istanbul}"
N8N_ENCRYPTION_KEY="$(get_env N8N_ENCRYPTION_KEY)"
N8N_USER_MANAGEMENT_JWT_SECRET="$(get_env N8N_USER_MANAGEMENT_JWT_SECRET)"
BROADCAST_MESSAGE="$(get_env BROADCAST_MESSAGE)"
SOURCE_GROUP_ID="$(get_env SOURCE_GROUP_ID)"
TARGET_GROUP_ID="$(get_env TARGET_GROUP_ID)"
N8N_OWNER_EMAIL="$(get_env N8N_OWNER_EMAIL)"
N8N_OWNER_PASSWORD="$(get_env N8N_OWNER_PASSWORD)"
N8N_OWNER_FIRST_NAME="$(get_env N8N_OWNER_FIRST_NAME)"
N8N_OWNER_LAST_NAME="$(get_env N8N_OWNER_LAST_NAME)"

echo "=== Ototext native setup ==="

export N8N_USER_FOLDER
export N8N_HOST N8N_PORT N8N_PROTOCOL WEBHOOK_URL
export GENERIC_TIMEZONE TZ="$TZ_VAL"
export N8N_ENCRYPTION_KEY N8N_USER_MANAGEMENT_JWT_SECRET
export N8N_BLOCK_ENV_ACCESS_IN_NODE=false
export NODE_FUNCTION_ALLOW_BUILTIN=fs,path
export N8N_DIAGNOSTICS_ENABLED=false
export N8N_PERSONALIZATION_ENABLED=false
export EXECUTIONS_DATA_SAVE_ON_SUCCESS=all
export EXECUTIONS_DATA_SAVE_ON_ERROR=all
export EXECUTIONS_DATA_SAVE_MANUAL_EXECUTIONS=true
export ID_INSTANCE API_TOKEN SOURCE_GROUP_ID TARGET_GROUP_ID BROADCAST_MESSAGE
export BROADCAST_GROUPS BOT_PREFIX BOT_ADMINS WEBHOOK_PUBLIC_URL
BROADCAST_GROUPS="$(get_env BROADCAST_GROUPS)"
BOT_PREFIX="$(get_env BOT_PREFIX)"
BOT_ADMINS="$(get_env BOT_ADMINS)"
WEBHOOK_PUBLIC_URL="$(get_env WEBHOOK_PUBLIC_URL)"
LICENSE_KEY="$(get_env LICENSE_KEY)"
OTOTEXT_LICENSE_SECRET="$(get_env OTOTEXT_LICENSE_SECRET)"
export BROADCAST_GROUPS BOT_PREFIX BOT_ADMINS WEBHOOK_PUBLIC_URL LICENSE_KEY OTOTEXT_LICENSE_SECRET

if [[ "${ID_INSTANCE}" == "YOUR_INSTANCE_ID" || "${API_TOKEN}" == "YOUR_API_TOKEN_INSTANCE" ]]; then
  echo "WARNING: ID_INSTANCE / API_TOKEN still placeholders in .env"
fi

if [[ -f "$ROOT_DIR/logs/n8n.pid" ]]; then
  OLD_PID="$(cat "$ROOT_DIR/logs/n8n.pid" || true)"
  if [[ -n "${OLD_PID}" ]] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "-> Stopping previous n8n pid $OLD_PID"
    kill "$OLD_PID" || true
    sleep 2
  fi
fi

echo "-> Starting n8n on port ${N8N_PORT}..."
nohup "$N8N_BIN" start >"$ROOT_DIR/logs/n8n.log" 2>&1 &
echo $! >"$ROOT_DIR/logs/n8n.pid"
echo "n8n pid $(cat "$ROOT_DIR/logs/n8n.pid")"

echo "-> Waiting for health..."
ATTEMPTS=90
for i in $(seq 1 "$ATTEMPTS"); do
  if curl -sf "http://127.0.0.1:${N8N_PORT}/healthz" >/dev/null 2>&1; then
    echo "n8n healthy (attempt $i)"
    break
  fi
  if [[ "$i" -eq "$ATTEMPTS" ]]; then
    echo "ERROR: n8n not healthy"
    tail -80 "$ROOT_DIR/logs/n8n.log" || true
    exit 1
  fi
  sleep 2
done

sleep 2

echo "-> Importing workflows..."
"$N8N_BIN" import:workflow --input="$ROOT_DIR/n8n-workflows/scenario-1-scheduled-group-broadcast.json"
"$N8N_BIN" import:workflow --input="$ROOT_DIR/n8n-workflows/scenario-2-sync-group-participants.json"
"$N8N_BIN" list:workflow || true

if [[ -n "${N8N_OWNER_EMAIL}" && -n "${N8N_OWNER_PASSWORD}" ]]; then
  echo "-> Owner bootstrap..."
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
  echo "Owner setup HTTP $HTTP_CODE — $(head -c 220 /tmp/n8n-owner-setup.json 2>/dev/null || true)"
fi

echo
echo "============================================"
echo " n8n UI:  http://localhost:${N8N_PORT}"
echo " Email:   ${N8N_OWNER_EMAIL}"
echo " Pass:    (see N8N_OWNER_PASSWORD in .env)"
echo " Logs:    $ROOT_DIR/logs/n8n.log"
echo " Data:    $N8N_USER_FOLDER"
echo "============================================"
