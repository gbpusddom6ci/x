# Trading Analysis Tools

Forex trading için çoklu timeframe analiz araçları.

## Uygulamalar

### 🕐 app48 (48 dakika)
- 48 dakikalık mumlarla sayım
- DC (Doji Candle) listesi ve analizi
- 12→48 dakika dönüştürücü
- Port: `2020`

### 🕐 app72 (72 dakika)
- 72 dakikalık mumlarla sayım
- DC analizi ve offset matrisi
- 12→72 dakika dönüştürücü (7 tane 12m = 1 tane 72m)
- Port: `2172`

### 🕐 app80 (80 dakika)
- 80 dakikalık mumlarla sayım
- DC analizi ve offset matrisi
- 20→80 dakika dönüştürücü (4 tane 20m = 1 tane 80m)
- Port: `2180`

### 🕐 app120 (120 dakika)
- 120 dakikalık mumlarla sayım
- DC istisnası ve offset sistemi
- 60→120 dakika dönüştürücü
- Port: `2120`

### 🎯 app120_iov (IOV Analysis)
- IOV (Inverse OC Value) mum analizi
- 2 haftalık 120m veri desteği
- Özelleştirilebilir limit sistemi
- Tüm offsetler (-3..+3) taranır
- Port: `2121`

### 🕐 app321 (60 dakika)
- 60 dakikalık sayım araçları
- DC listesi ve offset matrisi
- Port: `2019`

### 📰 app72_iou (IOU News Checker)
- IOU offset analizi için ForexFactory entegrasyonu
- **Selenium ile otomatik veri çekme (40 hafta tek komutla!)**
- Mid/High impact haber kontrolü
- 72 dakikalık mum aralığı taraması
- Otomatik News kolonu ekleme
- Cache sistemi (tekrar indirme yok)
- Port: `2172`

### 🏠 landing (Ana Sayfa)
- Tüm uygulamalara tek yerden erişim
- Port: `2000`

## Hızlı Başlangıç

```bash
# Landing page
python3 -m landing.web

# app72 web arayüzü
python3 -m app72.web

# app80 web arayüzü
python3 -m app80.web

# app120 web arayüzü
python3 -m app120.web

# app120_iov web arayüzü (IOV analizi)
python3 -m app120_iov.web

# app48 web arayüzü
python3 -m app48.web

# app321 web arayüzü
python3 -m app321.web

# app72_iou news checker (IOU CSV + ForexFactory)
# İlk önce 40 haftalık veriyi çek (bir kere yapılır):
python3 -m forexfactory.cli --weeks 40

# Sonra IOU analizlerini çalıştır:
python3 -m app72_iou.web
# veya CLI:
python3 -m app72_iou.cli ornek.csv output.csv
```

## Özellikler

- ✅ Esnek CSV okuyucu (farklı formatlar desteklenir)
- ✅ Timezone dönüşümü (UTC-5 → UTC-4)
- ✅ DC (Doji Candle) algılama ve filtreleme
- ✅ Sequence bazlı sayım (S1, S2)
- ✅ Offset sistemi (-3 ile +3 arası)
- ✅ Matrix görünümü (tüm offsetler tek ekranda)
- ✅ Timeframe dönüştürücüler
- ✅ Tahmin (prediction) desteği
- ✅ ForexFactory news integration (app72_iou)
- ✅ Economic calendar overlay
