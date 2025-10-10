# app72 - 72 Dakikalık Timeframe Analizi

72 dakikalık mumlar için sayım, DC analizi ve converter araçları.

## Özellikler

- ✅ 72 dakikalık mum sayımı
- ✅ DC (Doji Candle) algılama ve filtreleme
- ✅ Sequence bazlı sayım (S1, S2)
- ✅ Offset sistemi (-3 ile +3 arası)
- ✅ Matrix görünümü (tüm offsetler)
- ✅ 12→72 dakika converter (7 tane 12m = 1 tane 72m)
- ✅ Timezone dönüşümü (UTC-5 → UTC-4)
- ✅ Prediction desteği

## Web Arayüzü

```bash
python3 -m app72.web --host 0.0.0.0 --port 2172
```

Tarayıcıdan `http://localhost:2172/` adresine gidin.

### Sayfalar

1. **Counter** - CSV yükleyip sequence sayımı yapın
2. **IOU** - Inverse OC - Uniform sign analizi (haber verileri ile)
3. **DC List** - Tüm DC mumlarını listeleyin
4. **Matrix** - Tüm offset değerlerini tek ekranda görün
5. **12→72 Converter** - 12 dakikalık mumları 72 dakikaya dönüştürün (7 tane 12m = 1 tane 72m)
6. **Converter** - Alternatif converter arayüzü

## CLI Kullanımı

### Counter (Sayım)

```bash
# Basit sayım
python3 -m app72.counter --csv data.csv

# S1 dizisi ile
python3 -m app72.counter --csv data.csv --sequence S1

# Offset ile
python3 -m app72.counter --csv data.csv --sequence S2 --offset +2

# DC bilgisi göster
python3 -m app72.counter --csv data.csv --show-dc

# Belirli bir sequence değerini tahmin et
python3 -m app72.counter --csv data.csv --predict 37

# Sonraki sequence değerini tahmin et
python3 -m app72.counter --csv data.csv --predict-next
```

### Converter (12m → 72m)

```bash
# Dosyaya kaydet
python3 -m app72.main --csv 12m_data.csv --output 72m_output.csv

# Stdout'a yazdır
python3 -m app72.main --csv 12m_data.csv

# Timezone belirt
python3 -m app72.main --csv 12m_data.csv --input-tz UTC-5 --output 72m_data.csv
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
2024-01-01 19:12:00,1.09510,1.09550,1.09500,1.09540
```

## Parametreler

### Sequence Değerleri
- **S1**: [1, 3, 7, 13, 21, 31, 43, 57, 73, 91, 111, 133, 157]
- **S2**: [1, 5, 9, 17, 25, 37, 49, 65, 81, 101, 121, 145, 169]

### Offset Sistemi
Başlangıç zamanını 72 dakika adımlarla kaydırır:
- `-3`: 216 dakika geri (3 × 72)
- `-2`: 144 dakika geri (2 × 72)
- `-1`: 72 dakika geri
- `0`: Offset yok (varsayılan)
- `+1`: 72 dakika ileri
- `+2`: 144 dakika ileri (2 × 72)
- `+3`: 216 dakika ileri (3 × 72)

### DC (Doji Candle) Kuralları

Bir mum DC olarak işaretlenir eğer:
1. High ≤ prev.High
2. Low ≥ prev.Low
3. Close, prev mumun [Open, Close] aralığında
4. **18:00 mumu değilse** (Pazar dahil - 2. hafta başlangıcı için)
5. **Cuma 16:48 mumu değilse** (1. hafta bitimindeki son mum)
6. **Pazar hariç, 19:12 veya 20:24 mumu değilse** (günlük cycle noktaları)
7. Hafta kapanış mumu (Cuma 16:00) değilse
8. Önceki mum DC değilse

**Önemli - 2 Haftalık Veri İçin:**
- **18:00** mumu ASLA DC olamaz (Pazar günü dahil - ikinci hafta başlangıcı)
- **Cuma 16:48** mumu ASLA DC olamaz (birinci hafta bitimindeki son mum)
- **19:12 ve 20:24** mumları Pazar hariç DC olamaz (günlük cycle noktaları)

DC mumlar sayımda atlanır.

## Notlar

- Başlangıç zamanı sabit: **18:00** (hafta açılışı, Pazar akşamı)
- Hafta kapanışı: **Cuma 16:00**
- Haftasonu mumları otomatik filtrelenir
- Timezone: Girdi UTC-5 ise otomatik +1 saat eklenir → UTC-4

## Örnekler

### Web üzerinden analiz
1. `python3 -m app72.web` ile sunucuyu başlat
2. Tarayıcıdan `http://localhost:2172/` aç
3. CSV dosyasını yükle
4. Sequence (S1/S2) seç
5. Offset ayarla
6. "Analiz Et" butonuna tıkla

### CLI ile hızlı sayım
```bash
python3 -m app72.counter \
  --csv mydata.csv \
  --sequence S2 \
  --offset 0 \
  --show-dc
```

### Converter kullanımı
```bash
# 12 dakikalık veriyi 72 dakikaya çevir (7 tane 12m = 1 tane 72m)
python3 -m app72.main \
  --csv 12m_eurusd.csv \
  --input-tz UTC-5 \
  --output 72m_eurusd.csv
```

## IOU Analizi ve Haber Verileri

### IOU (Inverse OC - Uniform sign) Nedir?

IOU analizi, aynı yönlü hareket eden ardışık mumları tespit eder:
- **Kriterler:**
  1. |OC| ≥ limit (varsayılan 0.1)
  2. |PrevOC| ≥ limit
  3. OC ve PrevOC **aynı işarete sahip** (++ veya --)

### Haber Verileri (Economic Calendar)

IOU tablosu, ForexFactory economic calendar verilerini otomatik olarak yükler ve her mumun 72 dakikalık aralığındaki haberleri gösterir.

#### Haber Verisi Ekleme

1. **Klasör:** `news_data/` (workspace root'ta)
2. **Format:** JSON (ForexFactory formatı)
3. **Otomatik yükleme:** Klasöre JSON dosyası eklediğinizde otomatik algılanır

**Örnek:**
```bash
# Yeni haber verisi ekle
cp nisan2025.json news_data/
cp mayis2025.json news_data/

# Sistem otomatik olarak tüm JSON dosyalarını yükler ve birleştirir
```

#### JSON Format Örneği
```json
{
  "meta": {
    "source": "forex_factory",
    "year": 2025
  },
  "days": [
    {
      "date": "2025-03-17",
      "weekday": "Mon",
      "events": [
        {
          "time_24h": "08:30",
          "currency": "USD",
          "title": "Core Retail Sales m/m",
          "values": {
            "actual": "0.3%",
            "forecast": "0.3%",
            "previous": "-0.6%"
          }
        }
      ]
    }
  ]
}
```

**Not:** Saatler **UTC-4** formatında olmalıdır (mum verisi ile uyumlu).

#### IOU Tablosunda Haber Gösterimi

- Mumun **başlangıç zamanından** itibaren **72 dakika** içindeki tüm haberler gösterilir
- Format: `var: CURRENCY Title (actual:X, forecast:Y, prev:Z); ...`
- Birden fazla haber `;` ile ayrılır
- Haber yoksa: `-` gösterilir

**Örnek:**
```
Timestamp: 03-17 04:48
Haber: var: USD ISM Manufacturing PMI (actual:50.3, forecast:50.6, prev:50.9); EUR CPI Flash Estimate (actual:2.4%, forecast:2.3%, prev:2.5%)
```
