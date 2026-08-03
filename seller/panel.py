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
)

SELLER_DIR = Path(__file__).resolve().parent
ROOT = SELLER_DIR.parent
PORT = int(os.environ.get("SELLER_PORT", "8790"))

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
        <button type="submit">Lisans Üret</button>
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
    await downloadKit(j.customer.jti);
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


def build_customer_kit(jti: str) -> Path:
    data = load_customers()
    row = next((c for c in data.get("customers", []) if c.get("jti") == jti), None)
    if not row:
        raise ValueError("JTI bulunamadı")
    if row.get("revoked"):
        raise ValueError("Lisans iptal edilmiş")

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
        for key, val in (
            ("LICENSE_KEY=", f"LICENSE_KEY={row['licenseKey']}"),
            ("OTOTEXT_LICENSE_SECRET=", f"OTOTEXT_LICENSE_SECRET={secret}"),
            ("LICENSE_SKIP=", "LICENSE_SKIP="),
        ):
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
        (root / "MUSTERI.md").write_text(
            f"""# Ototext Müşteri Kurulum

Merhaba {row.get('name') or ''},

Bu paket senin Ototext kopyan (satıcının sistemiyle aynı).

## 1) Hazırlık
```bash
cp .env.example .env
```

`.env` içinde `LICENSE_KEY` zaten dolu. Sen sadece Green API doldur:

```env
ID_INSTANCE=...
API_TOKEN=...
BOT_ADMINS=905xxxxxxxxx@c.us
BOT_PREFIX=!
```

## 2) Kur
```bash
npm install
bash scripts/setup-native.sh
# veya mobil kurulum:
bash scripts/start-mobile-setup.sh
```

## 3) WhatsApp
Bot numarandan yaz: `!yardim`  
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


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print("[seller]", fmt % args)

    def _json(self, code: int, obj):
        raw = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
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

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            return self._html(HTML)
        if path == "/api/customers":
            return self._json(200, load_customers())
        if path == "/health":
            return self._json(200, {"ok": True})
        self._json(404, {"error": "not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode()
        try:
            body = json.loads(raw or "{}")
        except Exception:
            body = {k: v[0] for k, v in parse_qs(raw).items()}

        try:
            if path == "/api/create":
                row = create_license(
                    name=body.get("name") or "Musteri",
                    email=body.get("email") or "",
                    days=int(body.get("days") or 365),
                    plan=body.get("plan") or "standard",
                    note=body.get("note") or "",
                )
                return self._json(200, {"ok": True, "customer": row})
            if path == "/api/revoke":
                ok = revoke_license(body.get("jti") or "")
                return self._json(200 if ok else 404, {"ok": ok})
            if path == "/api/kit":
                zpath = build_customer_kit(body.get("jti") or "")
                data = zpath.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "application/zip")
                self.send_header("Content-Disposition", f'attachment; filename="{zpath.name}"')
                self.send_header("Content-Length", str(len(data)))
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
    print(f"Ototext Satış Paneli → http://127.0.0.1:{PORT}")
    print(f"Secret dosyası: {SECRET_PATH}")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
