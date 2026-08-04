# Ototext — Ürün Tanıtımı

**Ototext**, WhatsApp üzerinden `!` komutlarıyla yönetilen bir otomasyon botudur.  
n8n + Green API üzerinde çalışır. Yayın (otox), toplu DM, grup koruma, çoklu numara, lisanslı satış kiti ve web admin paneli tek sistemde birleşir.

Bu doküman botun **ne olduğunu, ne yaptığını ve her özelliğini** anlatır.

---

## 1. Tek cümlede ne?

WhatsApp’tan yazdığın komutlarla (veya web admin panelinden) gruplara otomatik mesaj atan, üyelere DM gönderen, grupları koruyan, ban riskini izleyen ve aynı sistemi lisansla satmana izin veren otomasyon motoru.

---

## 2. Kimler için?

| Kullanıcı | Ne işe yarar? |
|-----------|----------------|
| Ajans / pazarlamacı | Çok grupta kontrollü duyuru yayını |
| Topluluk yöneticisi | Guard ile spam/arama koruması, mesaj silme |
| Yazılım satıcısı | Aynı botu lisans + QR kit ile çoğaltıp satma |
| Operatör | Panikten log kanalına kadar tek yerden kontrol |

---

## 3. Nasıl çalışır? (mimari)

```
WhatsApp telefon
    ↕ (QR / Green API instance)
Green API bulutu
    ↕ webhook
n8n: “Ototext Bot — Prefix Komutlar”   ← gelen mesaj / komut
n8n: “Ototext Bot — Worker”            ← her ~1 dk otox / DM / mining / sağlık kontrolü
    ↕
data/ototext-state.json                ← tüm ayar ve durum
    ↕
Seller Admin Panel (:8790)             ← web’den her şeyi değiştir
```

- **Komut motoru:** WhatsApp’tan `!komut` gelir → yetki kontrolü → state güncellenir → cevap döner.
- **Worker:** Zamanı gelince bir sonraki gruba / kişiye mesaj atar; instance sağlığını kontrol eder.
- **State dosyası:** Tek gerçek kaynak. Panel ve bot aynı dosyayı okur/yazar.
- **Admin panel:** Tarayıcıdan log kanalı, yayın, guard, numaralar, lisans… hepsi.

---

## 4. Kurulum yolları

### A) Sen (sahip / satıcı)
```bash
bash scripts/start-seller-panel.sh   # admin + lisans
# kendi botun için ayrıca n8n + Green API kurulu olmalı
```

### B) Müşteri (QR-first — API görmez)
```bash
bash scripts/start-mobile-setup.sh
```
1. Telefonda çıkan linki açar  
2. **QR Kodunu Göster**  
3. WhatsApp’tan okutur  
4. Tunnel + webhook + bot otomatik ayağa kalkar  
5. Bota `!yardim` yazar  

Satıcı, kite Green API instance bilgilerini gömer; müşteri token girmez.

### C) Lisans atlama (kendi kopyan)
```bash
export LICENSE_SKIP=1
bash scripts/setup-native.sh
```

---

## 5. Yetki modeli

- Sadece **admin** listesindeki numaralar komut kullanabilir.
- Bot’un kendi WhatsApp numarası **otomatik admin** yapılır.
- Ek admin: `!admin-ekle` veya panelden **Admin / Black**.
- Ortam değişkeni `BOT_ADMINS` ile de başlangıç admin eklenebilir.
- Prefix varsayılan `!` — değiştirilebilir (`!prefix-main`, panel).

---

## 6. Özellikler — detaylı katalog

### 6.1 Ana menü ve yardım
| Özellik | Açıklama |
|---------|----------|
| `!yardim` / `!help` | Tüm ana komutları listeler |
| `!istatistik` | Komut / yayın / DM / katılma / numara sayıları |
| `!rapor` | Günlük özet (log grubuna da gidebilir) |
| `!lisans` | Lisans durumu (aktif / süre / iptal) |

---

### 6.2 Yayın motoru (Otox)

Gruplara sırayla, ayarlı aralıkla mesaj gönderir.

| Komut / özellik | Ne yapar? |
|-----------------|-----------|
| `!otox` | Yayın sihirbazını başlatır |
| Rotasyon sorusu | `!evet` → birden fazla metin; `!hayir` → tek metin |
| `!adet N` | Rotasyonda 2–10 metin |
| `!metin ...` | Metin adımlarını doldurur |
| `!onay` | Yayını başlatır |
| `!iptal` | Bekleyen akışı iptal |
| `!durdur` | Yayını durdurur |
| `!durum` | Kaç gönderildi, index, pencere… |
| `!sure 3` | Aralık (dakika) |
| `!zaman-otox 22:00-01:00` | Sadece bu saat aralığında gönder (İstanbul saati) |
| Metin rotasyonu | Worker her gönderimde sıradaki metne geçer |
| Min üye filtresi | `!min-uye N` — küçük grupları atlar |
| Kara liste | Blacklisted gruplara basmaz |
| Admin panel | Otox start/stop, metinler, pencere, aralık |

**Akış örneği:**
```
!otox
→ Rotasyon ister misin?
!evet
!adet 3
!metin Merhaba A
!metin Merhaba B
!metin Merhaba C
!onay
→ Yayın başlar
```

---

### 6.3 DM motoru

Bir gruptaki üyelere sırayla özel mesaj.

| Komut | Ne yapar? |
|-------|-----------|
| `!dm (metin). (grupId)` | Kuyruk kurar, onay ister |
| `!onay` | DM’i başlatır |
| `!dm-durdur` | Durdurur |
| `!dm-sure` | Aralık |
| `!dm-durum` | İlerleme / hata |
| `!zaman-dm 22:00-01:00` | Zaman penceresi |
| Panel | Metin, kuyruk, start/stop |

---

### 6.4 Panic — acil durdurma

| Yol | Etki |
|-----|------|
| `!panic` | Otox + DM + mining + bekleyen onay **hemen** durur |
| Panel PANIC butonu | Aynı etki (`/api/panic`, `/api/bot/action`) |

Hesaba girmez; sadece bot state’ini keser.

---

### 6.5 Guard — grup koruma

Bot **admin olduğu** gruplarda çalışır.

| Özellik | Detay |
|---------|--------|
| `!guard ac` / `kapat` | Global aç/kapa |
| `!guard grup ac` / `kapat` | Sadece o grup |
| `!guard liste` | Korunan gruplar |
| Sticker spam | 15 sn içinde N sticker → kick (varsayılan 4) |
| `!guard sticker N` | Limit ayarı |
| Grup araması | Arama teklifi → kick |
| Otomatik kilit | Olay sonrası sohbet **sadece admin yazar** |
| `!guard yaz` | Sohbeti tekrar herkese aç |
| `!guard kilit` | Elle kilitle |
| Admin koruması | Diğer adminleri kicklemez |
| Panel | Tüm guard bayrakları + özel grup listesi |

**Not:** WhatsApp grup aramasını “kapatmak” (VoIP’i bitirmek) Green API ile mümkün değil; bot kendi bacağını bırakır / kişiyi gruptan atar + sohbeti kilitler.

---

### 6.6 Mesaj silme

| Komut | Kural |
|-------|--------|
| `!sil N` | Son N **diğer üye** mesajını sil (1–50) |

Koşullar:
- Sadece grupta
- Komutu yazan **grup admini** olmalı
- Bot da **grup admini** olmalı
- Botun / senin mesajların değil; `incoming` mesajlar
- WhatsApp ~60 saat “herkesten sil” sınırı geçerli

---

### 6.7 Ban / kısıtlama erken uyarı

Worker + webhook (`stateInstanceChanged`) instance durumunu izler.

| Durum | Anlam |
|-------|--------|
| `blocked` | Hesap / cihaz ban |
| `suspended` / `yellowCard` | Geçici spam kısıtı |
| `notAuthorized` | QR oturumu düşmüş |
| `sleepMode` | Telefon kapalı / uyku |

**Davranış (önemli):**
- Bot **otomatik durmaz**
- `!log-grup` kanalına büyük kırmızı ❗❗❗ uyarısı + açıklama gider
- Aynı uyarı ~30 dakikada bir kez tekrarlanır
- Yayın/DM çalışmaya devam eder; sen istersen `!panic` dersin

---

### 6.8 Çoklu WhatsApp numarası

Birden fazla Green API instance yönetilir; aktif numaradan gönderim yapılır.

| Komut | Ne yapar? |
|-------|-----------|
| `!numara` | Menü |
| `!numara-ekle (isim) (id) (token)` | Yeni numara |
| `!numara-liste` | Liste |
| `!numara-aktif N` | Aktif yap |
| `!numara-sil N` | Sil |
| `!numara-yenile` | State / wid yenile |
| Panel | Numaralar JSON + aktif id |

Webhook hangi instance’tan gelirse o oturumun credentials’ı kullanılır.

---

### 6.9 Gruplar, filtre, kara liste, davetler

| Komut | Ne yapar? |
|-------|-----------|
| `!gruplar [sayfa]` | Grup listesi (isim, üye, id) — 10/sayfa |
| `!filtre` | Filtre menüsü |
| `!min-uye N` | Yayında minimum üye |
| `!temizlik` | Filtre temizliği / bakım |
| `!black` | Kara liste menüsü |
| `!black-ekle` / `!black-cikar` / `!black-liste` | Yönetim |
| `!davetler` | Gelen `chat.whatsapp.com` davet linkleri kaydı |
| `!katil (link)` | Tek gruba katıl |
| `!tumkatil (link...)` | Toplu katıl |

---

### 6.10 Mining (üye ekleme)

Diğer gruplardan aday alıp hedef gruba eklemeye çalışır (Green API limitlerine tabi).

| Komut | Ne yapar? |
|-------|-----------|
| `!mining` | Menü / durum |
| `!mining-baslat` | Başlat |
| `!mining-durdur` | Durdur |
| `!mining-durum` | İlerleme |
| Panel | Hedef grup, total, start/stop |

---

### 6.11 Profil / karakter

| Komut | Ne yapar? |
|-------|-----------|
| `!karakter ayarla (isim)` | WhatsApp görünen adı ayarlar |

---

### 6.12 Admin ve prefix yönetimi

| Komut | Ne yapar? |
|-------|-----------|
| `!admin` / `!admin-list` | Liste |
| `!admin-ekle` / `!admin-cikar` | Yönet |
| `!prefix` | Prefix menüsü |
| `!prefix-main (p)` | Ana prefix |
| `!prefix-ekle (p)` | Ek prefix (ör. `/`) |
| `!prefix-cikar (p)` | Çıkar |

Birden fazla prefix aynı anda dinlenebilir.

---

### 6.13 Log kanalı

| Yol | Ne yapar? |
|-----|-----------|
| `!log-grup (id)` | Log grubunu ayarla |
| Panel → Genel / Log | Aynı ayar |
| Worker logları | Yayın / DM / start / stop / hata |
| Ban uyarısı | Kırmızı ❗ mesajlar buraya |

---

### 6.14 Lisans ve satış sistemi

| Parça | Açıklama |
|-------|----------|
| Seller panel | Lisans üret, listele, iptal, ZIP kit |
| HMAC lisans | İmza + süre + plan (standard / pro / lifetime) |
| `!lisans` | Bot içinde durum |
| `/api/verify` | Dış doğrulama |
| Müşteri kiti | Lisans + bot + QR kurulum; müşteri API görmez |
| `seller/customers.json` | Müşteri kayıtları |
| İptal | Panelden revoke → yeni kit / verify iptali görür |

**Paket önerisi (örnek):** Basic 30g · Pro 90–365g · Lifetime.

---

### 6.15 Admin Control Center (web)

Adres: `http://127.0.0.1:8790`  
Dosya: `ototext-admin-panel.html` (başka siteye taşınabilir)

| Sekme | Ne yönetir? |
|-------|-------------|
| Overview | Canlı durum, hızlı start/stop, PANIC |
| Genel / Log | logGroupId, prefix, bot WID, min üye, mining |
| Yayın | running, aralık, pencere, metin / rotasyon |
| DM | metin, kuyruk, pencere, aralık |
| Guard | tüm koruma bayrakları + grup listesi |
| Numaralar | çoklu instance JSON |
| Admin / Black | yetki + kara liste |
| Canlı / Loglar | daily events, pending, healthWatch |
| Lisanslar | üret / ZIP / iptal / doğrula |
| JSON Lab | ham state merge veya replace |

API:
- `GET /api/bot/state`
- `POST /api/bot/patch`
- `POST /api/bot/action`
- `POST /api/panic`
- lisans endpoint’leri

Token’lar GET’te maskelenir; panel `***` bırakırsa eski token korunur.

---

## 7. Onay / sihirbaz sistemi (pending)

Kritik işlemler (otox, dm…) hemen başlamaz; **pending** oluşur:
- `!onay` / `!evet` → onayla  
- `!hayir` → bağlama göre (rotasyon hayır ≠ her zaman iptal)  
- `!iptal` → iptal  
- Süre dolunca pending düşer  
- Panelden “Pending Temizle” ile silinebilir  

---

## 8. Zaman pencereleri

`!zaman-otox` ve `!zaman-dm` **Europe/Istanbul** saatine göre çalışır.  
Gece / gündüz sınırlı yayın için: örn. `22:00-01:00` (gece yarısını aşan aralık desteklenir).

---

## 9. Güvenlik ve riskler (dürüstçe)

| Konu | Gerçek |
|------|--------|
| Resmi WhatsApp Business API mi? | Hayır — Green API (bağlı cihaz / instance) |
| Numara ban yer mi? | Evet, kullanım yoğunluğuna göre risk var |
| Grup ban? | Daha seyrek; asıl risk hesap / cihaz |
| Ototext ne yapar? | Riski azaltmaya yardım (hız, rotasyon, uyarı); garanti vermez |
| Panel “hesaba girer mi?” | Hayır — state + lisans; oturum çalmaz |
| `!sil` | Sadece admin + bot admin gruplarda |

Satışta “ban olmaz” demeyin; “kontrollü kullanım + erken uyarı” deyin.

---

## 10. Tipik kullanım senaryoları

1. **Gece duyurusu:** `!zaman-otox 22:00-01:00` + rotasyonlu 3 metin + `!sure 5`  
2. **Grup koruma:** Botu admin yap → `!guard ac` → spam/aramada kick + kilit  
3. **Temizlik:** `!sil 20` ile son spam mesajlarını sil  
4. **Çok numara:** Ana + yedek instance; birinde uyarı gelince diğerine geç  
5. **Satış:** Panelden lisans + ZIP → müşteri QR okutur → senin klonun çalışır  
6. **Kriz:** Log’da ❗ ban uyarısı → kontrol → gerekirse panelden PANIC  

---

## 11. Dosya / bileşen haritası

| Yol | Rol |
|-----|-----|
| `scripts/build-ototext-bot.py` | Komut + worker JS üretici |
| `n8n-workflows/ototext-bot-commands.json` | Komut workflow |
| `n8n-workflows/ototext-bot-worker.json` | Worker workflow |
| `data/ototext-state.json` | Canlı state |
| `seller/panel.py` | Admin API + satış |
| `seller/license.py` | Lisans HMAC |
| `ototext-admin-panel.html` | Control Center UI |
| `scripts/start-mobile-setup.sh` | QR müşteri kurulumu |
| `scripts/start-seller-panel.sh` | Panel başlat |
| `SATIS.md` | Satış prosedürü |
| `TANITIM.md` | Bu doküman |

---

## 12. Komut sözlüğü (hızlı referans)

```
!yardim
!otox · !adet · !metin · !onay · !evet · !hayir · !iptal
!panic · !durdur · !durum · !sure
!zaman-otox · !zaman-dm
!dm · !dm-durdur · !dm-sure · !dm-durum
!log-grup · !rapor · !istatistik · !lisans
!gruplar · !davetler · !filtre · !min-uye · !temizlik
!black · !black-ekle · !black-cikar · !black-liste
!mining · !mining-baslat · !mining-durdur · !mining-durum
!katil · !tumkatil · !karakter ayarla
!admin · !admin-ekle · !admin-cikar · !admin-list
!prefix · !prefix-main · !prefix-ekle · !prefix-cikar
!numara · !numara-ekle · !numara-liste · !numara-aktif · !numara-sil · !numara-yenile
!guard · !guard ac/kapat · !guard grup · !guard sticker · !guard yaz/kilit
!sil N
```

---

## 13. Tek bakışta vaat

**Ototext =**  
WhatsApp komutları + zamanlı yayın/DM + guard + silme + ban uyarısı + çoklu numara + web’den her şeyi yönetme + lisansla kopya satma.

Kurulum müşteri için QR kadar basit; operasyon sahibi için panel kadar derin.

---

*No Name Force · Ototext*
