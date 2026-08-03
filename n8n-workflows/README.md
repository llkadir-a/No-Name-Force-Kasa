# n8n Workflow JSON'ları

Import-ready Green API workflows.

## Dosyalar
- `scenario-1-scheduled-group-broadcast.json`
- `scenario-2-sync-group-participants.json`

## Import
```bash
# Native
bash scripts/import-workflows-native.sh

# Docker
bash scripts/import-workflows.sh

# veya UI: Workflows → Import from File
```

Credential'lar `.env` üzerinden `$env.ID_INSTANCE` / `$env.API_TOKEN` olarak okunur.
Ana kurulum için üst dizindeki `README.md` dosyasına bakın.
