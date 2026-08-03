# n8n + Green API WhatsApp Workflows

Doğrudan n8n arayüzüne **Import** edilebilecek iki workflow.

## İçe aktarma

1. n8n → **Workflows** → **Import from File**
2. İlgili JSON dosyasını seçin:
   - `scenario-1-scheduled-group-broadcast.json`
   - `scenario-2-sync-group-participants.json`

Alternatif: JSON içeriğini kopyalayıp n8n canvas üzerinde `Ctrl+V` / `Cmd+V` ile yapıştırın.

## Ortak kurulum

n8n **Settings → Variables** altında tanımlayın:

| Variable       | Açıklama                          |
|----------------|-----------------------------------|
| `ID_INSTANCE`  | Green API instance ID             |
| `API_TOKEN`    | Green API `apiTokenInstance`      |

URL formatı:

```text
https://api.green-api.com/waInstance{{$vars.ID_INSTANCE}}/{{METHOD}}/{{$vars.API_TOKEN}}
```

## Senaryo 1 — Zamanlanmış Grup Broadcast

Akış: `Schedule Trigger` → `Code (20 grup)` → `Loop Over Items` → `Wait 3 dk` → `POST /sendMessage` → döngü

- Code düğümündeki `120363...@g.us` placeholder chatId'leri gerçek grup ID'leriyle değiştirin.
- `message` metnini güncelleyin.
- Schedule periyodu varsayılan: her 24 saat.

## Senaryo 2 — Katılımcı Senkronizasyonu

Akış: `Manual` / `Schedule` → `POST /getGroupData` → `Code (participants → items)` → `Loop Over Items` → `Wait 15 dk` → `POST /addGroupParticipant` → döngü

- `KAYNAK_GRUP_ID@g.us` → kaynak grup
- `HEDEF_GRUP_ID@g.us` → hedef grup

### Green API uyumluluk notu

İstekte geçen `addGroupParticipants` / `participantPhone` alanları Green API dokümantasyonundaki gerçek isimlerle eşleştirildi:

| İstekte geçen              | Green API (çalışan)     |
|----------------------------|-------------------------|
| `/addGroupParticipants`    | `/addGroupParticipant`  |
| `participantPhone`         | `participantChatId`     |

`userChatId` Code çıktısından `participantChatId` body alanına map edilir.

## Wait düğümü notu

Uzun süreli `Wait` düğümlerinin resume edebilmesi için workflow'un **Active** olması gerekir.
