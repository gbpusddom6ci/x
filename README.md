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

### 🕐 app120 (120 dakika)
- 120 dakikalık mumlarla sayım
- DC istisnası ve offset sistemi
- 60→120 dakika dönüştürücü
- Port: `2120`

### 🕐 app321 (60 dakika)
- 60 dakikalık sayım araçları
- DC listesi ve offset matrisi
- Port: `2019`

### 🏠 landing (Ana Sayfa)
- Tüm uygulamalara tek yerden erişim
- Port: `2000`

## Hızlı Başlangıç

```bash
# Landing page
python3 -m landing.web

# app72 web arayüzü
python3 -m app72.web

# app120 web arayüzü
python3 -m app120.web

# app48 web arayüzü
python3 -m app48.web

# app321 web arayüzü
python3 -m app321.web
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
