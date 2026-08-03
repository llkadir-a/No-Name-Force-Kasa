#!/usr/bin/env python3
"""Kurulum öncesi lisans kontrolü. Exit 0 = geçerli."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_dotenv_key(name: str) -> str:
    env_path = ROOT / ".env"
    if not env_path.is_file():
        return ""
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{name}="):
            return line.split("=", 1)[1].strip()
    return ""


def _read_key() -> str:
    key = (os.environ.get("LICENSE_KEY") or "").strip()
    if key:
        return key
    key = _load_dotenv_key("LICENSE_KEY")
    if key:
        return key
    key_file = ROOT / "LICENSE_KEY.txt"
    if key_file.is_file():
        return key_file.read_text(encoding="utf-8").strip()
    return ""


def _ensure_secret_env() -> None:
    if os.environ.get("OTOTEXT_LICENSE_SECRET", "").strip():
        return
    for path in (ROOT / "LICENSE_SECRET.txt", ROOT / "seller" / ".license-secret"):
        if path.is_file():
            os.environ["OTOTEXT_LICENSE_SECRET"] = path.read_text(encoding="utf-8").strip()
            return


def main() -> int:
    if os.environ.get("LICENSE_SKIP", "").strip().lower() in ("1", "true", "yes"):
        print("LICENSE_SKIP aktif — lisans kontrolü atlandı (geliştirici).")
        return 0

    key = _read_key()
    seller_dir = ROOT / "seller"
    # Ana geliştirici reposu: key yoksa satış paneli tarafında serbest bırak
    if not key and seller_dir.is_dir() and (seller_dir / "license.py").is_file():
        print("Geliştirici modu — LICENSE_KEY yok, satıcı reposu algılandı.")
        return 0

    if not key:
        print("HATA: LICENSE_KEY yok. Satıcıdan aldığın kurulum paketini kullan.")
        return 1

    _ensure_secret_env()
    sys.path.insert(0, str(seller_dir if (seller_dir / "license.py").is_file() else ROOT / "scripts"))
    try:
        # kit: scripts/license_lib.py — repo: seller/license.py
        try:
            from license import license_status  # type: ignore
        except Exception:
            from license_lib import license_status  # type: ignore
    except Exception as e:
        print(f"HATA: lisans modülü yüklenemedi: {e}")
        return 1

    status = license_status(key)
    if not status.get("ok"):
        print("HATA:", status.get("error") or "lisans geçersiz")
        return 1

    payload = status.get("payload") or {}
    print("Lisans OK")
    print(f"Müşteri: {payload.get('name')}")
    print(f"Plan: {payload.get('plan')}")
    print(f"Kalan gün: {status.get('daysLeft')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
