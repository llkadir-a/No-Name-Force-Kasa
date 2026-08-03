# Ototext

WhatsApp bot — Green API numarana bağlanır, prefix komutlarla yönetilir.

## Bot komutları (varsayılan prefix `/`)

| Komut | Açıklama |
|-------|----------|
| `/help` | Komut listesi |
| `/ping` | Bot ayakta mı |
| `/status` | Green API instance durumu |
| `/id` | chatId / sender bilgin |
| `/groups` | Kayıtlı broadcast grupları |
| `/broadcast <mesaj>` | Gruplara mesaj at |
| `/sync` | Kaynak→hedef sync bilgilendirmesi |

Sadece `BOT_ADMINS` numaraları komut çalıştırabilir.

## Telefonla kurulum

```bash
bash scripts/start-mobile-setup.sh
```

Formda:
1. Green API `ID_INSTANCE` + `API_TOKEN`
2. Admin telefon numaran
3. Grup chatId’leri (opsiyonel)

Ototext: n8n public tunnel açar → bot workflow’u aktif eder → Green API webhook kaydeder.

Sonra WhatsApp’tan bota `/help` yaz.

## Ortam değişkenleri

```env
ID_INSTANCE=...
API_TOKEN=...
BOT_PREFIX=/
BOT_ADMINS=905xxxxxxxxx@c.us
BROADCAST_GROUPS=120363aaa@g.us,120363bbb@g.us
SOURCE_GROUP_ID=...
TARGET_GROUP_ID=...
WEBHOOK_URL=https://....trycloudflare.com/
```

## Workflow’lar

- `Ototext Bot — Prefix Komutlar` (webhook `/webhook/ototext-bot`)
- `Ototext — Zamanlanmış Grup Broadcast`
- `Ototext — Grup Katılımcı Senkronizasyonu`

## Native / Docker

```bash
npm install && npm run setup
npm run mobile
# Docker: npm run setup:docker
```

## Notlar

- Webhook için public URL gerekir (`scripts/ensure-n8n-tunnel.sh`)
- Cloudflare quick tunnel URL’leri değişebilir; değişince formu tekrar çalıştır
- Wait düğümleri için workflow Active olmalı
