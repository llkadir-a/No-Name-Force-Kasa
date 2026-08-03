#!/usr/bin/env python3
"""Mobile-friendly one-page setup for Green API + n8n.
Opens on phone via Cloudflare tunnel. Saves credentials, validates API,
restarts n8n, imports & activates workflows.
"""
from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
LOGS = ROOT / "logs"
LOGS.mkdir(exist_ok=True)
PORT = int(os.environ.get("SETUP_PORT", "8787"))
N8N_PORT = int(os.environ.get("N8N_PORT", "5678"))

HTML = """<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1"/>
<title>Green API Kurulum</title>
<style>
  :root { --bg:#0b0f14; --card:#151b24; --text:#e8eef7; --muted:#93a0b4; --acc:#3ddc97; --danger:#ff6b6b; --line:#243041; }
  * { box-sizing: border-box; }
  body { margin:0; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif; background:radial-gradient(1200px 600px at 10% -10%, #1a2740, var(--bg)); color:var(--text); min-height:100vh; }
  .wrap { max-width:560px; margin:0 auto; padding:24px 16px 48px; }
  h1 { font-size:1.45rem; margin:0 0 6px; }
  p { color:var(--muted); margin:0 0 18px; line-height:1.45; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:16px; padding:16px; }
  label { display:block; font-size:.82rem; color:var(--muted); margin:12px 0 6px; }
  input, textarea { width:100%; border:1px solid var(--line); background:#0f141c; color:var(--text); border-radius:12px; padding:12px 14px; font-size:16px; }
  textarea { min-height:72px; resize:vertical; }
  button { width:100%; margin-top:18px; border:0; border-radius:12px; padding:14px; font-size:1rem; font-weight:700; background:var(--acc); color:#062418; }
  button:disabled { opacity:.55; }
  .status { margin-top:14px; white-space:pre-wrap; font-family:ui-monospace, SFMono-Regular, Menlo, monospace; font-size:.78rem; background:#0f141c; border-radius:12px; padding:12px; border:1px solid var(--line); max-height:45vh; overflow:auto; }
  .ok { color:var(--acc); }
  .err { color:var(--danger); }
  .hint { font-size:.78rem; color:var(--muted); margin-top:10px; }
</style>
</head>
<body>
  <div class="wrap">
    <h1>WhatsApp Green API Kurulum</h1>
    <p>Telefondan tek seferlik form. Kaydedince sistem kendini ayarlar, doğrular ve workflow’ları aktif eder.</p>
    <div class="card">
      <form id="f">
        <label>ID_INSTANCE</label>
        <input name="ID_INSTANCE" required placeholder="örn. 7103xxxxxx" autocomplete="off"/>
        <label>API_TOKEN</label>
        <input name="API_TOKEN" required placeholder="Green API apiTokenInstance" autocomplete="off"/>
        <label>SOURCE_GROUP_ID (Senaryo 2 kaynak)</label>
        <input name="SOURCE_GROUP_ID" placeholder="120363...@g.us"/>
        <label>TARGET_GROUP_ID (Senaryo 2 hedef)</label>
        <input name="TARGET_GROUP_ID" placeholder="120363...@g.us"/>
        <label>Broadcast mesajı (Senaryo 1)</label>
        <textarea name="BROADCAST_MESSAGE">Merhaba! Green API n8n broadcast mesaji.</textarea>
        <label>Grup chatId listesi (Satır başına 1 — Senaryo 1)</label>
        <textarea name="GROUP_CHAT_IDS" placeholder="120363aaa@g.us&#10;120363bbb@g.us"></textarea>
        <button type="submit" id="btn">Kur ve Aktif Et</button>
      </form>
      <div class="hint">Green API konsolundan Instance ID + Token kopyala. QR ile WhatsApp bağlı olmalı.</div>
      <div id="out" class="status" hidden></div>
    </div>
  </div>
<script>
const f=document.getElementById('f');
const out=document.getElementById('out');
const btn=document.getElementById('btn');
f.addEventListener('submit', async (e)=>{
  e.preventDefault();
  btn.disabled=true; out.hidden=false; out.className='status'; out.textContent='Çalışıyor...';
  const fd=new FormData(f);
  const body=Object.fromEntries(fd.entries());
  try{
    const r=await fetch('/api/setup',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    const j=await r.json();
    out.className='status '+(j.ok?'ok':'err');
    out.textContent=(j.ok?'OK\\n':'HATA\\n')+(j.log||j.error||JSON.stringify(j,null,2));
  }catch(err){
    out.className='status err'; out.textContent=String(err);
  }finally{ btn.disabled=false; }
});
</script>
</body>
</html>
"""


def read_env() -> dict[str, str]:
    data: dict[str, str] = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            if not line or line.strip().startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            data[k.strip()] = v
    return data


def write_env(updates: dict[str, str]) -> None:
    data = read_env()
    data.update({k: str(v) for k, v in updates.items() if v is not None})
    # Keep known order
    keys = [
        "ID_INSTANCE",
        "API_TOKEN",
        "SOURCE_GROUP_ID",
        "TARGET_GROUP_ID",
        "BROADCAST_MESSAGE",
        "N8N_HOST",
        "N8N_PORT",
        "N8N_PROTOCOL",
        "WEBHOOK_URL",
        "GENERIC_TIMEZONE",
        "TZ",
        "N8N_ENCRYPTION_KEY",
        "N8N_USER_MANAGEMENT_JWT_SECRET",
        "N8N_OWNER_EMAIL",
        "N8N_OWNER_PASSWORD",
        "N8N_OWNER_FIRST_NAME",
        "N8N_OWNER_LAST_NAME",
    ]
    lines = []
    seen = set()
    for k in keys:
        if k in data:
            lines.append(f"{k}={data[k]}")
            seen.add(k)
    for k, v in data.items():
        if k not in seen:
            lines.append(f"{k}={v}")
    ENV_PATH.write_text("\n".join(lines) + "\n")


def http_json(method: str, url: str, body: dict | None = None, headers: dict | None = None, cookies: str | None = None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    if cookies:
        req.add_header("Cookie", cookies)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
            set_cookie = resp.headers.get_all("Set-Cookie") or []
            return resp.status, (json.loads(raw) if raw else {}), set_cookie
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            payload = json.loads(raw) if raw else {}
        except Exception:
            payload = {"raw": raw}
        return e.code, payload, []


def green_api_state(instance: str, token: str) -> tuple[bool, str]:
    url = f"https://api.green-api.com/waInstance{instance}/getStateInstance/{token}"
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            payload = json.loads(resp.read().decode())
            state = payload.get("stateInstance", "")
            return state == "authorized", f"stateInstance={state} body={payload}"
    except Exception as e:
        return False, str(e)


def update_scenario1_groups(chat_ids: list[str], message: str) -> None:
    path = ROOT / "n8n-workflows" / "scenario-1-scheduled-group-broadcast.json"
    data = json.loads(path.read_text())
    # find code node
    for node in data.get("nodes", []):
        if node.get("name") == "Grup Listesi Oluştur":
            ids_js = ",\n  ".join(json.dumps(x) for x in chat_ids)
            node["parameters"]["jsCode"] = f"""const message = $env.BROADCAST_MESSAGE || {json.dumps(message)};

const groupChatIds = [
  {ids_js}
];

return groupChatIds.map((chatId, index) => ({{
  json: {{
    index: index + 1,
    chatId,
    message
  }}
}}));"""
            break
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def restart_n8n() -> str:
    log: list[str] = []
    env = read_env()
    pid_file = LOGS / "n8n.pid"
    if pid_file.exists():
        try:
            old = int(pid_file.read_text().strip())
            os.kill(old, signal.SIGTERM)
            log.append(f"stopped old pid {old}")
            time.sleep(2)
        except Exception as e:
            log.append(f"stop note: {e}")
    # start
    n8n_bin = ROOT / "node_modules" / ".bin" / "n8n"
    child_env = os.environ.copy()
    child_env.update(
        {
            "N8N_USER_FOLDER": str(ROOT / ".n8n-data"),
            "N8N_HOST": env.get("N8N_HOST", "localhost"),
            "N8N_PORT": env.get("N8N_PORT", str(N8N_PORT)),
            "N8N_PROTOCOL": env.get("N8N_PROTOCOL", "http"),
            "WEBHOOK_URL": env.get("WEBHOOK_URL", f"http://localhost:{N8N_PORT}/"),
            "GENERIC_TIMEZONE": env.get("GENERIC_TIMEZONE", "Europe/Istanbul"),
            "TZ": env.get("TZ", "Europe/Istanbul"),
            "N8N_ENCRYPTION_KEY": env.get("N8N_ENCRYPTION_KEY", ""),
            "N8N_USER_MANAGEMENT_JWT_SECRET": env.get("N8N_USER_MANAGEMENT_JWT_SECRET", ""),
            "N8N_BLOCK_ENV_ACCESS_IN_NODE": "false",
            "ID_INSTANCE": env.get("ID_INSTANCE", ""),
            "API_TOKEN": env.get("API_TOKEN", ""),
            "SOURCE_GROUP_ID": env.get("SOURCE_GROUP_ID", ""),
            "TARGET_GROUP_ID": env.get("TARGET_GROUP_ID", ""),
            "BROADCAST_MESSAGE": env.get("BROADCAST_MESSAGE", ""),
        }
    )
    out = open(LOGS / "n8n.log", "a")
    proc = subprocess.Popen(
        [str(n8n_bin), "start"],
        cwd=str(ROOT),
        env=child_env,
        stdout=out,
        stderr=out,
        start_new_session=True,
    )
    pid_file.write_text(str(proc.pid))
    log.append(f"started n8n pid {proc.pid}")
    # wait health
    for i in range(60):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{N8N_PORT}/healthz", timeout=2) as r:
                if r.status == 200:
                    log.append(f"healthy after {i+1} checks")
                    return "\n".join(log)
        except Exception:
            time.sleep(1)
    raise RuntimeError("n8n did not become healthy\n" + "\n".join(log))


def n8n_login_cookie() -> str:
    env = read_env()
    code, payload, cookies = http_json(
        "POST",
        f"http://127.0.0.1:{N8N_PORT}/rest/login",
        {
            "emailOrLdapLoginId": env.get("N8N_OWNER_EMAIL", "admin@localhost.local"),
            "password": env.get("N8N_OWNER_PASSWORD", "ChangeMe_Admin_123!"),
        },
    )
    if code >= 400:
        raise RuntimeError(f"login failed {code}: {payload}")
    # join cookies
    jar = []
    for c in cookies:
        jar.append(c.split(";", 1)[0])
    return "; ".join(jar)


def import_and_activate(cookie: str) -> str:
    lines = []
    # CLI import (more reliable for file)
    env = read_env()
    child_env = os.environ.copy()
    child_env["N8N_USER_FOLDER"] = str(ROOT / ".n8n-data")
    child_env["N8N_ENCRYPTION_KEY"] = env.get("N8N_ENCRYPTION_KEY", "")
    child_env["N8N_BLOCK_ENV_ACCESS_IN_NODE"] = "false"
    for wf in [
        ROOT / "n8n-workflows/scenario-1-scheduled-group-broadcast.json",
        ROOT / "n8n-workflows/scenario-2-sync-group-participants.json",
    ]:
        # ensure id
        data = json.loads(wf.read_text())
        if not data.get("id"):
            import uuid

            data["id"] = str(uuid.uuid4())
            data["versionId"] = str(uuid.uuid4())
            wf.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        r = subprocess.run(
            [str(ROOT / "node_modules/.bin/n8n"), "import:workflow", f"--input={wf}"],
            cwd=str(ROOT),
            env=child_env,
            capture_output=True,
            text=True,
        )
        lines.append(f"import {wf.name}: rc={r.returncode} {r.stdout.strip()} {r.stderr.strip()}")

    # list + activate via API
    code, payload, _ = http_json("GET", f"http://127.0.0.1:{N8N_PORT}/rest/workflows", cookies=cookie)
    workflows = payload.get("data") if isinstance(payload, dict) else payload
    if isinstance(workflows, dict):
        workflows = workflows.get("data") or workflows.get("workflows") or []
    for wf in workflows or []:
        wid = wf.get("id")
        name = wf.get("name")
        # fetch full
        c2, full, _ = http_json("GET", f"http://127.0.0.1:{N8N_PORT}/rest/workflows/{wid}", cookies=cookie)
        body = full.get("data", full)
        body["active"] = True
        # n8n 2.x may use activate endpoint
        c3, res, _ = http_json(
            "POST",
            f"http://127.0.0.1:{N8N_PORT}/rest/workflows/{wid}/activate",
            {},
            cookies=cookie,
        )
        if c3 >= 400:
            # fallback patch/put
            c3, res, _ = http_json(
                "PATCH",
                f"http://127.0.0.1:{N8N_PORT}/rest/workflows/{wid}",
                {"active": True},
                cookies=cookie,
            )
        lines.append(f"activate {name} ({wid}): HTTP {c3} {json.dumps(res)[:180]}")
    return "\n".join(lines)


def run_setup(payload: dict) -> dict:
    logs: list[str] = []
    instance = (payload.get("ID_INSTANCE") or "").strip()
    token = (payload.get("API_TOKEN") or "").strip()
    if not instance or not token:
        return {"ok": False, "error": "ID_INSTANCE and API_TOKEN required"}

    source = (payload.get("SOURCE_GROUP_ID") or "KAYNAK_GRUP_ID@g.us").strip()
    target = (payload.get("TARGET_GROUP_ID") or "HEDEF_GRUP_ID@g.us").strip()
    message = (payload.get("BROADCAST_MESSAGE") or "Merhaba! Green API n8n broadcast mesaji.").strip()
    raw_groups = (payload.get("GROUP_CHAT_IDS") or "").strip()
    groups = [g.strip() for g in re.split(r"[\n,;]+", raw_groups) if g.strip()]

    logs.append("1) Saving .env")
    write_env(
        {
            "ID_INSTANCE": instance,
            "API_TOKEN": token,
            "SOURCE_GROUP_ID": source,
            "TARGET_GROUP_ID": target,
            "BROADCAST_MESSAGE": message,
        }
    )

    if groups:
        logs.append(f"2) Updating scenario-1 with {len(groups)} groups")
        # pad/truncate to keep at least provided list
        update_scenario1_groups(groups, message)
    else:
        logs.append("2) No group list provided — keeping existing placeholders")

    logs.append("3) Validating Green API")
    ok, detail = green_api_state(instance, token)
    logs.append(detail)
    if not ok:
        return {"ok": False, "error": "Green API not authorized / invalid credentials", "log": "\n".join(logs)}

    logs.append("4) Restarting n8n with credentials")
    logs.append(restart_n8n())

    logs.append("5) Login + import/activate")
    cookie = n8n_login_cookie()
    logs.append(import_and_activate(cookie))

    logs.append("DONE")
    return {"ok": True, "log": "\n".join(logs)}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print("[setup]", fmt % args)

    def _send(self, code: int, body: bytes, content_type: str):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, HTML.encode(), "text/html; charset=utf-8")
            return
        if self.path == "/health":
            self._send(200, b'{"ok":true}', "application/json")
            return
        self._send(404, b"not found", "text/plain")

    def do_POST(self):
        if self.path != "/api/setup":
            self._send(404, b"not found", "text/plain")
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode()
        ctype = self.headers.get("Content-Type", "")
        if "application/json" in ctype:
            payload = json.loads(raw or "{}")
        else:
            payload = {k: v[0] for k, v in parse_qs(raw).items()}
        try:
            result = run_setup(payload)
            code = 200 if result.get("ok") else 400
            self._send(code, json.dumps(result).encode(), "application/json")
        except Exception as e:
            self._send(500, json.dumps({"ok": False, "error": str(e)}).encode(), "application/json")


def main():
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Mobile setup server on http://0.0.0.0:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
