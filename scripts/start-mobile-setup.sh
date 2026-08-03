#!/usr/bin/env bash
# Mobil QR kurulum — müşteri API uğraşmaz, WhatsApp QR okutur
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"
mkdir -p logs

if [[ ! -f .env && -f .env.example ]]; then
  cp .env.example .env
fi

echo "-> License check"
python3 "$ROOT_DIR/scripts/check-license.py" || {
  echo "Lisans yok — satıcı paketini kullan veya LICENSE_SKIP=1"
  exit 1
}

if [[ ! -x "$ROOT_DIR/node_modules/.bin/n8n" ]]; then
  echo "-> npm install n8n (ilk kurulum)"
  npm install n8n --save
fi

if [[ -f logs/setup-server.pid ]]; then
  kill "$(cat logs/setup-server.pid)" 2>/dev/null || true
fi
if [[ -f logs/cloudflared.pid ]]; then
  kill "$(cat logs/cloudflared.pid)" 2>/dev/null || true
fi

echo "-> QR kurulum sunucusu :8787"
nohup python3 "$ROOT_DIR/scripts/mobile-setup-server.py" >logs/setup-server.log 2>&1 &
echo $! >logs/setup-server.pid

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

echo "-> Cloudflare tunnel"
nohup "$CF" tunnel --url http://127.0.0.1:8787 --no-autoupdate >logs/cloudflared.log 2>&1 &
echo $! >logs/cloudflared.pid

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
echo " OTOTEXT — TELEFONDA AÇ:"
echo " $URL"
echo "============================================"
echo "WhatsApp → Bağlı Cihazlar → QR okut → bot kendi kurulur"
echo "Müşteri ID_INSTANCE / API_TOKEN girmez."
