#!/usr/bin/env python3
"""Satıcı paneli — lisans üret, listele, müşteri kit hazırla."""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from license import (
    SECRET_PATH,
    create_license,
    get_secret,
    license_status,
    load_customers,
    revoke_license,
    save_customers,
)

SELLER_DIR = Path(__file__).resolve().parent
ROOT = SELLER_DIR.parent
PORT = int(os.environ.get("SELLER_PORT", "8790"))
STATE_PATH = ROOT / "data" / "ototext-state.json"

# Admin panelden patchlenebilir üst alanlar (her şeyi buradan yönet)
BOT_PATCHABLE = {
    "admins",
    "botWid",
    "mainPrefix",
    "prefixes",
    "numbers",
    "activeNumberId",
    "broadcast",
    "dm",
    "mining",
    "filters",
    "blacklist",
    "invites",
    "logGroupId",
    "pending",
    "guard",
    "healthWatch",
    "daily",
    "stats",
}

HTML = """<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Ototext Satış Paneli</title>
<style>
  :root { --bg:#0b0f14; --card:#151b24; --text:#e8eef7; --muted:#93a0b4; --acc:#3ddc97; --line:#243041; --danger:#ff6b6b; }
  body { margin:0; font-family: ui-sans-serif, system-ui, sans-serif; background:radial-gradient(1000px 500px at 0% 0%, #1a2740, var(--bg)); color:var(--text); }
  .wrap { max-width:960px; margin:0 auto; padding:24px 16px 48px; }
  h1 { margin:0 0 8px; font-size:1.5rem; }
  p { color:var(--muted); }
  .grid { display:grid; gap:16px; }
  @media(min-width:800px){ .grid { grid-template-columns: 1fr 1fr; } }
  .card { background:var(--card); border:1px solid var(--line); border-radius:16px; padding:16px; }
  label { display:block; font-size:.8rem; color:var(--muted); margin:10px 0 6px; }
  input, select { width:100%; box-sizing:border-box; border:1px solid var(--line); background:#0f141c; color:var(--text); border-radius:12px; padding:11px 12px; font-size:16px; }
  button { margin-top:10px; width:100%; border:0; border-radius:12px; padding:12px; font-weight:700; background:var(--acc); color:#062418; cursor:pointer; }
  button.secondary { background:#2a3545; color:var(--text); }
  button.danger { background:var(--danger); color:#1a0505; }
  table { width:100%; border-collapse:collapse; font-size:.85rem; }
  th, td { text-align:left; padding:8px 6px; border-bottom:1px solid var(--line); vertical-align:top; }
  .key { word-break:break-all; font-family:ui-monospace,monospace; font-size:.72rem; color:#b7f7d4; }
  .ok { color:var(--acc); } .bad { color:var(--danger); }
  .muted { color:var(--muted); font-size:.8rem; }
  .actions { display:grid; gap:6px; min-width:120px; }
</style>
</head>
<body>
<div class="wrap">
  <h1>Ototext Satış Paneli</h1>
  <p>Aynı sistemi sat: lisans üret → ZIP kit indir → müşteri kendi Green API’siyle kurar.</p>
  <div class="grid">
    <div class="card">
      <h3>Yeni lisans</h3>
      <form id="create">
        <label>Müşteri adı</label>
        <input name="name" required placeholder="Ahmet Yılmaz"/>
        <label>E-posta</label>
        <input name="email" type="email" placeholder="musteri@mail.com"/>
        <label>Plan</label>
        <select name="plan">
          <option value="standard">standard</option>
          <option value="pro">pro</option>
          <option value="lifetime">lifetime</option>
        </select>
        <label>Gün (lifetime için 36500)</label>
        <input name="days" type="number" value="365" min="1"/>
        <label>Not</label>
        <input name="note" placeholder="Telegram / ödeme no"/>
        <label>Green API ID_INSTANCE (müşteri QR okutacak — API görmez)</label>
        <input name="idInstance" placeholder="1101...."/>
        <label>Green API API_TOKEN</label>
        <input name="apiToken" placeholder="apiTokenInstance"/>
        <button type="submit">Lisans Üret + Kit</button>
      </form>
      <pre id="createOut" class="muted"></pre>
    </div>
    <div class="card">
      <h3>Nasıl satarsın?</h3>
      <p class="muted">1) Lisans üret<br/>2) Listeden <b>ZIP Kit</b> indir<br/>3) ZIP’i müşteriye gönder<br/>4) Müşteri Green API + kurulum yapar → senin botunla aynı sistem</p>
      <p class="muted">Detay: repo kökünde <code>SATIS.md</code></p>
      <form id="kit">
        <label>JTI ile kit (opsiyonel)</label>
        <input name="jti" placeholder="uuid"/>
        <button type="submit" class="secondary">ZIP Kit Üret</button>
      </form>
      <pre id="kitOut" class="muted"></pre>
    </div>
  </div>
  <div class="card" style="margin-top:16px;">
    <h3>Müşteriler</h3>
    <div id="list"></div>
  </div>
</div>
<script>
async function downloadKit(jti){
  kitOut.textContent = 'Hazırlanıyor...';
  const r = await fetch('/api/kit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({jti})});
  if((r.headers.get('content-type')||'').includes('application/zip')){
    const blob = await r.blob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = (jti||'ototext').slice(0,8) + '-kit.zip';
    a.click();
    kitOut.textContent = 'ZIP indirildi: ' + a.download;
  } else {
    const j = await r.json();
    kitOut.textContent = j.error || JSON.stringify(j);
  }
}
async function refresh(){
  const r = await fetch('/api/customers');
  const j = await r.json();
  const rows = (j.customers||[]).slice().reverse();
  if(!rows.length){ list.innerHTML='<p class="muted">Henüz müşteri yok.</p>'; return; }
  let html = '<table><tr><th>Müşteri</th><th>Durum</th><th>JTI / Key</th><th></th></tr>';
  for(const c of rows){
    const st = c.revoked ? '<span class="bad">IPTAL</span>' : '<span class="ok">AKTIF</span>';
    html += `<tr>
      <td><b>${c.name||'-'}</b><br/><span class="muted">${c.email||''}<br/>${c.plan} / ${c.days}g</span></td>
      <td>${st}</td>
      <td><div class="muted">${c.jti}</div><div class="key">${c.licenseKey||''}</div></td>
      <td class="actions">
        <button class="secondary" onclick="downloadKit('${c.jti}')">ZIP Kit</button>
        <button class="secondary" onclick="navigator.clipboard.writeText('${c.licenseKey||''}')">Key</button>
        ${c.revoked?'':`<button class="danger" onclick="revoke('${c.jti}')">İptal</button>`}
      </td>
    </tr>`;
  }
  html += '</table>';
  list.innerHTML = html;
}
async function revoke(jti){
  if(!confirm('Lisans iptal edilsin mi?')) return;
  await fetch('/api/revoke',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({jti})});
  refresh();
}
create.addEventListener('submit', async (e)=>{
  e.preventDefault();
  const body = Object.fromEntries(new FormData(create).entries());
  body.days = Number(body.days||365);
  const r = await fetch('/api/create',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const j = await r.json();
  if(j.ok){
    createOut.textContent = 'OK\\nLICENSE_KEY='+j.customer.licenseKey+'\\nJTI='+j.customer.jti;
    // kit isteğine Green API bilgisini de gönder
    kitOut.textContent = 'Kit hazırlanıyor...';
    const kr = await fetch('/api/kit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
      jti: j.customer.jti,
      idInstance: body.idInstance||'',
      apiToken: body.apiToken||'',
    })});
    if((kr.headers.get('content-type')||'').includes('application/zip')){
      const blob = await kr.blob();
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = (j.customer.jti||'ototext').slice(0,8) + '-kit.zip';
      a.click();
      kitOut.textContent = 'ZIP indirildi.';
    } else {
      const kj = await kr.json();
      kitOut.textContent = kj.error || JSON.stringify(kj);
    }
  } else {
    createOut.textContent = 'HATA\\n'+(j.error||'');
  }
  refresh();
});
kit.addEventListener('submit', async (e)=>{
  e.preventDefault();
  const body = Object.fromEntries(new FormData(kit).entries());
  await downloadKit(body.jti);
});
refresh();
</script>
</body>
</html>
"""


def build_customer_kit(jti: str, id_instance: str = "", api_token: str = "") -> Path:
    data = load_customers()
    row = next((c for c in data.get("customers", []) if c.get("jti") == jti), None)
    if not row:
        raise ValueError("JTI bulunamadı")
    if row.get("revoked"):
        raise ValueError("Lisans iptal edilmiş")

    # müşteri kaydında saklanan Green API (varsa)
    id_instance = (id_instance or row.get("idInstance") or "").strip()
    api_token = (api_token or row.get("apiToken") or "").strip()
    if id_instance or api_token:
        for c in data.get("customers", []):
            if c.get("jti") == jti:
                if id_instance:
                    c["idInstance"] = id_instance
                if api_token:
                    c["apiToken"] = api_token
                break
        save_customers(data)

    out_dir = SELLER_DIR / "kits"
    out_dir.mkdir(exist_ok=True)
    zip_path = out_dir / f"ototext-{jti[:8]}-kit.zip"
    secret = get_secret()

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        root = tmp_path / "ototext"
        root.mkdir()

        def copy_path(rel: str, ignore=None):
            src = ROOT / rel
            dst = root / rel
            if not src.exists():
                return
            if src.is_dir():
                shutil.copytree(
                    src,
                    dst,
                    ignore=ignore
                    or shutil.ignore_patterns(
                        "__pycache__",
                        "*.pyc",
                        "node_modules",
                        ".n8n-data",
                        "logs",
                        "ototext-state.json",
                        "worker-workflow-id.txt",
                    ),
                )
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)

        for rel in [
            "docker-compose.yml",
            ".env.example",
            "package.json",
            "README.md",
            "SATIS.md",
            "n8n-workflows",
            "scripts",
            "data",
        ]:
            copy_path(rel)

        # müşteriye satıcı paneli / gizli dosyalar gitmesin
        for bad in [
            root / "seller",
            root / "data" / "ototext-state.json",
            root / ".env",
            root / "node_modules",
            root / ".n8n-data",
            root / "logs",
            root / "LICENSE_KEY.txt",
            root / "LICENSE_SECRET.txt",
        ]:
            if bad.exists():
                if bad.is_dir():
                    shutil.rmtree(bad, ignore_errors=True)
                else:
                    bad.unlink(missing_ok=True)

        # verify için license modülü
        (root / "scripts").mkdir(exist_ok=True)
        shutil.copy2(SELLER_DIR / "license.py", root / "scripts" / "license_lib.py")

        env = (ROOT / ".env.example").read_text(encoding="utf-8")
        replacements = {
            "LICENSE_KEY=": f"LICENSE_KEY={row['licenseKey']}",
            "OTOTEXT_LICENSE_SECRET=": f"OTOTEXT_LICENSE_SECRET={secret}",
            "LICENSE_SKIP=": "LICENSE_SKIP=",
        }
        if id_instance:
            replacements["ID_INSTANCE="] = f"ID_INSTANCE={id_instance}"
        if api_token:
            replacements["API_TOKEN="] = f"API_TOKEN={api_token}"
        for key, val in replacements.items():
            if key in env:
                lines = []
                for line in env.splitlines():
                    if line.startswith(key):
                        lines.append(val)
                    else:
                        lines.append(line)
                env = "\n".join(lines) + "\n"
            else:
                env += f"\n{val}\n"
        (root / ".env.example").write_text(env, encoding="utf-8")
        (root / ".env").write_text(env, encoding="utf-8")
        (root / "LICENSE_KEY.txt").write_text(row["licenseKey"] + "\n", encoding="utf-8")
        (root / "LICENSE_SECRET.txt").write_text(secret + "\n", encoding="utf-8")
        (root / "license.json").write_text(
            json.dumps(
                {
                    "key": row["licenseKey"],
                    "jti": row["jti"],
                    "customer": row.get("name"),
                    "plan": row.get("plan"),
                    "expires_at": row.get("expiresAt"),
                    "status": "active",
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        ga_note = (
            "Green API instance pakete gömülü — sen API girmezsin, sadece QR okutursun."
            if id_instance and api_token
            else "Satıcı henüz instance eklemediyse kurulum ekranındaki gelişmiş alana girmesi gerekir."
        )
        (root / "MUSTERI.md").write_text(
            f"""# Ototext — QR ile Kurulum

Merhaba {row.get('name') or ''},

Bu paket senin Ototext kopyan. **API / token uğraşma.**

{ga_note}

## Kurulum
```bash
bash scripts/start-mobile-setup.sh
```

Telefonda çıkan linki aç → **QR Kodunu Göster** → WhatsApp’tan okut.  
Okutunca bot kendi kurulur.

## Sonra
Bot numarasına yaz: `!yardim`  
Lisans: `!lisans`

Plan: {row.get('plan')}  
JTI: {row.get('jti')}
""",
            encoding="utf-8",
        )

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in root.rglob("*"):
                if f.is_file():
                    zf.write(f, f.relative_to(tmp_path).as_posix())
    return zip_path


def default_bot_state() -> dict:
    return {
        "admins": [],
        "botWid": "",
        "mainPrefix": "!",
        "prefixes": ["!"],
        "numbers": [],
        "activeNumberId": "",
        "broadcast": {
            "running": False,
            "text": "",
            "texts": [],
            "textIndex": 0,
            "intervalMin": 3,
            "index": 0,
            "sent": 0,
            "lastSendAt": 0,
            "startedAt": 0,
            "cycle": 0,
            "windowStart": "",
            "windowEnd": "",
        },
        "dm": {
            "running": False,
            "text": "",
            "groupId": "",
            "intervalMin": 3,
            "queue": [],
            "index": 0,
            "sent": 0,
            "failed": 0,
            "lastSendAt": 0,
            "startedAt": 0,
            "windowStart": "",
            "windowEnd": "",
        },
        "mining": {
            "running": False,
            "targetGroupId": "",
            "targetName": "",
            "members": 0,
            "addedToday": 0,
            "pending": 0,
            "totalTarget": 0,
            "durationMin": 0,
            "startedAt": 0,
            "lastAddAt": 0,
            "dayKey": "",
        },
        "filters": {"minUye": 0},
        "blacklist": [],
        "invites": [],
        "logGroupId": "",
        "pending": None,
        "guard": {
            "enabled": False,
            "groups": {},
            "stickerLimit": 4,
            "stickerWindowMs": 15000,
            "kickOnCall": True,
            "kickOnStickerSpam": True,
            "lockOnIncident": True,
            "protectAdmins": True,
            "stickerHits": {},
            "lockedGroups": {},
        },
        "healthWatch": {"byInstance": {}, "lastCheckAt": 0},
        "daily": {
            "dayKey": "",
            "broadcastSent": 0,
            "dmSent": 0,
            "errors": 0,
            "starts": 0,
            "stops": 0,
            "events": [],
        },
        "stats": {
            "commands": 0,
            "broadcastSent": 0,
            "dmSent": 0,
            "joins": 0,
            "startedAt": 0,
        },
    }


def load_bot_state() -> dict:
    if not STATE_PATH.is_file():
        state = default_bot_state()
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        save_bot_state(state)
        return state
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def save_bot_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(
        json.dumps(state, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _mask_secret(val: str) -> str:
    s = str(val or "")
    if len(s) <= 8:
        return "***" if s else ""
    return s[:3] + "***" + s[-4:]


def redact_bot_state(state: dict) -> dict:
    """GET yanıtında API token'ları maskele."""
    out = json.loads(json.dumps(state))
    nums = out.get("numbers")
    if isinstance(nums, list):
        for n in nums:
            if isinstance(n, dict) and n.get("apiToken"):
                n["apiTokenMasked"] = _mask_secret(n.get("apiToken"))
                n["apiToken"] = n["apiTokenMasked"]
    return out


def deep_merge(dst, src):
    if not isinstance(dst, dict) or not isinstance(src, dict):
        return src
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            deep_merge(dst[k], v)
        else:
            dst[k] = v
    return dst


def restore_masked_tokens(incoming_numbers, existing_numbers):
    """Panel maskeli token gönderirse eski token korunur."""
    if not isinstance(incoming_numbers, list):
        return incoming_numbers
    by_id = {}
    if isinstance(existing_numbers, list):
        for n in existing_numbers:
            if isinstance(n, dict) and n.get("id"):
                by_id[str(n["id"])] = n
            if isinstance(n, dict) and n.get("instanceId"):
                by_id[str(n["instanceId"])] = n
    for n in incoming_numbers:
        if not isinstance(n, dict):
            continue
        tok = str(n.get("apiToken") or "")
        if "***" in tok or tok == "":
            old = by_id.get(str(n.get("id") or "")) or by_id.get(str(n.get("instanceId") or ""))
            if old and old.get("apiToken"):
                n["apiToken"] = old["apiToken"]
        n.pop("apiTokenMasked", None)
    return incoming_numbers


def apply_bot_patch(patch: dict, *, replace: bool = False) -> dict:
    if not isinstance(patch, dict):
        raise ValueError("patch object olmalı")
    current = load_bot_state()
    if replace:
        base = default_bot_state()
        for k, v in patch.items():
            if k in BOT_PATCHABLE:
                base[k] = v
        if isinstance(base.get("numbers"), list):
            base["numbers"] = restore_masked_tokens(base["numbers"], current.get("numbers"))
        save_bot_state(base)
        return base

    for k, v in patch.items():
        if k not in BOT_PATCHABLE:
            continue
        if k == "numbers" and isinstance(v, list):
            current["numbers"] = restore_masked_tokens(v, current.get("numbers"))
        elif isinstance(v, dict) and isinstance(current.get(k), dict):
            deep_merge(current[k], v)
        else:
            current[k] = v
    save_bot_state(current)
    return current


def panic_local_bot() -> dict:
    """Yerel Ototext state — otox/dm/mining/pending durdur. Hesaba girmez."""
    if not STATE_PATH.is_file():
        return {"ok": False, "error": "ototext-state.json yok"}
    state = load_bot_state()
    for key in ("broadcast", "dm", "mining"):
        if isinstance(state.get(key), dict):
            state[key]["running"] = False
    state["pending"] = None
    save_bot_state(state)
    return {"ok": True, "message": "local panic applied", "stopped": ["broadcast", "dm", "mining", "pending"]}


def bot_action(action: str, body: dict | None = None) -> dict:
    body = body or {}
    state = load_bot_state()
    act = (action or "").strip().lower()
    if act == "panic":
        return panic_local_bot()
    if act == "stop_broadcast":
        state.setdefault("broadcast", {})["running"] = False
        save_bot_state(state)
        return {"ok": True, "action": act}
    if act == "stop_dm":
        state.setdefault("dm", {})["running"] = False
        save_bot_state(state)
        return {"ok": True, "action": act}
    if act == "stop_mining":
        state.setdefault("mining", {})["running"] = False
        save_bot_state(state)
        return {"ok": True, "action": act}
    if act == "start_broadcast":
        state.setdefault("broadcast", {})["running"] = True
        state["broadcast"]["startedAt"] = state["broadcast"].get("startedAt") or __import__("time").time() * 1000
        save_bot_state(state)
        return {"ok": True, "action": act}
    if act == "start_dm":
        state.setdefault("dm", {})["running"] = True
        save_bot_state(state)
        return {"ok": True, "action": act}
    if act == "clear_pending":
        state["pending"] = None
        save_bot_state(state)
        return {"ok": True, "action": act}
    if act == "clear_invites":
        state["invites"] = []
        save_bot_state(state)
        return {"ok": True, "action": act}
    if act == "clear_daily_events":
        state.setdefault("daily", {})["events"] = []
        save_bot_state(state)
        return {"ok": True, "action": act}
    if act == "set_log_group":
        gid = str(body.get("logGroupId") or "").strip()
        state["logGroupId"] = gid
        save_bot_state(state)
        return {"ok": True, "action": act, "logGroupId": gid}
    raise ValueError(f"bilinmeyen action: {action}")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print("[seller]", fmt % args)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, code: int, obj):
        raw = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self._cors()
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _html(self, html: str):
        raw = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def _read_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode()
        try:
            return json.loads(raw or "{}")
        except Exception:
            return {k: v[0] for k, v in parse_qs(raw).items()}

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html", "/admin", "/ototext-admin-panel.html"):
            p = ROOT / "ototext-admin-panel.html"
            if p.is_file():
                return self._html(p.read_text(encoding="utf-8"))
            return self._html(HTML)
        if path == "/sales":
            return self._html(HTML)
        if path == "/api/customers":
            return self._json(200, load_customers())
        if path == "/api/bot/state":
            try:
                state = load_bot_state()
                return self._json(
                    200,
                    {
                        "ok": True,
                        "state": redact_bot_state(state),
                        "path": str(STATE_PATH),
                        "patchable": sorted(BOT_PATCHABLE),
                    },
                )
            except Exception as e:
                return self._json(500, {"ok": False, "error": str(e)})
        if path == "/health":
            return self._json(
                200,
                {
                    "ok": True,
                    "botState": STATE_PATH.is_file(),
                    "endpoints": [
                        "/api/bot/state",
                        "/api/bot/patch",
                        "/api/bot/action",
                        "/api/panic",
                        "/api/customers",
                    ],
                },
            )
        self._json(404, {"error": "not found"})

    def do_PATCH(self):
        return self._handle_bot_write()

    def do_PUT(self):
        return self._handle_bot_write(replace_default=True)

    def _handle_bot_write(self, replace_default: bool = False):
        path = urlparse(self.path).path
        body = self._read_body()
        try:
            if path in ("/api/bot/state", "/api/bot/patch"):
                replace = bool(body.get("replace")) if isinstance(body, dict) else False
                if replace_default and "replace" not in body:
                    replace = True
                patch = body.get("patch") if isinstance(body.get("patch"), dict) else body
                if isinstance(patch, dict):
                    patch = {k: v for k, v in patch.items() if k not in ("replace", "patch", "ok")}
                state = apply_bot_patch(patch, replace=replace)
                return self._json(200, {"ok": True, "state": redact_bot_state(state)})
            self._json(404, {"error": "not found"})
        except Exception as e:
            self._json(400, {"ok": False, "error": str(e)})

    def do_POST(self):
        path = urlparse(self.path).path
        body = self._read_body()

        try:
            if path in ("/api/bot/state", "/api/bot/patch"):
                replace = bool(body.get("replace"))
                patch = body.get("patch") if isinstance(body.get("patch"), dict) else body
                if isinstance(patch, dict):
                    patch = {k: v for k, v in patch.items() if k not in ("replace", "patch", "ok")}
                state = apply_bot_patch(patch, replace=replace)
                return self._json(200, {"ok": True, "state": redact_bot_state(state)})
            if path == "/api/bot/action":
                return self._json(200, bot_action(body.get("action") or "", body))
            if path == "/api/panic":
                target = (body.get("target") or "local").strip()
                if target != "local":
                    return self._json(
                        400,
                        {
                            "ok": False,
                            "error": "Şimdilik sadece target=local. Uzak müşteri panic için heartbeat eklenecek.",
                        },
                    )
                return self._json(200, panic_local_bot())
            if path == "/api/create":
                row = create_license(
                    name=body.get("name") or "Musteri",
                    email=body.get("email") or "",
                    days=int(body.get("days") or 365),
                    plan=body.get("plan") or "standard",
                    note=body.get("note") or "",
                )
                # Green API’yi müşteri kaydına yaz (kit için)
                iid = (body.get("idInstance") or "").strip()
                at = (body.get("apiToken") or "").strip()
                if iid or at:
                    data = load_customers()
                    for c in data.get("customers", []):
                        if c.get("jti") == row["jti"]:
                            if iid:
                                c["idInstance"] = iid
                            if at:
                                c["apiToken"] = at
                            row = c
                            break
                    save_customers(data)
                return self._json(200, {"ok": True, "customer": row})
            if path == "/api/revoke":
                ok = revoke_license(body.get("jti") or "")
                return self._json(200 if ok else 404, {"ok": ok})
            if path == "/api/kit":
                zpath = build_customer_kit(
                    body.get("jti") or "",
                    id_instance=(body.get("idInstance") or ""),
                    api_token=(body.get("apiToken") or ""),
                )
                data = zpath.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "application/zip")
                self.send_header("Content-Disposition", f'attachment; filename="{zpath.name}"')
                self.send_header("Content-Length", str(len(data)))
                self._cors()
                self.end_headers()
                self.wfile.write(data)
                return
            if path == "/api/verify":
                return self._json(200, license_status(body.get("key") or ""))
            self._json(404, {"error": "not found"})
        except Exception as e:
            self._json(400, {"ok": False, "error": str(e)})


def main():
    get_secret()
    print(f"Ototext Admin / Satış → http://127.0.0.1:{PORT}")
    print(f"Bot state API: /api/bot/state  |  panel: /  veya /admin")
    print(f"Secret dosyası: {SECRET_PATH}")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
