#!/usr/bin/env python3
"""Ototext license create / verify (HMAC)."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
import uuid
from pathlib import Path
from typing import Any

SELLER_DIR = Path(__file__).resolve().parent
ROOT = SELLER_DIR.parent
CUSTOMERS_PATH = SELLER_DIR / "customers.json"
SECRET_PATH = SELLER_DIR / ".license-secret"


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def b64url_decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def get_secret() -> str:
    env = os.environ.get("OTOTEXT_LICENSE_SECRET", "").strip()
    if env:
        return env
    if SECRET_PATH.exists():
        return SECRET_PATH.read_text().strip()
    secret = secrets.token_hex(32)
    SECRET_PATH.write_text(secret + "\n")
    try:
        SECRET_PATH.chmod(0o600)
    except Exception:
        pass
    return secret


def load_customers() -> dict[str, Any]:
    if not CUSTOMERS_PATH.exists():
        return {"customers": []}
    return json.loads(CUSTOMERS_PATH.read_text())


def save_customers(data: dict[str, Any]) -> None:
    CUSTOMERS_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def sign_payload(payload: dict[str, Any], secret: str | None = None) -> str:
    secret = secret or get_secret()
    body = b64url(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode())
    sig = b64url(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{sig}"


def verify_license(token: str, secret: str | None = None) -> dict[str, Any]:
    secret = secret or get_secret()
    if not token or "." not in token:
        raise ValueError("Geçersiz lisans formatı")
    body, sig = token.strip().split(".", 1)
    expect = b64url(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(expect, sig):
        raise ValueError("Lisans imzası geçersiz")
    payload = json.loads(b64url_decode(body).decode())
    if payload.get("revoked"):
        raise ValueError("Lisans iptal edilmiş")
    exp = int(payload.get("exp") or 0)
    if exp and time.time() > exp:
        raise ValueError("Lisans süresi dolmuş")
    return payload


def create_license(
    name: str,
    email: str = "",
    days: int = 365,
    plan: str = "standard",
    note: str = "",
) -> dict[str, Any]:
    now = int(time.time())
    jti = str(uuid.uuid4())
    payload = {
        "jti": jti,
        "name": name,
        "email": email,
        "plan": plan,
        "iat": now,
        "exp": now + max(1, int(days)) * 86400,
        "product": "ototext",
        "note": note,
    }
    key = sign_payload(payload)
    data = load_customers()
    row = {
        "jti": jti,
        "name": name,
        "email": email,
        "plan": plan,
        "days": days,
        "note": note,
        "createdAt": now,
        "expiresAt": payload["exp"],
        "revoked": False,
        "licenseKey": key,
    }
    data.setdefault("customers", []).append(row)
    save_customers(data)
    return row


def revoke_license(jti: str) -> bool:
    data = load_customers()
    found = False
    for c in data.get("customers", []):
        if c.get("jti") == jti:
            c["revoked"] = True
            found = True
            # re-sign revoked token marker is local registry only;
            # sold keys remain cryptographically valid until expiry unless
            # you rotate secret. Registry revoke blocks kit rebuild / status.
    if found:
        save_customers(data)
    return found


def license_status(token: str) -> dict[str, Any]:
    try:
        payload = verify_license(token)
        data = load_customers()
        row = next((c for c in data.get("customers", []) if c.get("jti") == payload.get("jti")), None)
        if row and row.get("revoked"):
            return {"ok": False, "error": "Lisans satıcı panelinden iptal edilmiş", "payload": payload}
        left = max(0, int(payload.get("exp", 0) - time.time()))
        return {
            "ok": True,
            "payload": payload,
            "daysLeft": left // 86400,
            "customer": row,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Ototext lisans araçları")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("create", help="Yeni lisans üret")
    c.add_argument("--name", required=True)
    c.add_argument("--email", default="")
    c.add_argument("--days", type=int, default=365)
    c.add_argument("--plan", default="standard")
    c.add_argument("--note", default="")

    sub.add_parser("list", help="Müşteri/lisans listesi")

    r = sub.add_parser("revoke", help="Lisans iptal (jti)")
    r.add_argument("--jti", required=True)

    v = sub.add_parser("verify", help="Lisans doğrula")
    v.add_argument("--key", required=True)

    args = ap.parse_args()
    if args.cmd == "create":
        row = create_license(args.name, args.email, args.days, args.plan, args.note)
        print(json.dumps(row, indent=2, ensure_ascii=False))
        print("\nLICENSE_KEY=" + row["licenseKey"])
    elif args.cmd == "list":
        data = load_customers()
        for c in data.get("customers", []):
            status = "REVOKED" if c.get("revoked") else "OK"
            print(f"{c['jti'][:8]} | {status} | {c.get('name')} | {c.get('email')} | plan={c.get('plan')} | exp={c.get('expiresAt')}")
    elif args.cmd == "revoke":
        ok = revoke_license(args.jti)
        print("revoked" if ok else "not found")
    elif args.cmd == "verify":
        print(json.dumps(license_status(args.key), indent=2, ensure_ascii=False))
