# Ototext

WhatsApp grup otomasyonu — n8n + Green API altyapısı.

## Telefonla kurulum (tek form)

```bash
bash scripts/start-mobile-setup.sh
```

Çıkan `trycloudflare.com` linkini telefonda aç → `ID_INSTANCE` + `API_TOKEN` yapıştır → **Kur ve Aktif Et**.

Script Green API'yi doğrular, n8n'i yeniden başlatır, workflow'ları import/aktif eder.

## Durum (bu ortam)

- n8n: `http://localhost:5678` (çalışıyor)
- Owner: `admin@localhost.local` / `.env` içindeki `N8N_OWNER_PASSWORD`
- Import edilen workflow'lar:
  - Ototext — Zamanlanmış Grup Broadcast
  - Ototext — Grup Katılımcı Senkronizasyonu

## 1) Credential doldur

```bash
cp .env.example .env   # yoksa
```

`.env` zorunlu alanlar:

```env
ID_INSTANCE=1234567890
API_TOKEN=your_green_api_token
SOURCE_GROUP_ID=120363xxxx@g.us
TARGET_GROUP_ID=120363yyyy@g.us
```

Senaryo 1 Code node içinde chatId listesini gerçek grup ID'leriyle değiştirin (UI, mobil form veya JSON).

## 2) Başlat / durdur

```bash
# Native (önerilen — bu cloud ortamında çalışır)
npm install
npm run setup          # n8n start + workflow import + owner setup

# veya
bash scripts/setup-native.sh
bash scripts/stop-native.sh

# Docker (VPS / local makine)
bash scripts/setup.sh
bash scripts/stop.sh
```

## 3) UI'da Active et

1. http://localhost:5678
2. Login (`admin@localhost.local`)
3. Her iki Ototext workflow'unu aç → **Active**

> Uzun `Wait` düğümleri için workflow Active olmalıdır.

## Workflow özeti

| Senaryo | Akış | Rate limit |
|---------|------|------------|
| 1 Broadcast | Schedule → Code(gruplar) → Loop → Wait → `POST /sendMessage` | 3 dk |
| 2 Sync | Manual/Schedule → `getGroupData` → Code → Loop → Wait → `addGroupParticipant` | 15 dk |

API URL:

```text
https://api.green-api.com/waInstance{{$env.ID_INSTANCE}}/{{METHOD}}/{{$env.API_TOKEN}}
```

## Doğrulama

```bash
bash scripts/validate-green-api.sh
```

Instance bilgisini Green API `getStateInstance` ile kontrol eder (gerçek credential gerekir).

## Dosya yapısı

```text
docker-compose.yml
.env.example
package.json
scripts/
  setup-native.sh / stop-native.sh / import-workflows-native.sh
  setup.sh / start.sh / stop.sh / import-workflows.sh   # Docker
  start-mobile-setup.sh / mobile-setup-server.py
  validate-green-api.sh
n8n-workflows/
  scenario-1-scheduled-group-broadcast.json
  scenario-2-sync-group-participants.json
```

## Notlar

- `$env.*` erişimi için `N8N_BLOCK_ENV_ACCESS_IN_NODE=false`
- Green API gerçek alanlar: `addGroupParticipant` + `participantChatId`
- `.env`, `.n8n-data/`, `node_modules/`, `logs/` git'e girmez
- Credential değişince native'de process'i yeniden başlatın: `npm run setup`
