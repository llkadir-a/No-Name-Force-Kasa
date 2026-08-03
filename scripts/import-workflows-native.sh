#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"
N8N_BIN="$ROOT_DIR/node_modules/.bin/n8n"
export N8N_USER_FOLDER="${N8N_USER_FOLDER:-$ROOT_DIR/.n8n-data}"

get_env() {
  local key="$1"
  local line
  line="$(grep -E "^${key}=" .env | tail -n1 || true)"
  echo "${line#*=}"
}

export N8N_ENCRYPTION_KEY="$(get_env N8N_ENCRYPTION_KEY)"
export N8N_USER_MANAGEMENT_JWT_SECRET="$(get_env N8N_USER_MANAGEMENT_JWT_SECRET)"
export ID_INSTANCE="$(get_env ID_INSTANCE)"
export API_TOKEN="$(get_env API_TOKEN)"
export SOURCE_GROUP_ID="$(get_env SOURCE_GROUP_ID)"
export TARGET_GROUP_ID="$(get_env TARGET_GROUP_ID)"
export BROADCAST_MESSAGE="$(get_env BROADCAST_MESSAGE)"
export N8N_BLOCK_ENV_ACCESS_IN_NODE=false

"$N8N_BIN" import:workflow --input="$ROOT_DIR/n8n-workflows/scenario-1-scheduled-group-broadcast.json"
"$N8N_BIN" import:workflow --input="$ROOT_DIR/n8n-workflows/scenario-2-sync-group-participants.json"
"$N8N_BIN" list:workflow
