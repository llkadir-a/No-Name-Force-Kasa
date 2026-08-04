# Ototext

WhatsApp bot — `!` prefix komutlarla yönetilir. Bot numarası otomatik admindir.

## Komutlar

| Komut | Açıklama |
|-------|----------|
| `!yardim` | Ana menü |
| `!otox` | Yayın: rotasyon sorulur → adet/metin → onay |
| `!adet N` | Rotasyonda kaç metin (2-10) |
| `!metin ...` | Otox/DM metin adımları |
| `!onay` / `!evet` / `!hayir` / `!iptal` | Onay / rotasyon cevabı |
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
| `!numara` | Çoklu WhatsApp numarası menüsü |
| `!numara-ekle (isim) (id) (token)` | Yeni bot numarası ekle |
| `!numara-liste` / `!numara-aktif N` / `!numara-sil N` | Listele / aktif yap / sil |
| `!guard ac` / `!guard kapat` | Grup koruma (sticker spam + arama → kick) |
| `!guard grup ac` | Sadece bu grupta guard |
| `!guard sticker 4` | Sticker spam limiti (15 sn içinde) |
| `!guard yaz` / `!guard kilit` | Sohbeti aç / sadece admin yazabilir |
| `!sil N` | Grupta diğer üyelerin son N mesajını sil (grup admin + bot admin) |

Ban/kısıtlama erken uyarı: `blocked` / `suspended` / `yellowCard` / `notAuthorized` / `sleepMode` algılanınca bot **durmaz**; `!log-grup` kanalına kırmızı ❗ uyarısı düşer (aynı uyarı 30 dk’da bir kez).

Sadece adminler kullanabilir. Bot’un kendi numarası otomatik admin.

## Admin Control Center

```bash
bash scripts/start-seller-panel.sh
```

Tarayıcı: `http://127.0.0.1:8790` (veya `/admin`)

Panelden ayarlanır: log kanalı, prefix, otox/DM, guard, numaralar, admin/blacklist, panic, lisanslar, ham JSON.  
API: `GET/POST /api/bot/state` · `POST /api/bot/patch` · `POST /api/bot/action`  
Taşınabilir dosya: `ototext-admin-panel.html`

## Satış (müşteri kopyası)

Aynı panilden lisans üret → ZIP kit indir. Detay: [`SATIS.md`](SATIS.md)

## Telefonla kurulum

```bash
bash scripts/start-mobile-setup.sh
```

Telefondaki linki aç → **QR Kodunu Göster** → WhatsApp’tan okut. API/token girmen gerekmez (satıcı pakete gömer).

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
