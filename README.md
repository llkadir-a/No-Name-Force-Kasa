# Ototext

WhatsApp bot — `!` prefix komutlarla yönetilir. Bot numarası otomatik admindir.

## Komutlar

| Komut | Açıklama |
|-------|----------|
| `!yardim` | Ana menü |
| `!otox (metin)` | Yayın başlat (onay ister) |
| `!onay` / `!iptal` | Onay sistemi |
| `!panic` | Her şeyi anında durdur |
| `!zaman-otox 22:00-01:00` | Zamanlı yayın penceresi |
| `!zaman-dm 22:00-01:00` | Zamanlı DM penceresi |
| `!metin (yazı)` | Zamanlı akışta metin gir |
| `!log-grup (id)` | Log grubu ayarla |
| `!rapor` | Günlük rapor |
| `!durdur` | Yayını durdur |
| `!durum` | Yayın statusu |
| `!sure 3` | Yayın aralığı (dakika) |
| `!dm (metin). (grupId)` | Gruptakilere DM |
| `!dm-durdur` / `!dm-sure` / `!dm-durum` | DM kontrol |
| `!gruplar 1` | Gruplar (10/sayfa: no, isim, üye, id) |
| `!davetler` | DM’den gelen davet linkleri |
| `!filtre` / `!min-uye N` / `!temizlik` | Filtreler |
| `!black` / `!black-ekle` / `!black-cikar` / `!black-liste` | Kara liste |
| `!mining` / `!mining-baslat` / `!mining-durdur` / `!mining-durum` | Üye ekleme |
| `!katil (link)` / `!tumkatil (link...)` | Gruba katıl |
| `!karakter ayarla (isim)` | WhatsApp ismi |
| `!admin` / `!admin-ekle` / `!admin-cikar` / `!admin-list` | Adminler |
| `!prefix` | Prefix menüsü |
| `!prefix-main (p)` | Ana prefix |
| `!prefix-ekle (p)` | Ek prefix |
| `!prefix-cikar (p)` / `!prefix cikar (p)` | Prefix çıkar |
| `!istatistik` | Genel istatistik |
| `!lisans` | Lisans durumu |

Sadece adminler kullanabilir. Bot’un kendi numarası otomatik admin.

## Satış (müşteri kopyası)

Aynı sistemi satmak için: `bash scripts/start-seller-panel.sh` → lisans üret → ZIP kit indir.  
Detay: [`SATIS.md`](SATIS.md)

## Telefonla kurulum

```bash
bash scripts/start-mobile-setup.sh
```

Forma Green API `ID_INSTANCE` + `API_TOKEN` + admin numaranı yaz.

## Mimari

- `Ototext Bot — Prefix Komutlar` — webhook komut motoru
- `Ototext Bot — Worker` — her 1 dk yayın/DM/mining kuyruğu
- State: `data/ototext-state.json`

## Ortam

```env
ID_INSTANCE=...
API_TOKEN=...
BOT_PREFIX=!
BOT_ADMINS=905xxxxxxxxx@c.us
NODE_FUNCTION_ALLOW_BUILTIN=fs,path
```
