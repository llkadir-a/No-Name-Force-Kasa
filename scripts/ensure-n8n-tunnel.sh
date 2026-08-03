#!/usr/bin/env bash
# Public Cloudflare tunnel for n8n (WhatsApp bot webhooks)
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"
mkdir -p logs

CF="${CLOUDFLARED_BIN:-/tmp/cloudflared}"
if [[ ! -x "$CF" ]]; then
  curl -sL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /tmp/cloudflared
  chmod +x /tmp/cloudflared
  CF=/tmp/cloudflared
fi

if [[ -f logs/n8n-tunnel.pid ]]; then
  kill "$(cat logs/n8n-tunnel.pid)" 2>/dev/null || true
  rm -f logs/n8n-tunnel.pid
fi
rm -f logs/n8n-tunnel.log logs/n8n-public-url.txt

echo "-> Cloudflare tunnel → n8n :5678"
nohup "$CF" tunnel --url http://127.0.0.1:5678 --no-autoupdate >logs/n8n-tunnel.log 2>&1 &
echo $! >logs/n8n-tunnel.pid

URL=""
for i in $(seq 1 50); do
  URL="$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' logs/n8n-tunnel.log | head -n1 || true)"
  if [[ -n "$URL" ]]; then
    break
  fi
  sleep 0.4
done

if [[ -z "$URL" ]]; then
  echo "ERROR: could not obtain n8n public URL"
  tail -40 logs/n8n-tunnel.log || true
  exit 1
fi

echo "$URL" >logs/n8n-public-url.txt

# Persist into .env
if grep -q '^WEBHOOK_PUBLIC_URL=' .env 2>/dev/null; then
  sed -i "s|^WEBHOOK_PUBLIC_URL=.*|WEBHOOK_PUBLIC_URL=${URL}|" .env
else
  echo "WEBHOOK_PUBLIC_URL=${URL}" >> .env
fi
if grep -q '^WEBHOOK_URL=' .env 2>/dev/null; then
  sed -i "s|^WEBHOOK_URL=.*|WEBHOOK_URL=${URL}/|" .env
else
  echo "WEBHOOK_URL=${URL}/" >> .env
fi

echo "N8N_PUBLIC_URL=$URL"
echo "BOT_WEBHOOK=${URL}/webhook/ototext-bot"
