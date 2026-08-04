#!/usr/bin/env bash
# Ototext Admin Control Center + satış paneli
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PORT="${SELLER_PORT:-8790}"

echo "=============================================="
echo "  Ototext Admin Control Center"
echo "  http://127.0.0.1:${PORT}"
echo "=============================================="
echo "Buradan:"
echo "  • QR ile WhatsApp bağla"
echo "  • Log / otox / DM / guard / numaralar"
echo "  • PANIC, lisans üret, ZIP kit"
echo "=============================================="
echo ""
echo "Başlatmak için bu komutu çalıştır:"
echo "  bash scripts/start-seller-panel.sh"
echo ""

exec python3 "$ROOT/seller/panel.py"
