# Green API + n8n WhatsApp Otomasyon Sistemi

Hazır n8n stack + 2 Green API workflow. Bu ortamda **native** olarak çalışır; sunucunuzda Docker ile de ayağa kalkar.

## Durum (bu ortam)

- n8n: `http://localhost:5678` (çalışıyor)
- Owner: `admin@localhost.local` / `.env` içindeki `N8N_OWNER_PASSWORD`
- Import edilen workflow'lar:
  - Senaryo 1 — Zamanlanmış Grup Broadcast
  - Senaryo 2 — Grup Katılımcı Senkronizasyonu

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

Senaryo 1 Code node içinde 20 adet `chatId` placeholder'ını gerçek grup ID'leriyle değiştirin (UI veya JSON).

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
3. Her iki workflow'u aç → **Active**

> Uzun `Wait` düğümleri için workflow Active olmalıdır.

## Workflow özeti

| Senaryo | Akış | Rate limit |
|---------|------|------------|
| 1 Broadcast | Schedule → Code(20 grup) → Loop → Wait → `POST /sendMessage` | 3 dk |
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
