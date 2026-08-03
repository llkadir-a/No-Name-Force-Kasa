# Ototext — n8n Workflow JSON'ları

## Bot
- `ototext-bot-commands.json` → **Ototext Bot — Prefix Komutlar**
  - Webhook path: `ototext-bot`
  - Prefix komutlar: help, ping, status, id, groups, broadcast, sync

## Yardımcı senaryolar
- `scenario-1-scheduled-group-broadcast.json`
- `scenario-2-sync-group-participants.json`

Credential’lar `.env` → `$env.ID_INSTANCE`, `$env.API_TOKEN`, `$env.BOT_PREFIX`, `$env.BOT_ADMINS`, `$env.BROADCAST_GROUPS`
