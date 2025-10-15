# app80 - 80 Dakikalık Timeframe Analizi

80 dakikalık mumlar için sayım, DC analizi ve converter araçları.

## Özellikler

- ✅ 80 dakikalık mum sayımı
- ✅ DC (Doji Candle) algılama ve filtreleme
- ✅ Sequence bazlı sayım (S1, S2)
- ✅ Offset sistemi (-3 ile +3 arası)
- ✅ Matrix görünümü (tüm offsetler)
- ✅ 20→80 dakika converter (4 tane 20m = 1 tane 80m)
- ✅ Timezone dönüşümü (UTC-5 → UTC-4)
- ✅ Prediction desteği

## Web Arayüzü

```bash
python3 -m app80.web --host 0.0.0.0 --port 2180
```

Tarayıcıdan `http://localhost:2180/` adresine gidin.

### Sayfalar

1. **Analiz** - CSV yükleyip sequence sayımı yapın
2. **DC List** - Tüm DC mumlarını listeleyin
3. **Matrix** - Tüm offset değerlerini tek ekranda görün
4. **20→80 Converter** - 20 dakikalık mumları 80 dakikaya dönüştürün (4 tane 20m = 1 tane 80m)

## CLI Kullanımı

### Counter (Sayım)

```bash
# Basit sayım
python3 -m app80.counter --csv data.csv

# S1 dizisi ile
python3 -m app80.counter --csv data.csv --sequence S1

# Offset ile
python3 -m app80.counter --csv data.csv --sequence S2 --offset +2

# DC bilgisi göster
python3 -m app80.counter --csv data.csv --show-dc

# Belirli bir sequence değerini tahmin et
python3 -m app80.counter --csv data.csv --predict 37

# Sonraki sequence değerini tahmin et
python3 -m app80.counter --csv data.csv --predict-next
```

### Converter (20m → 80m)

```bash
# Dosyaya kaydet
python3 -m app80.main --csv 20m_data.csv --output 80m_output.csv

# Stdout'a yazdır
python3 -m app80.main --csv 20m_data.csv

# Timezone belirt
python3 -m app80.main --csv 20m_data.csv --input-tz UTC-5 --output 80m_data.csv
```

## CSV Formatı

Gerekli sütunlar (eş anlamlılar desteklenir):
- **Time** / Timestamp / Date / DateTime
- **Open** / O / Open (First)
- **High** / H
- **Low** / L
- **Close (Last)** / Close / Last / C

Örnek:
```csv
Time,Open,High,Low,Close (Last)
2024-01-01 18:00:00,1.09500,1.09520,1.09480,1.09510
2024-01-01 18:20:00,1.09510,1.09550,1.09500,1.09540
```

## Parametreler

### Sequence Değerleri
- **S1**: [1, 3, 7, 13, 21, 31, 43, 57, 73, 91, 111, 133, 157]
- **S2**: [1, 5, 9, 17, 25, 37, 49, 65, 81, 101, 121, 145, 169]

### Offset Sistemi
Başlangıç zamanını 80 dakika adımlarla kaydırır:
- `-3`: 240 dakika geri (3 × 80)
- `-2`: 160 dakika geri (2 × 80)
- `-1`: 80 dakika geri
- `0`: Offset yok (varsayılan)
- `+1`: 80 dakika ileri
- `+2`: 160 dakika ileri (2 × 80)
- `+3`: 240 dakika ileri (3 × 80)

### DC (Doji Candle) Kuralları

Bir mum DC olarak işaretlenir eğer:
1. High ≤ prev.High
2. Low ≥ prev.Low
3. Close, prev mumun [Open, Close] aralığında
4. **Pazar hariç, 18:00, 19:20 veya 20:40 mumu değilse** (günlük cycle noktaları)
5. Hafta kapanış mumu (Cuma 16:40) değilse
6. Önceki mum DC değilse

**Önemli:** 
- Pazartesi-Cumartesi günlerinde 18:00, 19:20 ve 20:40 mumları DC olamaz (günlük cycle başlangıç noktaları). Pazar günlerinde bu kısıtlama yoktur (hafta açılışı).
- Cuma 16:40 mumu DC olamaz (hafta kapanışı - 80 dakikalık sistemde son mum).

DC mumlar sayımda atlanır.

## Notlar

- Başlangıç zamanı sabit: **18:00** (hafta açılışı, Pazar akşamı)
- Hafta kapanışı: **Cuma 16:40** (80 dakikalık sistemde)
- Haftasonu mumları otomatik filtrelenir
- Timezone: Girdi UTC-5 ise otomatik +1 saat eklenir → UTC-4

## Örnekler

### Web üzerinden analiz
1. `python3 -m app80.web` ile sunucuyu başlat
2. Tarayıcıdan `http://localhost:2180/` aç
3. CSV dosyasını yükle
4. Sequence (S1/S2) seç
5. Offset ayarla
6. "Analiz Et" butonuna tıkla

### CLI ile hızlı sayım
```bash
python3 -m app80.counter \
  --csv mydata.csv \
  --sequence S2 \
  --offset 0 \
  --show-dc
```

### Converter kullanımı
```bash
# 20 dakikalık veriyi 80 dakikaya çevir (4 tane 20m = 1 tane 80m)
python3 -m app80.main \
  --csv 20m_eurusd.csv \
  --input-tz UTC-5 \
  --output 80m_eurusd.csv
```
