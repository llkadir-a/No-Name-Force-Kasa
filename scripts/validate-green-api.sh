#!/usr/bin/env bash
# Validate Green API credentials from .env via getStateInstance
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

get_env() {
  local key="$1"
  local line
  line="$(grep -E "^${key}=" .env | tail -n1 || true)"
  echo "${line#*=}"
}

ID_INSTANCE="$(get_env ID_INSTANCE)"
API_TOKEN="$(get_env API_TOKEN)"

if [[ -z "$ID_INSTANCE" || -z "$API_TOKEN" || "$ID_INSTANCE" == "YOUR_INSTANCE_ID" || "$API_TOKEN" == "YOUR_API_TOKEN_INSTANCE" ]]; then
  echo "FAIL: Set real ID_INSTANCE and API_TOKEN in .env first."
  exit 1
fi

URL="https://api.green-api.com/waInstance${ID_INSTANCE}/getStateInstance/${API_TOKEN}"
echo "GET $URL"
HTTP_CODE=$(curl -sS -o /tmp/green-api-state.json -w "%{http_code}" "$URL" || true)
echo "HTTP $HTTP_CODE"
cat /tmp/green-api-state.json
echo

if [[ "$HTTP_CODE" != "200" ]]; then
  echo "FAIL: Green API did not return 200"
  exit 1
fi

STATE=$(python3 -c 'import json; print(json.load(open("/tmp/green-api-state.json")).get("stateInstance",""))')
echo "stateInstance=$STATE"
if [[ "$STATE" == "authorized" ]]; then
  echo "OK: Green API instance is authorized"
  exit 0
fi
echo "WARN: Instance responded but state is '$STATE' (expected authorized)"
exit 2
