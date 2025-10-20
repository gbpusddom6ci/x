# 📘 x1 Proje Teknik Dokümantasyonu

**Son Güncelleme:** 2025-01-18  
**Versiyon:** 2.0  
**Amaç:** Bu dokümantasyon AI agent'ların projeyi eksiksiz anlaması için hazırlanmıştır.

Bu doküman **gerçek kod implementasyonuna** dayanır ve varsayım içermez.

---

## 📑 İçindekiler

### Temel Bilgiler
- [🎯 Proje Özeti](#-proje-özeti)
- [📂 Proje Yapısı](#-proje-yapısı)
- [📊 Veri Yapıları](#-veri-yapıları)
- [🔑 Sequence Dizileri](#-sequence-dizileri)

### Core Mantık
- [🕐 Distorted Candle (DC) Kuralları](#-distorted-candle-dc-kuralları)
  - [Temel DC Tanımı](#temel-dc-tanımı-tüm-uygulamalar)
  - [Ardışık DC Yasağı](#ardışık-dc-yasağı-tüm-uygulamalar)
  - [App-Specific DC İstisnaları](#app-specific-dc-i̇stisnaları)
- [🎯 Offset Mantığı](#-offset-mantığı)
- [📍 Sequence Allocation Mantığı](#-sequence-allocation-mantığı)

### Özellikler
- [🔍 IOU Analizi](#-iou-inverse-oc---uniform-sign-analizi)
  - [IOU Kriterleri](#iou-kriterleri-5-şart)
  - [Tolerance](#tolerance-güvenlik-payı)
  - [XYZ Küme Analizi](#xyz-küme-analizi)
  - [Haber Verisi](#haber-verisi-news_datajson)
- [🔄 Converter'lar](#-converterlar)

### Teknik Detaylar
- [📝 CSV Format Desteği](#-csv-format-desteği)
- [🎨 Web Arayüzü Detayları](#-web-arayüzü-detayları)
- [🌐 Web Server Routes](#-web-server-routes)

### Kullanım
- [⚙️ CLI Kullanımı](#️-cli-kullanımı)
- [🚀 Web Başlatma](#-web-başlatma)

### Referans
- [📌 Kritik İmplementasyon Notları](#-kritik-i̇mplementasyon-notları)
- [🐛 Bilinen Limitasyonlar](#-bilinen-limitasyonlar)
- [📚 Referans: Fonksiyon İmzaları](#-referans-fonksiyon-i̇mzaları)
- [🎓 Örnek Kullanım Senaryoları](#-örnek-kullanım-senaryoları)

---

## 🎯 Proje Özeti

**x1:** Python-based forex/kripto mum analiz platformu.

**5 Ana Uygulama:**
- `app321` → 60 dakika (60m)
- `app48` → 48 dakika (48m)
- `app72` → 72 dakika (72m)
- `app80` → 80 dakika (80m)
- `app120` → 120 dakika (120m)

**Teknoloji Stack:**
- Pure Python 3.x
- `http.server` (BaseHTTPRequestHandler)
- `csv` module (dialect detection)
- `email.parser` (multipart form-data)
- `dataclasses`
- No external dependencies

**Port Mapping:**
```
app321  → localhost:2160
app48   → localhost:2148
app72   → localhost:2172
app80   → localhost:2180
app120  → localhost:2120
landing → localhost:8000
```

---

## 📂 Proje Yapısı

```
x1/
├── app321/          # 60m uygulama
│   ├── main.py      # CLI + IOU + sayım mantığı
│   └── web.py       # Web arayüzü (Counter, DC, Matrix, IOU)
│
├── app48/           # 48m uygulama
│   ├── main.py      # CLI + 12m→48m converter + IOU
│   └── web.py       # Web (Counter, DC, Matrix, IOU, 12→48 Converter)
│
├── app72/           # 72m uygulama
│   ├── counter.py   # Sayım mantığı + IOU
│   ├── main.py      # 12m→72m converter
│   └── web.py       # Web (Counter, DC, Matrix, IOU, 12→72 Converter)
│
├── app80/           # 80m uygulama
│   ├── counter.py   # Sayım mantığı + IOU
│   ├── main.py      # 20m→80m converter
│   └── web.py       # Web (Counter, DC, Matrix, IOU, 20→80 Converter)
│
├── app120/          # 120m uygulama
│   ├── counter.py   # Sayım mantığı
│   ├── main.py      # 60m→120m converter
│   ├── web.py       # Web (Counter, DC, Matrix, IOV, IOU, 60→120 Converter)
│   ├── iov/         # IOV modülü
│   └── iou/         # IOU modülü
│
├── landing/         # Ana giriş sayfası
│   └── web.py
│
├── appsuite/        # Reverse proxy (tüm applar)
│   └── web.py
│
├── news_data/       # ForexFactory JSON dosyaları
├── favicon/         # Favicon dosyaları
└── agents.md        # Bu dokümantasyon
```

---

## 📊 Veri Yapıları

### Candle (Mum)

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Candle:
    ts: datetime      # Timestamp (UTC-4, timezone-naive)
    open: float       # Açılış fiyatı
    high: float       # En yüksek fiyat
    low: float        # En düşük fiyat
    close: float      # Kapanış fiyatı
```

**Not:** `app48` için ek alan:
```python
synthetic: bool = False  # Sentetik mum mu?
```

### SequenceAllocation

```python
@dataclass
class SequenceAllocation:
    idx: Optional[int]      # Candle index (None = predicted/missing)
    ts: Optional[datetime]  # Timestamp (None = predicted)
    used_dc: bool           # DC mumuna yerleştirildi mi?
```

### IOUResult

```python
@dataclass
class IOUResult:
    seq_value: int          # Sequence değeri
    index: int              # Candle index
    timestamp: datetime     # Candle timestamp
    oc: float               # OC (open-close) değeri
    prev_oc: float          # Önceki mumun OC değeri
    prev_index: int         # Önceki mum index
    prev_timestamp: datetime # Önceki mum timestamp
```

---

## 🔑 Sequence Dizileri

### Tam Diziler (SEQUENCES)

```python
SEQUENCES = {
    "S1": [1, 3, 7, 13, 21, 31, 43, 57, 73, 91, 111, 133, 157],
    "S2": [1, 5, 9, 17, 25, 37, 49, 65, 81, 101, 121, 145, 169],
}
```

### Filtrelenmiş Diziler (SEQUENCES_FILTERED)

IOU analizi için kullanılır (erken değerler hariç):

```python
SEQUENCES_FILTERED = {
    "S1": [7, 13, 21, 31, 43, 57, 73, 91, 111, 133, 157],    # 1,3 excluded
    "S2": [9, 17, 25, 37, 49, 65, 81, 101, 121, 145, 169],   # 1,5 excluded
}
```

---

## 🕐 Distorted Candle (DC) Kuralları

### Temel DC Tanımı (Tüm Uygulamalar)

Bir mum **DC**'dir ancak ve ancak **3 şart** birden sağlanırsa:

```python
prev = candles[i - 1]
cur = candles[i]

# Şart 1: High geçmemeli
cur.high <= prev.high

# Şart 2: Low düşmemeli
cur.low >= prev.low

# Şart 3: Close önceki mumun open-close aralığında
min(prev.open, prev.close) <= cur.close <= max(prev.open, prev.close)
```

### Ardışık DC Yasağı (Tüm Uygulamalar)

```python
# Önceki mum DC ise, bu mum DC olarak işaretlenmez
if prev_flag and cond:
    cond = False
```

### App-Specific DC İstisnaları

Her uygulamanın **farklı** DC istisna kuralları vardır:

#### app321 (60m)

```python
# Pazar HARİÇ, 13:00 - 20:00 arası DC SAYILMAZ (20:00 dahil değil)
if ts.weekday() != 6 and time(13, 0) <= ts.time() < time(20, 0):
    return False  # DC değil (istisna)
```

**Not:** `compute_sequence_allocations` içinde ayrıca:
```python
# while döngüsünde 13:00 - 20:00 kontrolü (20:00 dahil)
dc_exception = (tod >= time(13, 0)) and (tod <= time(20, 0))
```

#### app48 (48m)

```python
# İlk gün (Pazar) HARİÇ, 18:00, 18:48 ve 19:36 mumları DC olamaz
# İlk gün = verinin başladığı gün (input data'nın ilk tarihi)
first_day = candles[0].ts.date() if candles else None

if first_day and cur.ts.date() != first_day:
    if (cur.ts.hour == 18 and cur.ts.minute == 0) or \
       (cur.ts.hour == 18 and cur.ts.minute == 48) or \
       (cur.ts.hour == 19 and cur.ts.minute == 36):
        cond = False  # DC olamaz (istisna)
```

#### app72 (72m)

```python
# 1. 18:00 mumu ASLA DC olamaz (Pazar dahil)
if cur.ts.hour == 18 and cur.ts.minute == 0:
    cond = False

# 2. Pazar HARİÇ: 19:12 ve 20:24 DC olamaz (günlük cycle noktaları)
elif cur.ts.weekday() != 6:
    if (cur.ts.hour == 19 and cur.ts.minute == 12) or \
       (cur.ts.hour == 20 and cur.ts.minute == 24):
        cond = False

# 3. Cuma 16:48 ASLA DC olamaz (1. hafta bitimindeki son mum)
if cur.ts.weekday() == 4 and cur.ts.hour == 16 and cur.ts.minute == 48:
    cond = False

# 4. Hafta kapanış mumu (16:00) DC olamaz
# Bir sonraki mumla arasında >72dk gap varsa kapanış sayılır
if cur.ts.hour == 16 and cur.ts.minute == 0:
    if i + 1 >= len(candles):
        is_week_close = True
    else:
        gap_minutes = (candles[i + 1].ts - cur.ts).total_seconds() / 60
        if gap_minutes > 72:
            is_week_close = True
if is_week_close:
    cond = False
```

#### app80 (80m)

```python
# 1. Pazar HARİÇ: 18:00, 19:20, 20:40 DC olamaz (günlük cycle noktaları)
if cur.ts.weekday() != 6:
    if (cur.ts.hour == 18 and cur.ts.minute == 0) or \
       (cur.ts.hour == 19 and cur.ts.minute == 20) or \
       (cur.ts.hour == 20 and cur.ts.minute == 40):
        cond = False

# 2. Cuma 16:40 DC olamaz (hafta kapanışı)
# 80 dakikalık sistemde Cuma son mum 16:40 (14:00 → 15:20 → 16:40)
if cur.ts.weekday() == 4 and cur.ts.hour == 16 and cur.ts.minute == 40:
    if i + 1 >= len(candles):
        is_week_close = True
    else:
        gap_minutes = (candles[i + 1].ts - cur.ts).total_seconds() / 60
        if gap_minutes > 80:
            is_week_close = True
if is_week_close:
    cond = False
```

#### app120 (120m)

```python
# 1. 18:00 mumu DC olamaz
if cur.ts.hour == 18 and cur.ts.minute == 0:
    cond = False

# 2. Hafta kapanış mumu (16:00) DC olamaz
# Bir sonraki mumla arasında >120dk gap varsa kapanış sayılır
if cur.ts.hour == 16 and cur.ts.minute == 0:
    if i + 1 >= len(candles):
        is_week_close = True
    else:
        gap_minutes = (candles[i + 1].ts - cur.ts).total_seconds() / 60
        if gap_minutes > 120:
            is_week_close = True
if is_week_close:
    cond = False
```

**Not:** app120'de günlük cycle'a özel ek saat istisnaları yok (app72/app80'deki gibi).

---

## 🎯 Offset Mantığı

### Temel Kural

**Base Mumu (18:00):** Tüm uygulamalarda sayım `18:00` mumundan başlar.

```python
DEFAULT_START_TOD = time(hour=18, minute=0)
```

**Offset Aralığı:** `-3` ile `+3` arası (toplam 7 offset)

```
Offset -3 → 18:00'dan 3 adım geriye
Offset -2 → 18:00'dan 2 adım geriye
Offset -1 → 18:00'dan 1 adım geriye
Offset  0 → 18:00 (base)
Offset +1 → 18:00'dan 1 adım ileriye
Offset +2 → 18:00'dan 2 adım ileriye
Offset +3 → 18:00'dan 3 adım ileriye
```

### Offset Hesaplama

```python
# Hedef zaman hesaplama
target_ts = base_candle.ts + timedelta(minutes=offset * MINUTES_PER_STEP)

# Örnek (app72, offset=+2):
# base: 2025-01-10 18:00:00
# target_ts = 2025-01-10 18:00:00 + (2 * 72) dakika
# target_ts = 2025-01-10 20:24:00
```

### DC ile İlişkisi

**Kritik:** DC mumlar sayımda atlanır, ancak **last step DC rule** uygulanır:

```python
# Sayım sırasında
if is_dc:
    if counted == steps_needed - 1:
        last_dc_idx = cur_idx  # Son adımdaki DC'yi kaydet
    continue  # DC'yi sayma

# Son adımdaysa ve DC denk geldiyse
if last_dc_idx is not None:
    assigned_idx = last_dc_idx
    used_dc = True  # DC'ye yerleştirildi
```

---

## 📍 Sequence Allocation Mantığı

### compute_sequence_allocations()

Her sequence değeri için mum indeksi atayan temel fonksiyon.

```python
def compute_sequence_allocations(
    candles: List[Candle],
    dc_flags: List[Optional[bool]],
    start_idx: int,
    seq_values: List[int],
) -> List[SequenceAllocation]:
```

**Algoritma:**

1. **İlk değer:** `start_idx` direkt atanır
2. **Sonraki değerler için:**
   - Adım farkı kadar ilerle (`cur_val - prev_val`)
   - DC mumları **sayma** (skip)
   - Son adımda DC'ye denk gelirse, o DC'yi kullan (`used_dc=True`)

**Örnek:**
```python
# start_idx = 5, seq_values = [1, 7, 13]
# DC'ler: index 8, 9

# seq=1  → idx=5  (başlangıç)
# seq=7  → 5'ten 6 adım (7-1=6)
#          6,7,8(DC skip),9(DC skip),10,11,12,13 → idx=13
# seq=13 → 13'ten 6 adım (13-7=6) → idx=19
```

### Missing Steps Handling

Hedef offset mumu veride yoksa (veri eksikliği):

```python
# 1. Hedef zamandan sonraki ilk mumu bul
after_idx = None
for i, candle in enumerate(candles):
    if candle.ts >= target_ts:
        after_idx = i
        break

# 2. Missing steps hesapla
delta_minutes = int((candle.ts - target_ts).total_seconds() // 60)
missing_steps = max(0, delta_minutes // MINUTES_PER_STEP)

# 3. Sequence'ı missing_steps+1'den başlat
actual_start_count = missing_steps + 1
seq_compute = [actual_start_count]
for v in seq_values:
    if v > missing_steps and v != actual_start_count:
        seq_compute.append(v)
```

### Prediction Logic

Veri dışındaki sequence değerleri için zaman tahmini:

```python
def predict_time_after_n_steps(base_ts: datetime, n_steps: int) -> datetime:
    """
    n adım sonrasını hesaplar, haftasonu boşluğunu dikkate alır.
    """
    current_ts = base_ts
    for _ in range(n_steps):
        current_ts = predict_next_candle_time(current_ts)
    return current_ts
```

**Haftasonu Kuralları (app72, app80, app120):**

```python
def predict_next_candle_time(current_ts: datetime) -> datetime:
    """
    Piyasa: Cuma 16:00'da kapanır, Pazar 18:00'da açılır.
    """
    # Cuma 16:00'dan sonra → Pazar 18:00
    if current_ts.weekday() == 4 and current_ts.hour == 16:
        return datetime.combine(
            current_ts.date() + timedelta(days=2),
            time(hour=18, minute=0)
        )
    
    # Cumartesi → Pazar 18:00
    if current_ts.weekday() == 5:
        return datetime.combine(
            current_ts.date() + timedelta(days=1),
            time(hour=18, minute=0)
        )
    
    # Pazar 18:00'dan önce → Pazar 18:00
    if current_ts.weekday() == 6 and current_ts.hour < 18:
        return datetime.combine(current_ts.date(), time(hour=18, minute=0))
    
    # Normal: dakika ekle
    return current_ts + timedelta(minutes=MINUTES_PER_STEP)
```

**Not:** app321 ve app48'de haftasonu yönetimi yok (direkt dakika ekleme).

---

## 🌐 Web Server Routes

### Route Tablosu

| App | Routes | Açıklama |
|-----|--------|----------|
| **app321** | `/` (GET/POST) | Counter analizi |
| | `/dc` (GET/POST) | DC List |
| | `/matrix` (GET/POST) | Matrix (tüm offsetler) |
| | `/iou` (GET/POST) | IOU analizi (çoklu dosya) |
| **app48** | `/` (GET/POST) | Counter analizi |
| | `/dc` (GET/POST) | DC List |
| | `/matrix` (GET/POST) | Matrix |
| | `/convert` (GET/POST) | 12m→48m Converter |
| | `/iou` (GET/POST) | IOU analizi (çoklu dosya) |
| **app72** | `/` (GET/POST) | Counter analizi |
| | `/dc` (GET/POST) | DC List |
| | `/matrix` (GET/POST) | Matrix |
| | `/converter` (GET/POST) | 12m→72m Converter |
| | `/iou` (GET/POST) | IOU analizi (çoklu dosya) |
| **app80** | `/` (GET/POST) | Counter analizi |
| | `/dc` (GET/POST) | DC List |
| | `/matrix` (GET/POST) | Matrix |
| | `/converter` (GET/POST) | 20m→80m Converter |
| | `/iou` (GET/POST) | IOU analizi (çoklu dosya) |
| **app120** | `/` (GET/POST) | Counter analizi |
| | `/dc` (GET/POST) | DC List |
| | `/matrix` (GET/POST) | Matrix |
| | `/iov` (GET/POST) | IOV analizi (çoklu dosya) |
| | `/iou` (GET/POST) | IOU analizi (çoklu dosya) |
| | `/converter` (GET/POST) | 60m→120m Converter |

### HTTP Handler Pattern

```python
from http.server import BaseHTTPRequestHandler, HTTPServer

class AppXXHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            # Render index
        elif self.path == "/dc":
            # Render DC page
        elif self.path.startswith("/favicon/"):
            # Serve favicon
        else:
            # 404
    
    def do_POST(self):
        if self.path == "/analyze":
            # Process counter analysis
        elif self.path == "/iou":
            # Process IOU analysis (multiple files)
```

---

## 🔍 IOU (Inverse OC - Uniform sign) Analizi

### IOU Tanımı

**IOU:** OC ve PrevOC değerleri limit üstünde ve **aynı işaretli** mumlar.

### IOU Kriterleri (5 Şart)

```python
# 1. |OC| >= limit
if abs(oc) < limit:
    continue  # IOU değil

# 2. |PrevOC| >= limit
if abs(prev_oc) < limit:
    continue  # IOU değil

# 3. Tolerance kontrolü (güvenlik payı)
# OC'nin limit'e olan uzaklığı tolerance'tan büyük olmalı
if abs(abs(oc) - limit) < tolerance:
    continue  # Limit'e çok yakın, güvenilmez

# 4. PrevOC için aynı kontrol
if abs(abs(prev_oc) - limit) < tolerance:
    continue  # Limit'e çok yakın, güvenilmez

# 5. Aynı işaret kontrolü (++ veya --)
if not ((oc > 0 and prev_oc > 0) or (oc < 0 and prev_oc < 0)):
    continue  # Zıt işaret → IOU değil
```

### Tolerance (Güvenlik Payı)

**Varsayılan:** `0.005`

**Amaç:** Limit değerine çok yakın olan OC/PrevOC değerlerini elemek.

**Örnek (Limit=0.1, Tolerance=0.005):**

```python
# OC = 0.006 → Kontrol 1: 0.006 < 0.1 → ELEME (limit altı)
# OC = 0.098 → Kontrol 1: 0.098 < 0.1 → ELEME (limit altı)
# OC = 0.103 → Kontrol 2: |0.103-0.1| = 0.003 < 0.005 → ELEME (çok yakın)
# OC = 0.106 → Her iki kontrol geçiyor → IOU! ✅
```

### XYZ Küme Analizi

**Amaç:** Habersiz IOU içeren offsetleri elemek.

**Mantık:**

```python
# 1. Her offset için IOU'ları tara
for offset in range(-3, 4):
    for iou in results[offset]:
        # Haber bulma (timeframe süresince)
        news_events = find_news_in_timerange(
            events_by_date,
            iou.timestamp,
            duration_minutes  # 48, 72, 80, 120, 321 (app'e göre)
        )
        
        # Sadece non-holiday eventler sayılır
        non_holiday_events = [e for e in news_events if not is_holiday_event(e)]
        has_news = bool(non_holiday_events)
        
        # XYZ tracking
        if has_news:
            file_xyz_data[offset]["with_news"] += 1
        else:
            file_xyz_data[offset]["news_free"] += 1

# 2. XYZ kümesi oluştur
xyz_set = []
eliminated = []
for offset in range(-3, 4):
    if file_xyz_data[offset]["news_free"] > 0:
        eliminated.append(offset)  # En az 1 habersiz IOU var → ELEME
    else:
        xyz_set.append(offset)  # Habersiz IOU yok → XYZ'de
```

**Örnek:**
```
Offset -3: 2 IOU (2 haberli, 0 habersiz) → XYZ'de ✅
Offset -2: 1 IOU (0 haberli, 1 habersiz) → Elendi ❌
Offset -1: 0 IOU → XYZ'de ✅
Offset  0: 3 IOU (3 haberli, 0 habersiz) → XYZ'de ✅
Offset +1: 1 IOU (1 haberli, 0 habersiz) → XYZ'de ✅
Offset +2: 2 IOU (1 haberli, 1 habersiz) → Elendi ❌
Offset +3: 0 IOU → XYZ'de ✅

XYZ Kümesi: {-3, -1, 0, +1, +3}
Elenen: {-2, +2}
```

### Haber Verisi (news_data/*.json)

**Format:**
```json
{
  "meta": {
    "time_zone": "UTC-4",
    "counts": {"days": 35, "events": 156}
  },
  "days": [
    {
      "date": "2025-06-01",
      "events": [
        {
          "currency": "USD",
          "title": "Non-Farm Payrolls",
          "time_24h": "14:30",
          "impact": "high",
          "values": {
            "actual": 200,
            "forecast": 180,
            "previous": 190
          }
        }
      ]
    }
  ]
}
```

**Haber Arama Kuralları:**

```python
def find_news_in_timerange(
    events_by_date: Dict,
    start_ts: datetime,
    duration_minutes: int
) -> List[Dict]:
    """
    Regular events: [start_ts, start_ts + duration) aralığında
    Null events (time_24h=null): [start_ts - 1 hour, start_ts + duration)
    
    NOT: JSON'daki yıl GÖRMEZDEN GELİNİR, mum yılı kullanılır.
    """
```

**Holiday Kontrolü:**

```python
def is_holiday_event(event: Dict) -> bool:
    """
    Holiday events gösterilir ama XYZ eleme'yi ETKİLEMEZ.
    """
    title = event.get('title', '').lower()
    return 'holiday' in title
```

---

## 🔄 Converter'lar

### Özet Tablo

| App | Converter | Input | Output | CLI |
|-----|-----------|-------|--------|-----|
| **app48** | 12m→48m | 12m CSV (UTC-5) | 48m CSV (UTC-4) | ❌ (web only) |
| **app72** | 12m→72m | 12m CSV (UTC-5) | 72m CSV (UTC-4) | ✅ `python -m app72.main` |
| **app80** | 20m→80m | 20m CSV (UTC-5) | 80m CSV (UTC-4) | ✅ `python -m app80.main` |
| **app120** | 60m→120m | 60m CSV (UTC-5) | 120m CSV (UTC-4) | ✅ `python -m app120.main` |

**Not:** app321'de converter yok.

### Genel Converter Mantığı

```python
# 1. CSV yükle
candles = load_candles(input_csv)

# 2. Timezone düzeltmesi (UTC-5 → UTC-4)
if input_tz == "UTC-5":
    candles = [
        Candle(ts=c.ts + timedelta(hours=1), ...)
        for c in candles
    ]

# 3. Timeframe'e göre gruplama (18:00 anchor)
def _align_to_XX_minutes(ts: datetime) -> datetime:
    anchor = datetime.combine(ts.date(), time(hour=18, minute=0))
    if ts < anchor:
        anchor -= timedelta(days=1)
    delta_minutes = int((ts - anchor).total_seconds() // 60)
    block_index = delta_minutes // XX  # 48, 72, 80, 120
    return anchor + timedelta(minutes=block_index * XX)

# 4. Cumartesi ve Pazar 18:00 öncesi atla
if weekday == 5:  # Cumartesi
    continue
if weekday == 6 and ts.hour < 18:  # Pazar 18:00 öncesi
    continue

# 5. OHLC birleştirme
for block_ts, block_candles in groups.items():
    open = block_candles[0].open
    close = block_candles[-1].close
    high = max(c.high for c in block_candles)
    low = min(c.low for c in block_candles)

# 6. Close düzeltmesi (bir sonraki mumun open'ı)
for i in range(len(aggregated) - 1):
    aggregated[i].close = aggregated[i + 1].open
    if next_open >= aggregated[i].high:
        aggregated[i].high = next_open
    if next_open <= aggregated[i].low:
        aggregated[i].low = next_open

# 7. CSV çıktı (trailing zeros temizle)
def format_price(value: float) -> str:
    s = f"{value:.6f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s
```

### app48 Özel: Sentetik Mum Ekleme

```python
def insert_synthetic_48m(candles: List[Candle]) -> List[Candle]:
    """
    Her gün (başlangıç gününden sonraki günler için)
    18:00 ve 18:48 sentetik mumlar ekler.
    
    Bu mumlar hizalama/doğruluk için gereklidir.
    """
    # İlk gün hariç, her gün için 18:00 ve 18:48 kontrolü
    # Yoksa son mumun OHLC'si ile sentetik mum ekle
    # synthetic=True flag eklenir
```

---

## 📝 CSV Format Desteği

### Zorunlu Başlıklar

| Alan | Kabul Edilen İsimler |
|------|---------------------|
| **Time** | `time`, `date`, `datetime`, `timestamp` |
| **Open** | `open`, `o`, `open (first)` |
| **High** | `high`, `h` |
| **Low** | `low`, `l` |
| **Close** | `close`, `last`, `c`, `close (last)`, `close last`, `close(last)` |

**Not:** Başlıklar case-insensitive.

### Tarih-Saat Format Desteği

```python
# ISO format (timezone drop edilir)
"2025-01-10T18:00:00Z"          → 2025-01-10 18:00:00
"2025-01-10T18:00:00+00:00"     → 2025-01-10 18:00:00

# Standart formatlar
"2025-01-10 18:00:00"
"2025-01-10 18:00"
"10.01.2025 18:00:00"
"10.01.2025 18:00"
"01/10/2025 18:00:00"
"01/10/2025 18:00"
```

### Ondalık Ayraç

```python
# Nokta separator (standart)
1.23456 → 1.23456

# Virgül separator (Avrupa formatı)
"1,23456" → Replace "," ile "." → 1.23456
```

### Dialect Detection

```python
# csv.Sniffer kullanır
# Desteklenen: , ; \t
# Bulamazsa default: comma (,)
try:
    dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
except:
    # Fallback dialect
```

### CSV Sıralama

**Önemli:** CSV yüklendikten sonra **timestamp'e göre sıralanır** (ascending).

```python
candles.sort(key=lambda x: x.ts)
```

---

## 🎨 Web Arayüzü Detayları

### HTML Template Pattern

```python
def page(title: str, body: str, active_tab: str = "analyze") -> bytes:
    html = f"""<!doctype html>
    <html>
      <head>
        <meta charset='utf-8'>
        <title>{html.escape(title)}</title>
        <link rel="icon" href="/favicon/favicon.ico">
        <style>
          /* Inline CSS... */
        </style>
      </head>
      <body>
        <header><h2>appXX</h2></header>
        <nav class='tabs'>
          <a href='/' class='{"active" if active_tab=="analyze" else ""}'>Counter</a>
          <a href='/dc' class='{"active" if active_tab=="dc" else ""}'>DC List</a>
          <!-- ... -->
        </nav>
        {body}
      </body>
    </html>"""
    return html.encode("utf-8")
```

### Multipart Form Parsing

```python
from email.parser import BytesParser
from email.policy import default as email_default

def parse_multipart(handler: BaseHTTPRequestHandler) -> Dict:
    ctype = handler.headers.get("Content-Type")
    length = int(handler.headers.get("Content-Length", "0"))
    
    form = BytesParser(policy=email_default).parsebytes(
        b"Content-Type: " + ctype.encode("utf-8") + b"\n\n" +
        handler.rfile.read(length)
    )
    
    out = {}
    for part in form.iter_parts():
        name = part.get_param("name", header="content-disposition")
        filename = part.get_filename()
        
        if filename:
            out[name] = {"filename": filename, "data": part.get_payload(decode=True)}
        else:
            out[name] = {"value": part.get_payload(decode=True).decode("utf-8")}
    
    return out
```

### Çoklu Dosya Desteği (IOU)

```python
def _parse_multipart_multiple_files(self) -> Dict[str, Any]:
    """
    IOU için 25 dosyaya kadar yükleme desteği.
    
    Returns:
        {
            "files": [{"filename": str, "data": bytes}, ...],
            "params": {"sequence": str, "limit": str, ...}
        }
    """
```

### Favicon Servisi

```python
# Tüm uygulamalarda /favicon/ path'i desteklenir
if self.path.startswith("/favicon/"):
    filename = self.path.split("/")[-1].split("?")[0]
    favicon_path = os.path.join(os.path.dirname(__file__), "..", "favicon", filename)
    # Serve favicon.ico, favicon-16x16.png, favicon-32x32.png
```

---

## ⚙️ CLI Kullanımı

### app321 (main.py)

```bash
python -m app321.main \
    --csv data.csv \
    --sequence S1 \
    --offset 0 \
    --show-dc
```

### app48 (main.py)

```bash
python -m app48.main \
    --csv data.csv \
    --sequence S2 \
    --offset +1 \
    --predict 37  # Belirli seq değerinin tahmini
```

### app72 (counter.py + converter)

```bash
# Counter
python -m app72.counter \
    --csv data.csv \
    --sequence S1 \
    --offset 0

# Converter
python -m app72.main \
    --csv input12m.csv \
    --input-tz UTC-5 \
    --output output72m.csv
```

### app80

```bash
# Counter
python -m app80.counter \
    --csv data.csv \
    --sequence S2 \
    --offset +2

# Converter
python -m app80.main \
    --csv input20m.csv \
    --input-tz UTC-5 \
    --output output80m.csv
```

### app120

```bash
# Counter
python -m app120.counter \
    --csv data.csv \
    --sequence S1 \
    --offset 0 \
    --predict-next

# Converter
python -m app120.main \
    --csv input60m.csv \
    --input-tz UTC-5 \
    --output output120m.csv
```

---

## 🚀 Web Başlatma

```bash
# app321
python -m app321.web --host 127.0.0.1 --port 2160

# app48
python -m app48.web --host 127.0.0.1 --port 2148

# app72
python -m app72.web --host 127.0.0.1 --port 2172

# app80
python -m app80.web --host 127.0.0.1 --port 2180

# app120
python -m app120.web --host 127.0.0.1 --port 2120

# landing
python -m landing.web --host 127.0.0.1 --port 8000
```

---

## 📌 Kritik İmplementasyon Notları

### 1. DC Kontrolü Zamanlaması

DC kontrolleri **app-specific** istisnalardan **önce** yapılmalıdır:

```python
# ❌ YANLIŞ
if is_dc_candle(idx):
    # Burada app-specific kontrol yapılırsa çok geç

# ✅ DOĞRU
def compute_dc_flags(candles):
    for i in range(1, len(candles)):
        # 1. Temel DC kriterleri
        cond = cur.high <= prev.high and cur.low >= prev.low and within
        
        # 2. App-specific istisnalar
        if cur.ts.hour == 18 and cur.ts.minute == 0:
            cond = False
        # ...
        
        # 3. Ardışık DC yasağı
        if prev_flag and cond:
            cond = False
```

### 2. Offset ve Missing Steps

```python
# Hedef mum bulunamadığında DOĞRU sıra:
# 1. İlk >= target_ts mumu bul
# 2. delta_minutes hesapla
# 3. missing_steps = delta_minutes // MINUTES_PER_STEP
# 4. seq_compute = [missing_steps+1, ...] ile başlat
```

### 3. IOU Tolerance

```python
# Tolerance kontrolü HEM limit kontrolünden SONRA yapılmalıdır:

# ✅ DOĞRU SIRA:
# 1. |OC| >= limit kontrolü
if abs(oc) < limit:
    continue

# 2. Tolerance kontrolü
if abs(abs(oc) - limit) < tolerance:
    continue
```

### 4. XYZ Holiday Kuralı

```python
# Holiday events:
# - Gösterilir ✅
# - XYZ eleme'yi ETKİLEMEZ ✅

non_holiday_events = [e for e in news_events if not is_holiday_event(e)]
has_news = bool(non_holiday_events)  # Sadece bunlar sayılır
```

### 5. Haftasonu Prediction

```python
# app72, app80, app120: predict_time_after_n_steps kullan
# app321, app48: Direkt dakika ekleme (haftasonu yok)

# Cuma 16:00 → Pazar 18:00 sıçrama kontrolü GEREKLİ
```

---

## 🐛 Bilinen Limitasyonlar

1. **Timezone:** Tüm zamanlar `timezone-naive` (UTC-4 kabul edilir)
2. **Holiday data:** `news_data/*.json` manuel olarak güncellenmeli
3. **CSV size:** Çok büyük CSV'ler (>10MB) yavaş işlenebilir
4. **Multipart limit:** Çoklu dosya yüklemede 25 dosya limiti var
5. **Session state:** Web arayüzü stateless (her request bağımsız)

---

## 📚 Referans: Fonksiyon İmzaları

### Core Functions

```python
# CSV Processing
load_candles(path: str) -> List[Candle]
parse_float(val: str) -> Optional[float]
parse_time_value(val: str) -> Optional[datetime]
normalize_key(name: str) -> str

# DC Processing
compute_dc_flags(candles: List[Candle]) -> List[Optional[bool]]

# Sequence Processing
find_start_index(candles: List[Candle], start_tod: time) -> Tuple[int, str]
compute_sequence_allocations(
    candles: List[Candle],
    dc_flags: List[Optional[bool]],
    start_idx: int,
    seq_values: List[int]
) -> List[SequenceAllocation]

# Offset Processing
determine_offset_start(
    candles: List[Candle],
    base_idx: int,
    offset: int,
    minutes_per_step: int,
    dc_flags: Optional[List[Optional[bool]]]
) -> Tuple[Optional[int], Optional[datetime], str]

# Prediction
predict_next_candle_time(current_ts: datetime, minutes_per_step: int) -> datetime
predict_time_after_n_steps(base_ts: datetime, n_steps: int, minutes_per_step: int) -> datetime

# IOU Analysis
analyze_iou(
    candles: List[Candle],
    sequence: str,
    limit: float,
    tolerance: float = 0.005
) -> Dict[int, List[IOUResult]]

# News Processing
load_news_data_from_directory(directory_path: str) -> Dict[str, List[Dict]]
find_news_in_timerange(
    events_by_date: Dict,
    start_ts: datetime,
    duration_minutes: int
) -> List[Dict]
is_holiday_event(event: Dict) -> bool
format_news_events(events: List[Dict]) -> str

# Converter
adjust_to_output_tz(candles: List[Candle], input_tz: str) -> Tuple[List[Candle], str]
convert_12m_to_48m(candles: List[Candle]) -> List[Candle]
convert_12m_to_72m(candles: List[Candle]) -> List[Candle]
convert_20m_to_80m(candles: List[Candle]) -> List[Candle]
convert_60m_to_120m(candles: List[Candle]) -> List[Candle]

# Web
page(title: str, body: str, active_tab: str) -> bytes
parse_multipart(handler: BaseHTTPRequestHandler) -> Dict
```

---

## 🎓 Örnek Kullanım Senaryoları

### Senaryo 1: DC Analizi

```python
# 1. Veri yükle
candles = load_candles("data.csv")

# 2. DC hesapla (app72 için)
dc_flags = compute_dc_flags(candles)

# 3. DC mumları filtrele
dc_candles = [
    candles[i] for i, flag in enumerate(dc_flags) if flag
]

# 4. İstatistik
print(f"Toplam mum: {len(candles)}")
print(f"DC mum: {len(dc_candles)}")
print(f"DC oranı: {len(dc_candles)/len(candles)*100:.2f}%")
```

### Senaryo 2: IOU Analizi

```python
# 1. Veri yükle
candles = load_candles("data.csv")

# 2. IOU analiz (S1, limit=0.1, tolerance=0.005)
results = analyze_iou(candles, "S1", 0.1, 0.005)

# 3. Sonuçları görüntüle
for offset in range(-3, 4):
    iou_list = results[offset]
    print(f"Offset {offset:+d}: {len(iou_list)} IOU")
    for iou in iou_list:
        print(f"  Seq={iou.seq_value}, Idx={iou.index}, "
              f"OC={iou.oc:+.5f}, PrevOC={iou.prev_oc:+.5f}")
```

### Senaryo 3: XYZ Analizi

```python
# 1. Haber verisi yükle
events_by_date = load_news_data_from_directory("news_data/")

# 2. IOU analiz
results = analyze_iou(candles, "S1", 0.1, 0.005)

# 3. Her offset için haber kontrolü
xyz_data = {offset: {"news_free": 0, "with_news": 0} for offset in range(-3, 4)}

for offset, iou_list in results.items():
    for iou in iou_list:
        news_events = find_news_in_timerange(
            events_by_date,
            iou.timestamp,
            72  # app72 için
        )
        non_holiday = [e for e in news_events if not is_holiday_event(e)]
        
        if non_holiday:
            xyz_data[offset]["with_news"] += 1
        else:
            xyz_data[offset]["news_free"] += 1

# 4. XYZ kümesi oluştur
xyz_set = [o for o in range(-3, 4) if xyz_data[o]["news_free"] == 0]
print(f"XYZ Kümesi: {xyz_set}")
```

---

## 📖 Son Notlar

Bu dokümantasyon **gerçek kod implementasyonuna** dayanır ve varsayım içermez. Her app için DC kuralları, offset mantığı, IOU kriterleri kod içinde doğrulandı.

**Önemli:** Her app'ın kendine özgü DC istisnaları ve timeframe'i var. Bir app için geçerli olan kural başka bir app için geçerli olmayabilir.

**Güncelleme:** Kod değişikliklerinde bu dokümantasyon da güncellenmelidir.

**İletişim:** Hata veya eksik bulunursa lütfen bildirin.

---

**agents.md - v2.0 - 2025-01-18**
