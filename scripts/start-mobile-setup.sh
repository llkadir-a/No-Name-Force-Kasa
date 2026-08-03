#!/usr/bin/env bash
# Start mobile setup UI + public Cloudflare quick tunnel
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"
mkdir -p logs

# Ensure n8n is up
if ! curl -sf "http://127.0.0.1:5678/healthz" >/dev/null 2>&1; then
  echo "n8n not healthy — starting native setup first"
  bash "$ROOT_DIR/scripts/setup-native.sh"
fi

# Stop previous setup server / tunnel if any
if [[ -f logs/setup-server.pid ]]; then
  kill "$(cat logs/setup-server.pid)" 2>/dev/null || true
fi
if [[ -f logs/cloudflared.pid ]]; then
  kill "$(cat logs/cloudflared.pid)" 2>/dev/null || true
fi

echo "-> Starting mobile setup server on :8787"
nohup python3 "$ROOT_DIR/scripts/mobile-setup-server.py" >logs/setup-server.log 2>&1 &
echo $! >logs/setup-server.pid

# Wait local
for i in $(seq 1 30); do
  if curl -sf http://127.0.0.1:8787/health >/dev/null; then
    break
  fi
  sleep 0.5
done

CF="${CLOUDFLARED_BIN:-/tmp/cloudflared}"
if [[ ! -x "$CF" ]]; then
  curl -sL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /tmp/cloudflared
  chmod +x /tmp/cloudflared
  CF=/tmp/cloudflared
fi

echo "-> Opening Cloudflare quick tunnel"
nohup "$CF" tunnel --url http://127.0.0.1:8787 --no-autoupdate >logs/cloudflared.log 2>&1 &
echo $! >logs/cloudflared.pid

# Extract public URL
URL=""
for i in $(seq 1 40); do
  URL="$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' logs/cloudflared.log | head -n1 || true)"
  if [[ -n "$URL" ]]; then
    break
  fi
  sleep 0.5
done

echo "$URL" >logs/mobile-setup-url.txt
echo
echo "============================================"
echo " TELEFON LINK:"
echo " $URL"
echo "============================================"
echo "Bu linki telefonda aç → Green API bilgilerini yapıştır → Kur ve Aktif Et"
