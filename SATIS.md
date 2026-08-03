# Ototext — Satış / Müşteri Kopyası Sistemi

Bu repo hem **senin ana sistemin** hem de **satacağın müşteri kopyalarının** kaynağıdır.

## Senin tarafın (satıcı)

```bash
bash scripts/start-seller-panel.sh
```

Tarayıcıda: `http://127.0.0.1:8790`

1. Müşteri adı yaz
2. Kaç günlük lisans (30 / 90 / 365 / lifetime için 36500)
3. Plan seç (standard / pro / lifetime)
4. **Lisans Üret**
5. Listeden **ZIP Kit** → müşteriye gönder

Panel kayıtları: `seller/customers.json`  
İptal: panelden **İptal** (yeni kit üretilmez; online `/api/verify` iptali görür)

CLI:

```bash
python3 seller/license.py create --name "Ahmet" --days 30 --plan pro
python3 seller/license.py list
python3 seller/license.py revoke --jti <uuid>
python3 seller/license.py verify --key "....."
```

## Müşteriye ne veriyorsun?

ZIP içinde lisans + bot + kurulum. **Müşteri API/token girmez.**

Sen (satıcı) ZIP’ten önce her müşteri için Green API’de bir instance oluşturup  
`.env.example` içine `ID_INSTANCE` + `API_TOKEN` yaz (veya panelden kit üretirken doldur).  
İstersen `GREEN_API_PARTNER_TOKEN` ile kurulum instance’ı otomatik de üretebilir.

Müşteri:

1. ZIP’i açar / sunucuda çalıştırır
2. `bash scripts/start-mobile-setup.sh`
3. Telefondaki linki açar → **QR’ı WhatsApp’tan okutur**
4. Sistem webhook + botu kendi kurar → `!yardim`

## Paket önerisi

| Paket | Süre | Not |
|-------|------|-----|
| Basic | 30 gün | standard |
| Pro | 90–365 gün | pro |
| Lifetime | 36500 gün | lifetime |

Fiyatı sen belirlersin; sistem süre + imzayı kontrol eder.

## Senin kendi kopyan

```bash
export LICENSE_SKIP=1
bash scripts/setup-native.sh
```

veya kendine sınırsız lisans üretip `LICENSE_KEY` olarak `.env`’e koy.
