#!/usr/bin/env python3
"""Ototext mobile setup — QR okut, bot açılsın (müşteri API uğraşmasın)."""
from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

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
<title>Ototext — QR ile Bağlan</title>
<style>
  :root { --bg:#0b0f14; --card:#151b24; --text:#e8eef7; --muted:#93a0b4; --acc:#3ddc97; --danger:#ff6b6b; --line:#243041; }
  * { box-sizing: border-box; }
  body { margin:0; font-family: ui-sans-serif, system-ui, sans-serif; background:radial-gradient(1200px 600px at 10% -10%, #1a2740, var(--bg)); color:var(--text); min-height:100vh; }
  .wrap { max-width:520px; margin:0 auto; padding:24px 16px 48px; }
  h1 { font-size:1.5rem; margin:0 0 6px; }
  p { color:var(--muted); margin:0 0 16px; line-height:1.45; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:16px; padding:16px; }
  label { display:block; font-size:.82rem; color:var(--muted); margin:12px 0 6px; }
  input { width:100%; border:1px solid var(--line); background:#0f141c; color:var(--text); border-radius:12px; padding:12px 14px; font-size:16px; }
  button { width:100%; margin-top:14px; border:0; border-radius:12px; padding:14px; font-size:1rem; font-weight:700; background:var(--acc); color:#062418; cursor:pointer; }
  button.secondary { background:#2a3545; color:var(--text); }
  button:disabled { opacity:.55; }
  .qrbox { margin:16px auto 8px; width:min(280px,80vw); aspect-ratio:1; background:#fff; border-radius:12px; display:flex; align-items:center; justify-content:center; overflow:hidden; }
  .qrbox img { width:100%; height:100%; object-fit:contain; }
  .status { margin-top:12px; white-space:pre-wrap; font-family:ui-monospace,monospace; font-size:.78rem; background:#0f141c; border-radius:12px; padding:12px; border:1px solid var(--line); max-height:40vh; overflow:auto; }
  .ok { color:var(--acc); } .err { color:var(--danger); }
  .hint { font-size:.8rem; color:var(--muted); margin-top:8px; line-height:1.4; }
  .step { font-weight:700; color:var(--acc); margin-bottom:8px; }
  details { margin-top:14px; color:var(--muted); font-size:.85rem; }
  details summary { cursor:pointer; }
  .hidden { display:none !important; }
</style>
</head>
<body>
  <div class="wrap">
    <h1>Ototext</h1>
    <p>WhatsApp’tan QR okut — sistem kendini kurar. API / token uğraşı yok.</p>
    <div class="card">
      <div id="bootMsg" class="hint">Hazırlanıyor...</div>

      <div id="panelNeedCreds" class="hidden">
        <div class="step">Satıcı kurulumu gerekli</div>
        <p class="hint">Bu pakette henüz Green API instance yok. Satıcı panelinden instance eklenmeli veya aşağıdaki gelişmiş alana girilmeli.</p>
      </div>

      <div id="panelQr">
        <div class="step" id="stepLabel">1) WhatsApp ile bağlan</div>
        <label>Komut yetkisi (senin numaran) — boş bırakırsan bot numarası admin olur</label>
        <input id="admin" placeholder="905xxxxxxxxx" autocomplete="tel"/>
        <button id="btnQr" type="button">QR Kodunu Göster</button>
        <div id="qrWrap" class="hidden">
          <div class="qrbox"><img id="qrImg" alt="QR"/></div>
          <p class="hint">WhatsApp → Bağlı Cihazlar → Cihaz Bağla → bu QR’ı okut.<br/>Kod ~20 sn’de yenilenir; okutunca otomatik devam eder.</p>
          <div id="stateLine" class="hint">Durum: bekleniyor…</div>
        </div>
        <button id="btnActivate" class="secondary hidden" type="button">Bağlandı — Botu Başlat</button>
      </div>

      <div id="out" class="status hidden"></div>

      <details>
        <summary>Gelişmiş (satıcı / teknik)</summary>
        <label>ID_INSTANCE</label>
        <input id="advId" autocomplete="off"/>
        <label>API_TOKEN</label>
        <input id="advToken" autocomplete="off"/>
        <button id="btnSaveCreds" class="secondary" type="button">Kaydet ve QR’a geç</button>
      </details>
    </div>
  </div>
<script>
let timer=null, activating=false;
const out=document.getElementById('out');
function show(msg, ok){ out.hidden=false; out.className='status '+(ok===true?'ok':ok===false?'err':''); out.textContent=msg; }
async function boot(){
  const r=await fetch('/api/boot'); const j=await r.json();
  document.getElementById('bootMsg').textContent = j.message || '';
  if(j.admin) document.getElementById('admin').value=j.admin;
  if(j.authorized){
    document.getElementById('stepLabel').textContent='WhatsApp zaten bağlı';
    document.getElementById('btnActivate').classList.remove('hidden');
    document.getElementById('stateLine').textContent='Durum: authorized';
  }
  if(!j.hasCreds && !j.canProvision){
    document.getElementById('panelNeedCreds').classList.remove('hidden');
  }
  if(j.idInstance) document.getElementById('advId').value=j.idInstance;
}
async function saveCreds(){
  const body={ID_INSTANCE:advId.value.trim(), API_TOKEN:advToken.value.trim()};
  const r=await fetch('/api/creds',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const j=await r.json();
  show(j.ok?'Kimlik kaydedildi. QR’a bas.':(j.error||'Hata'), !!j.ok);
  boot();
}
async function poll(){
  try{
    const r=await fetch('/api/qr'); const j=await r.json();
    if(j.qrDataUrl){ qrImg.src=j.qrDataUrl; qrWrap.classList.remove('hidden'); }
    stateLine.textContent='Durum: '+(j.state||j.type||'?')+(j.message&&!j.qrDataUrl?(' — '+j.message):'');
    if(j.authorized){
      clearInterval(timer); timer=null;
      stateLine.textContent='Durum: authorized — bot kuruluyor…';
      btnActivate.classList.remove('hidden');
      await activate();
    }
  }catch(e){ stateLine.textContent='QR hata: '+e; }
}
async function startQr(){
  btnQr.disabled=true;
  show('QR hazırlanıyor…');
  const r=await fetch('/api/prepare',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({BOT_ADMINS:admin.value.trim()})});
  const j=await r.json();
  if(!j.ok){ show(j.error||'Hazırlık başarısız', false); btnQr.disabled=false; return; }
  show('QR’ı WhatsApp ile okut…', true);
  qrWrap.classList.remove('hidden');
  if(timer) clearInterval(timer);
  await poll();
  timer=setInterval(poll, 2000);
  btnQr.disabled=false;
}
async function activate(){
  if(activating) return; activating=true;
  btnActivate.disabled=true; btnQr.disabled=true;
  show('Bot kuruluyor (tunnel + webhook)… bu 1-2 dk sürebilir');
  try{
    const r=await fetch('/api/activate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({BOT_ADMINS:admin.value.trim(), BOT_PREFIX:'!'})});
    const j=await r.json();
    show((j.ok?'OK\\n':'HATA\\n')+(j.log||j.error||JSON.stringify(j,null,2)), !!j.ok);
    if(j.ok) document.getElementById('stepLabel').textContent='Hazır — WhatsApp’tan !yardim yaz';
  }catch(e){ show(String(e), false); }
  finally{ activating=false; btnActivate.disabled=false; btnQr.disabled=false; }
}
btnQr.onclick=startQr;
btnActivate.onclick=activate;
btnSaveCreds.onclick=saveCreds;
boot();
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
    keys = [
        "ID_INSTANCE",
        "API_TOKEN",
        "SOURCE_GROUP_ID",
        "TARGET_GROUP_ID",
        "BROADCAST_MESSAGE",
        "BROADCAST_GROUPS",
        "BOT_PREFIX",
        "BOT_ADMINS",
        "WEBHOOK_PUBLIC_URL",
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
        "LICENSE_KEY",
        "OTOTEXT_LICENSE_SECRET",
        "LICENSE_SKIP",
        "NODE_FUNCTION_ALLOW_BUILTIN",
        "GREEN_API_PARTNER_TOKEN",
    ]
    lines, seen = [], set()
    for k in keys:
        if k in data:
            lines.append(f"{k}={data[k]}")
            seen.add(k)
    for k, v in data.items():
        if k not in seen:
            lines.append(f"{k}={v}")
    ENV_PATH.write_text("\n".join(lines) + "\n")


def normalize_admin(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return ""
    parts = []
    for piece in re.split(r"[,;\s]+", raw):
        piece = piece.strip()
        if not piece:
            continue
        if "@" not in piece:
            digits = re.sub(r"\D", "", piece)
            if digits.startswith("0") and len(digits) == 11:
                digits = "90" + digits[1:]
            piece = f"{digits}@c.us"
        parts.append(piece)
    return ",".join(parts)


def http_json(method: str, url: str, body: dict | None = None, cookies: str | None = None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if cookies:
        req.add_header("Cookie", cookies)
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
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


def creds() -> tuple[str, str]:
    env = read_env()
    return (env.get("ID_INSTANCE") or "").strip(), (env.get("API_TOKEN") or "").strip()


def placeholder(v: str) -> bool:
    return (not v) or v in ("YOUR_INSTANCE_ID", "YOUR_API_TOKEN_INSTANCE")


def has_creds() -> bool:
    i, t = creds()
    return not placeholder(i) and not placeholder(t)


def partner_token() -> str:
    env = read_env()
    return (os.environ.get("GREEN_API_PARTNER_TOKEN") or env.get("GREEN_API_PARTNER_TOKEN") or "").strip()


def green_api_state(instance: str, token: str) -> tuple[str, dict]:
    url = f"https://api.green-api.com/waInstance{instance}/getStateInstance/{token}"
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            payload = json.loads(resp.read().decode())
            return str(payload.get("stateInstance") or ""), payload
    except Exception as e:
        return "", {"error": str(e)}


def green_api_qr(instance: str, token: str) -> dict:
    url = f"https://api.green-api.com/waInstance{instance}/qr/{token}"
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return json.loads(raw)
        except Exception:
            return {"type": "error", "message": raw or str(e)}
    except Exception as e:
        return {"type": "error", "message": str(e)}


def green_api_settings(instance: str, token: str) -> dict:
    url = f"https://api.green-api.com/waInstance{instance}/getSettings/{token}"
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}


def green_api_set_webhook(instance: str, token: str, webhook_url: str) -> str:
    url = f"https://api.green-api.com/waInstance{instance}/setSettings/{token}"
    body = {
        "webhookUrl": webhook_url,
        "incomingWebhook": "yes",
        "incomingCallWebhook": "yes",
        "outgoingWebhook": "no",
        "outgoingAPIMessageWebhook": "no",
        "outgoingMessageWebhook": "no",
        "stateWebhook": "yes",
        "deviceWebhook": "no",
    }
    code, payload, _ = http_json("POST", url, body)
    return f"setSettings HTTP {code} {json.dumps(payload)[:300]}"


def green_api_create_instance(name: str) -> dict:
    tok = partner_token()
    if not tok:
        raise RuntimeError("GREEN_API_PARTNER_TOKEN yok — satıcı instance oluşturmalı")
    url = f"https://api.green-api.com/partner/createInstance/{tok}"
    code, payload, _ = http_json("POST", url, {"name": name or "Ototext", "delaySendMessagesMilliseconds": 3000})
    if code >= 400:
        raise RuntimeError(f"createInstance HTTP {code}: {payload}")
    iid = str(payload.get("idInstance") or "")
    at = str(payload.get("apiTokenInstance") or "")
    if not iid or not at:
        raise RuntimeError(f"createInstance eksik cevap: {payload}")
    write_env({"ID_INSTANCE": iid, "API_TOKEN": at})
    return {"idInstance": iid, "apiTokenInstance": at}


def check_license() -> tuple[bool, str]:
    try:
        r = subprocess.run(
            ["python3", str(ROOT / "scripts" / "check-license.py")],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            env=os.environ.copy(),
        )
        out = ((r.stdout or "") + (r.stderr or "")).strip()
        return r.returncode == 0, out or ("ok" if r.returncode == 0 else "lisans hatası")
    except Exception as e:
        return False, str(e)


def ensure_n8n_tunnel() -> str:
    script = ROOT / "scripts" / "ensure-n8n-tunnel.sh"
    r = subprocess.run(["bash", str(script)], cwd=str(ROOT), capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"tunnel failed: {r.stdout}\n{r.stderr}")
    url_file = LOGS / "n8n-public-url.txt"
    if not url_file.exists():
        raise RuntimeError("n8n public url missing")
    return url_file.read_text().strip()


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

    n8n_bin = ROOT / "node_modules" / ".bin" / "n8n"
    if not n8n_bin.exists():
        log.append("npm install n8n...")
        subprocess.run(["npm", "install", "n8n", "--save"], cwd=str(ROOT), check=False)

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
            "NODE_FUNCTION_ALLOW_BUILTIN": "fs,path",
            "ID_INSTANCE": env.get("ID_INSTANCE", ""),
            "API_TOKEN": env.get("API_TOKEN", ""),
            "SOURCE_GROUP_ID": env.get("SOURCE_GROUP_ID", ""),
            "TARGET_GROUP_ID": env.get("TARGET_GROUP_ID", ""),
            "BROADCAST_MESSAGE": env.get("BROADCAST_MESSAGE", ""),
            "BROADCAST_GROUPS": env.get("BROADCAST_GROUPS", ""),
            "BOT_PREFIX": env.get("BOT_PREFIX", "!"),
            "BOT_ADMINS": env.get("BOT_ADMINS", ""),
            "WEBHOOK_PUBLIC_URL": env.get("WEBHOOK_PUBLIC_URL", ""),
            "LICENSE_KEY": env.get("LICENSE_KEY", ""),
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
    for i in range(90):
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
        # owner maybe not set up yet
        setup_code, setup_payload, _ = http_json(
            "POST",
            f"http://127.0.0.1:{N8N_PORT}/rest/owner/setup",
            {
                "email": env.get("N8N_OWNER_EMAIL", "admin@localhost.local"),
                "password": env.get("N8N_OWNER_PASSWORD", "ChangeMe_Admin_123!"),
                "firstName": env.get("N8N_OWNER_FIRST_NAME", "Admin"),
                "lastName": env.get("N8N_OWNER_LAST_NAME", "Ototext"),
            },
        )
        if setup_code < 400 or "already" in json.dumps(setup_payload).lower():
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
    return "; ".join(c.split(";", 1)[0] for c in cookies)


def workflow_files() -> list[Path]:
    return [
        ROOT / "n8n-workflows/ototext-bot-commands.json",
        ROOT / "n8n-workflows/ototext-bot-worker.json",
        ROOT / "n8n-workflows/scenario-1-scheduled-group-broadcast.json",
        ROOT / "n8n-workflows/scenario-2-sync-group-participants.json",
    ]


def import_and_activate(cookie: str, activate_names: set[str] | None = None) -> str:
    lines = []
    env = read_env()
    child_env = os.environ.copy()
    child_env["N8N_USER_FOLDER"] = str(ROOT / ".n8n-data")
    child_env["N8N_ENCRYPTION_KEY"] = env.get("N8N_ENCRYPTION_KEY", "")
    child_env["N8N_BLOCK_ENV_ACCESS_IN_NODE"] = "false"

    for wf in workflow_files():
        if not wf.exists():
            lines.append(f"missing {wf.name}")
            continue
        data = json.loads(wf.read_text())
        if not data.get("id"):
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
        lines.append(f"import {wf.name}: rc={r.returncode} {(r.stdout or r.stderr).strip()}")

    code, payload, _ = http_json("GET", f"http://127.0.0.1:{N8N_PORT}/rest/workflows", cookies=cookie)
    workflows = payload.get("data") if isinstance(payload, dict) else payload
    if isinstance(workflows, dict):
        workflows = workflows.get("data") or workflows.get("workflows") or []

    activate_names = activate_names or {"Ototext Bot — Prefix Komutlar", "Ototext Bot — Worker"}
    for wf in workflows or []:
        wid = wf.get("id")
        name = wf.get("name") or ""
        if name not in activate_names:
            continue
        c2, full, _ = http_json("GET", f"http://127.0.0.1:{N8N_PORT}/rest/workflows/{wid}", cookies=cookie)
        body = full.get("data", full)
        version_id = body.get("versionId")
        c3, res, _ = http_json(
            "POST",
            f"http://127.0.0.1:{N8N_PORT}/rest/workflows/{wid}/activate",
            {"versionId": version_id},
            cookies=cookie,
        )
        if c3 >= 400:
            c3, res, _ = http_json(
                "PATCH",
                f"http://127.0.0.1:{N8N_PORT}/rest/workflows/{wid}",
                {"active": True, "versionId": version_id},
                cookies=cookie,
            )
        lines.append(
            f"activate {name} ({wid}): HTTP {c3} active={res.get('data', res).get('active') if isinstance(res, dict) else res}"
        )
    return "\n".join(lines)


def api_boot() -> dict:
    ok_lic, lic_msg = check_license()
    if not ok_lic:
        return {"ok": False, "hasCreds": False, "canProvision": False, "message": "Lisans: " + lic_msg}
    iid, _ = creds()
    state = ""
    authorized = False
    if has_creds():
        state, _ = green_api_state(*creds())
        authorized = state == "authorized"
    env = read_env()
    admin = env.get("BOT_ADMINS", "")
    if admin and "@" in admin:
        admin = admin.split("@", 1)[0]
    return {
        "ok": True,
        "hasCreds": has_creds(),
        "canProvision": bool(partner_token()),
        "authorized": authorized,
        "state": state,
        "idInstance": "" if placeholder(iid) else iid,
        "admin": admin,
        "message": (
            "QR’ı okut, gerisini Ototext yapsın."
            if has_creds() or partner_token()
            else "Instance yok — satıcı eklemeli veya gelişmiş alana girmeli."
        ),
    }


def api_prepare(payload: dict) -> dict:
    ok_lic, lic_msg = check_license()
    if not ok_lic:
        return {"ok": False, "error": lic_msg}
    if not ENV_PATH.exists():
        if (ROOT / ".env.example").exists():
            ENV_PATH.write_text((ROOT / ".env.example").read_text())
    if payload.get("BOT_ADMINS"):
        write_env({"BOT_ADMINS": normalize_admin(payload.get("BOT_ADMINS") or "")})
    if not has_creds():
        if partner_token():
            try:
                created = green_api_create_instance("Ototext-" + (payload.get("BOT_ADMINS") or "bot")[:20])
                return {"ok": True, "provisioned": True, **created}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "Green API instance yok. Satıcı pakete ID_INSTANCE/API_TOKEN eklemeli."}
    # already authorized? still ok
    return {"ok": True, "provisioned": False}


def api_qr() -> dict:
    if not has_creds():
        return {"ok": False, "type": "error", "message": "credentials yok", "authorized": False}
    instance, token = creds()
    state, _ = green_api_state(instance, token)
    if state == "authorized":
        return {
            "ok": True,
            "authorized": True,
            "state": state,
            "type": "alreadyLogged",
            "message": "authorized",
            "qrPage": f"https://qr.green-api.com/waInstance{instance}/{token}",
        }
    qr = green_api_qr(instance, token)
    out = {
        "ok": True,
        "authorized": False,
        "state": state or "notAuthorized",
        "type": qr.get("type"),
        "message": qr.get("message") if qr.get("type") != "qrCode" else "",
        "qrPage": f"https://qr.green-api.com/waInstance{instance}/{token}",
    }
    if qr.get("type") == "qrCode" and qr.get("message"):
        out["qrDataUrl"] = "data:image/png;base64," + str(qr["message"]).strip()
    elif qr.get("type") == "alreadyLogged":
        out["authorized"] = True
    return out


def api_activate(payload: dict) -> dict:
    logs: list[str] = []
    ok_lic, lic_msg = check_license()
    logs.append("0) License: " + lic_msg)
    if not ok_lic:
        return {"ok": False, "error": "Geçerli lisans yok", "log": "\n".join(logs)}
    if not has_creds():
        return {"ok": False, "error": "Instance yok", "log": "\n".join(logs)}

    instance, token = creds()
    state, detail = green_api_state(instance, token)
    logs.append(f"1) stateInstance={state} {detail}")
    if state != "authorized":
        return {"ok": False, "error": "Önce WhatsApp QR okut (authorized değil)", "log": "\n".join(logs)}

    prefix = (payload.get("BOT_PREFIX") or read_env().get("BOT_PREFIX") or "!").strip() or "!"
    admins = normalize_admin(payload.get("BOT_ADMINS") or read_env().get("BOT_ADMINS") or "")
    settings = green_api_settings(instance, token)
    wid = normalize_admin(str(settings.get("wid") or ""))
    if wid and wid not in (admins or "").split(","):
        admins = ",".join(x for x in [admins, wid] if x)
    write_env(
        {
            "BOT_PREFIX": prefix,
            "BOT_ADMINS": admins,
            "NODE_FUNCTION_ALLOW_BUILTIN": "fs,path",
        }
    )
    logs.append(f"2) admins={admins} wid={wid}")

    logs.append("3) Public n8n tunnel")
    try:
        public = ensure_n8n_tunnel()
    except Exception as e:
        return {"ok": False, "error": f"tunnel: {e}", "log": "\n".join(logs)}
    bot_webhook = f"{public}/webhook/ototext-bot"
    write_env({"WEBHOOK_PUBLIC_URL": public, "WEBHOOK_URL": public + "/"})
    logs.append(f"public={public}")

    logs.append("4) Restart n8n")
    try:
        logs.append(restart_n8n())
    except Exception as e:
        return {"ok": False, "error": str(e), "log": "\n".join(logs)}

    logs.append("5) Import + activate")
    try:
        cookie = n8n_login_cookie()
        logs.append(import_and_activate(cookie))
    except Exception as e:
        return {"ok": False, "error": str(e), "log": "\n".join(logs)}

    logs.append("6) Webhook")
    logs.append(green_api_set_webhook(instance, token, bot_webhook))
    logs.append("DONE — WhatsApp’tan yaz: " + prefix + "yardim")
    return {"ok": True, "log": "\n".join(logs), "bot_webhook": bot_webhook, "prefix": prefix}


# legacy name used by older clients
def run_setup(payload: dict) -> dict:
    if payload.get("ID_INSTANCE") and payload.get("API_TOKEN"):
        write_env(
            {
                "ID_INSTANCE": str(payload["ID_INSTANCE"]).strip(),
                "API_TOKEN": str(payload["API_TOKEN"]).strip(),
            }
        )
    prep = api_prepare(payload)
    if not prep.get("ok"):
        return prep
    # if not authorized, tell client to use QR UI
    instance, token = creds()
    state, _ = green_api_state(instance, token)
    if state != "authorized":
        return {
            "ok": False,
            "error": "WhatsApp bağlı değil. Sayfadaki QR’ı okut, sonra otomatik kurulum başlar.",
            "needQr": True,
            "log": f"stateInstance={state}",
        }
    return api_activate(payload)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print("[setup]", fmt % args)

    def _send(self, code: int, body: bytes, content_type: str):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, obj: dict):
        self._send(code, json.dumps(obj, ensure_ascii=False).encode(), "application/json")

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            self._send(200, HTML.encode(), "text/html; charset=utf-8")
            return
        if path == "/health":
            return self._json(200, {"ok": True})
        if path == "/api/boot":
            return self._json(200, api_boot())
        if path == "/api/qr":
            return self._json(200, api_qr())
        self._send(404, b"not found", "text/plain")

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode()
        ctype = self.headers.get("Content-Type", "")
        if "application/json" in ctype:
            payload = json.loads(raw or "{}")
        else:
            payload = {k: v[0] for k, v in parse_qs(raw).items()}
        try:
            if path == "/api/creds":
                iid = (payload.get("ID_INSTANCE") or "").strip()
                tok = (payload.get("API_TOKEN") or "").strip()
                if placeholder(iid) or placeholder(tok):
                    return self._json(400, {"ok": False, "error": "ID_INSTANCE / API_TOKEN gerekli"})
                write_env({"ID_INSTANCE": iid, "API_TOKEN": tok})
                return self._json(200, {"ok": True})
            if path == "/api/prepare":
                result = api_prepare(payload)
                return self._json(200 if result.get("ok") else 400, result)
            if path == "/api/activate":
                result = api_activate(payload)
                return self._json(200 if result.get("ok") else 400, result)
            if path == "/api/setup":
                result = run_setup(payload)
                return self._json(200 if result.get("ok") else 400, result)
            self._send(404, b"not found", "text/plain")
        except Exception as e:
            self._json(500, {"ok": False, "error": str(e)})


def main():
    if not ENV_PATH.exists() and (ROOT / ".env.example").exists():
        ENV_PATH.write_text((ROOT / ".env.example").read_text())
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Ototext QR kurulum → http://0.0.0.0:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
