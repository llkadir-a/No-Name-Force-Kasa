#!/usr/bin/env bash
# Satıcı paneli — lisans üret, müşteri listesi, kurulum ZIP indir
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PORT="${SELLER_PORT:-8790}"

echo "=============================================="
echo "  Ototext Satıcı Paneli"
echo "  http://127.0.0.1:${PORT}"
echo "=============================================="
echo "Buradan:"
echo "  1) Müşteri adı + süre ile lisans üret"
echo "  2) Kurulum ZIP indir → müşteriye ver"
echo "  3) Gerekirse lisansı iptal et"
echo "=============================================="

exec python3 "$ROOT/seller/panel.py"
