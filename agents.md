# 📘 Proje Teknik Dokümantasyonu (AI Context-Ready)

**Son Güncelleme:** 2025-10-15  
**Amaç:** Bu dokümantasyon bir AI agent'ın projeyi tamamen anlaması için hazırlanmıştır.

Bu doküman app321, app48, app72, app80, app120, app120_iov ve app120_iou uygulamalarının **tüm implementation detaylarını**, kod yapısını, fonksiyon isimlerini, dosya organizasyonunu ve özelliklerini en ince detayına kadar açıklar. Tüm açıklamalar Türkçe'dir ve en güncel davranışları yansıtır.

## 🎯 Proje Özeti

Python-based forex/kripto mum analiz uygulaması. **7 ana uygulama**, her biri HTTP server, CSV işleme ve web arayüzü içerir.

**Port Mapping:**
- app321 → 2160 (60m)
- app48 → 2148 (48m)  
- app72 → 2172 (72m)
- app80 → 2180 (80m)
- app120 → 2120 (120m, merkezi)
- app120_iov → 2121 (IOV analizi)
- app120_iou → 2122 (IOU analizi)

**Teknoloji Stack:**
- Python 3.x
- BaseHTTPRequestHandler (http.server)
- CSV işleme (csv module)
- Email parser (multipart form-data için)
- Dataclasses
- No external dependencies (pure Python)

## 📂 Dosya Yapısı ve Kod Organizasyonu

```
x/
├── app120/                    # Merkezi 120m uygulama
│   ├── __init__.py
│   ├── counter.py            # Sayım mantığı, DC hesaplama, sequence allocation
│   │                         # Classes: Candle, SequenceAllocation
│   │                         # Functions: find_start_index(), compute_dc_flags(), 
│   │                         #            compute_sequence_allocations(), analyze_count()
│   ├── web.py                # Web server (6 sekme: Counter, DC, Matrix, IOV, IOU, Converter)
│   │                         # Classes: App120Handler(BaseHTTPRequestHandler)
│   │                         # Functions: parse_multipart(), parse_multipart_with_multiple_files(),
│   │                         #            load_candles_from_text(), page(), render_*_index()
│   └── main.py               # 60→120 converter CLI
│
├── app120_iov/               # IOV analiz uygulaması
│   ├── __init__.py
│   ├── counter.py            # IOV analiz mantığı
│   │                         # Classes: Candle, IOVResult
│   │                         # Constants: SEQUENCES_FULL, SEQUENCES_FILTERED
│   │                         # Functions: analyze_iov(), find_start_index(),
│   │                         #            determine_offset_start(), compute_sequence_allocations()
│   ├── web.py                # IOV web arayüzü (standalone, port 2121)
│   └── README.md
│
├── app120_iou/               # IOU analiz uygulaması
│   ├── __init__.py
│   ├── counter.py            # IOU analiz mantığı (IOV'den farklı: aynı işaret)
│   │                         # Classes: Candle, IOUResult
│   │                         # Functions: analyze_iou(), ...
│   └── web.py                # IOU web arayüzü (standalone, port 2122)
│
├── app321/                   # 60m uygulama
│   ├── counter.py            # 60m sayım mantığı
│   └── web.py                # Web server (3 sekme: Counter, DC, Matrix)
│
├── app48/                    # 48m uygulama
│   ├── counter.py
│   ├── web.py                # Web server (4 sekme: Counter, 12-48, DC, Matrix)
│   └── main.py               # 12→48 converter CLI
│
├── app72/                    # 72m uygulama
│   ├── counter.py
│   ├── web.py                # Web server (4 sekme: Counter, DC, Matrix, 12→72)
│   └── main.py               # 12→72 converter CLI
│
├── app80/                    # 80m uygulama
│   ├── counter.py
│   ├── web.py                # Web server (4 sekme: Counter, DC, Matrix, 20→80)
│   └── main.py               # 20→80 converter CLI
│
├── landing/                  # Ana giriş sayfası
│   └── web.py                # Landing page, tüm uygulamalara linkler
│
├── appsuite/                 # Tüm appları tek sayfada toplayan reverse proxy
│   └── web.py                # Proxy server, backend'leri başlatır
│
├── agents.md                 # Bu dokümantasyon
├── x222.csv                  # Örnek 120m test verisi (2 haftalık)
└── README.md
```

## 📊 Veri Yapıları (Data Structures)

### Candle (Mum) Dataclass
**Tüm uygulamalarda kullanılır**

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

### SequenceAllocation Dataclass
**Dosya:** `app120/counter.py`, tüm counter.py dosyaları

```python
@dataclass
class SequenceAllocation:
    seq_value: int          # Sequence değeri (örn: 7, 13, 21)
    idx: Optional[int]      # Candle index (None = predicted/missing)
    ts: Optional[datetime]  # Timestamp (None = predicted)
    is_pred: bool           # True = tahmin edilen (missing)
```

### IOVResult Dataclass
**Dosya:** `app120_iov/counter.py`

```python
@dataclass
class IOVResult:
    seq_value: int          # Sequence değeri
    offset: int             # Offset (-3 to +3)
    index: int              # Candle index
    timestamp: datetime     # Candle timestamp
    oc: float               # OC (open-close) değeri
    prev_oc: float          # Önceki mumun OC değeri
    prev_index: int         # Önceki mum index
    prev_timestamp: datetime # Önceki mum timestamp
```

### IOUResult Dataclass
**Dosya:** `app120_iou/counter.py`

```python
@dataclass
class IOUResult:
    seq_value: int          # Sequence değeri
    offset: int             # Offset (-3 to +3)  
    index: int              # Candle index
    timestamp: datetime     # Candle timestamp
    oc: float               # OC (open-close) değeri
    prev_oc: float          # Önceki mumun OC değeri
    prev_index: int         # Önceki mum index
    prev_timestamp: datetime # Önceki mum timestamp
```

**Not:** IOVResult ve IOUResult yapısal olarak aynıdır, sadece mantık farklıdır (zıt işaret vs aynı işaret).

### News Event JSON Schema
**Dosya:** `news_data/*.json`

```json
{
  "meta": {
    "source": "markdown_import",
    "assumptions": {
      "year": 2025,
      "time_zone": "UTC-4",
      "value_columns_order": ["actual", "forecast", "previous"],
      "two_value_rule": "When only two values are present, interpret as (actual, previous)."
    },
    "counts": {
      "days": 35,
      "events": 156
    }
  },
  "days": [
    {
      "date": "2025-06-01",
      "weekday": "Sun",
      "events": [
        {
          "date": "2025-06-01",
          "weekday": "Sun",
          "currency": "USD",
          "title": "Non-Farm Payrolls",
          "time_label": "14:30",
          "time_24h": "14:30",
          "impact": "high",
          "actual": 200,
          "forecast": 180,
          "previous": 190
        },
        {
          "title": "Bank Holiday",
          "time_label": "All Day",
          "time_24h": null,
          "impact": "holiday"
        }
      ]
    }
  ]
}
```

**Kritik Alanlar:**
- `time_24h`: `null` ise "All Day" event (speeches, statements)
- `impact`: "high", "medium", "low", "holiday"
- `actual`, `forecast`, `previous`: `null` olabilir
- Timezone: **UTC-4** (mum verileriyle aynı)

---

## 🔑 Kritik Fonksiyonlar ve Kod Parçaları

### `parse_multipart_with_multiple_files()` - Çoklu Dosya Parser
**Dosya:** `app120/web.py` (satır 391-429)

```python
from email.parser import BytesParser
from email.policy import default as email_default

def parse_multipart_with_multiple_files(handler: BaseHTTPRequestHandler) -> Dict[str, Any]:
    """
    Multipart form-data'yı parse eder, çoklu dosya desteği ile.
    
    Args:
        handler: HTTP request handler instance
        
    Returns:
        {
            "files": List[Dict{"filename": str, "data": bytes}],
            "params": Dict[str, str] (sequence, limit, vb.)
        }
    """
    ctype = handler.headers.get("Content-Type")
    length = int(handler.headers.get("Content-Length", "0") or "0")
    
    # BytesParser ile multipart parse
    form = BytesParser(policy=email_default).parsebytes(
        b"Content-Type: " + ctype.encode("utf-8") + b"\n\n" + handler.rfile.read(length)
    )
    
    files: List[Dict[str, Any]] = []
    params: Dict[str, str] = {}
    
    for part in form.iter_parts():
        if part.get_content_disposition() != "form-data":
            continue
        
        name = part.get_param("name", header="content-disposition")
        filename = part.get_filename()
        
        if filename:
            # File part
            data = part.get_payload(decode=True) or part.get_content().encode("utf-8")
            files.append({"filename": filename, "data": data or b""})
        else:
            # Form field part
            value = part.get_payload(decode=True).decode("utf-8")
            params[name] = value
    
    return {"files": files, "params": params}
```

### Helper Functions (Yardımcı Fonksiyonlar)

#### `format_pip()` - OC Değeri Formatlama
**Tüm web.py dosyalarında**

```python
def format_pip(delta: Optional[float]) -> str:
    """
    OC (open-close) değerini formatlar.
    
    Args:
        delta: OC değeri (None olabilir)
    
    Returns:
        "+0.15200" formatında string veya "-" (None için)
    """
    if delta is None:
        return "-"
    return f"{delta:+.5f}"  # +/- işareti dahil, 5 decimal
```

#### `is_holiday_event()` - Holiday Kontrolü
**Tüm web.py dosyalarında**

```python
def is_holiday_event(event: Dict[str, Any]) -> bool:
    """
    Bir event'in holiday olup olmadığını kontrol eder.
    
    XYZ Analysis için: Holidays gösterilir ama offset eleme'yi ETKİLEMEZ.
    
    Args:
        event: News event dict
    
    Returns:
        True if title contains 'holiday' (case-insensitive)
    """
    title = event.get('title', '').lower()
    return 'holiday' in title
```

#### `find_news_in_timerange()` - Haber Arama
**Tüm web.py dosyalarında**

```python
def find_news_in_timerange(
    events_by_date: Dict[str, List[Dict[str, Any]]],
    start_ts: datetime,
    duration_minutes: int = 120  # App'e göre değişir (48, 72, 80, 120)
) -> List[Dict[str, Any]]:
    """
    Belirli bir zaman aralığındaki haberleri bulur.
    
    Özel Kural: Null-valued events (speeches, statements) için
    mum başlangıcından 1 SAAT ÖNCE kontrol edilir.
    
    Args:
        events_by_date: {date_str: [event, ...]}
        start_ts: Mum başlangıç zamanı (UTC-4)
        duration_minutes: Mum süresi (48/72/80/120)
    
    Returns:
        Matching events listesi
        
    Mantık:
        1. Regular events: [start_ts, start_ts + duration) aralığında
        2. Null events (time_24h=null): [start_ts - 1 hour, start_ts + duration)
        3. JSON'daki yıl GÖRMEZDEN GELİNİR, mum yılı kullanılır
    """
    end_ts = start_ts + timedelta(minutes=duration_minutes)
    extended_start_ts = start_ts - timedelta(hours=1)  # Null events için
    
    # Mum tarihini kullan (JSON yılını ignore et)
    candle_date_str = start_ts.strftime("%Y-%m-%d")
    
    # ... (event matching logic)
```

#### `format_news_events()` - Haber Formatla
**Tüm web.py dosyalarında**

```python
def format_news_events(events: List[Dict[str, Any]]) -> str:
    """
    Haber listesini HTML tablo gösterimi için formatlar.
    
    Format: "var: CURRENCY Title (actual:X, forecast:Y, prev:Z); ..."
    
    All Day events: "[ALL DAY] CURRENCY Title" formatında
    
    Args:
        events: News events listesi
    
    Returns:
        Formatted string (HTML escape gerekmez, sonradan yapılır)
    """
    if not events:
        return "-"
    
    parts = []
    for event in events:
        currency = event.get('currency', '')
        title = event.get('title', '')
        
        is_all_day = event.get('time_24h') is None
        
        if is_all_day:
            prefix = "[ALL DAY] "
        else:
            prefix = "var: "
        
        # actual, forecast, previous değerleri varsa ekle
        # ...
    
    return "; ".join(parts)
```

---

### `analyze_iov()` - IOV Analiz Mantığı
**Dosya:** `app120_iov/counter.py` (satır 282-391)

```python
def analyze_iov(
    candles: List[Candle],
    sequence: str,
    limit: float,
) -> Dict[int, List[IOVResult]]:
    """
    Tüm offsetler için IOV mumlarını tespit eder.
    
    Args:
        candles: List[Candle] - 120m mum listesi (2 haftalık, ~120 mum)
        sequence: "S1" veya "S2"
        limit: IOV limit değeri (örn: 0.1)
        
    Returns:
        Dict[offset, List[IOVResult]]
        offset: -3 to +3 (7 tane)
        
    IOV Kriterleri:
        1. |OC| ≥ limit
        2. |PrevOC| ≥ limit  
        3. OC ve PrevOC zıt işaretli (+ ve - veya - ve +)
    """
    results: Dict[int, List[IOVResult]] = {}
    
    # Base mumunu bul (18:00)
    start_tod = DEFAULT_START_TOD  # time(hour=18, minute=0)
    base_idx, _ = find_start_index(candles, start_tod)
    
    # DC flags hesapla
    dc_flags = compute_dc_flags(candles)
    
    # Sequence değerleri
    seq_values_full = SEQUENCES_FULL[sequence]      # Allocation için
    seq_values_filtered = SEQUENCES_FILTERED[sequence]  # IOV check için
    
    # Her offset için analiz
    for offset in range(-3, 4):
        iov_list: List[IOVResult] = []
        
        # Offset başlangıç noktasını bul
        start_idx, target_ts, _ = determine_offset_start(candles, base_idx, offset)
        
        # Missing steps hesapla (offset mumu yoksa)
        missing_steps = 0
        if start_idx is None:
            # Hedef mumdan sonraki ilk mumu bul
            for i, candle in enumerate(candles):
                if candle.ts >= target_ts:
                    start_idx = i
                    delta_minutes = int((candle.ts - target_ts).total_seconds() // 60)
                    missing_steps = max(0, delta_minutes // MINUTES_PER_STEP)
                    break
        
        # Synthetic sequence oluştur
        actual_start_count = missing_steps + 1
        seq_compute = [actual_start_count]
        for v in seq_values_full:
            if v > missing_steps and v != actual_start_count:
                seq_compute.append(v)
        
        # Sequence allocation
        allocations = compute_sequence_allocations(candles, dc_flags, start_idx, seq_compute)
        
        # Mapping: seq_value → allocation
        seq_map = {}
        for idx, val in enumerate(seq_compute):
            seq_map[val] = allocations[idx]
        
        # Filtered sequence üzerinde IOV kontrolü
        for seq_val in seq_values_filtered:
            alloc = seq_map.get(seq_val)
            if not alloc or alloc.idx is None:
                continue
            
            idx = alloc.idx
            if idx <= 0 or idx >= len(candles):
                continue
            
            candle = candles[idx]
            prev_candle = candles[idx - 1]
            
            # OC hesapla
            oc = candle.close - candle.open
            prev_oc = prev_candle.close - prev_candle.open
            
            # IOV kriterleri
            if abs(oc) < limit or abs(prev_oc) < limit:
                continue
            
            # Zıt işaret kontrolü
            if (oc > 0 and prev_oc > 0) or (oc < 0 and prev_oc < 0):
                continue  # Aynı işaret → IOV değil
            
            # IOV bulundu!
            iov_list.append(IOVResult(
                seq_value=seq_val,
                offset=offset,
                index=idx,
                timestamp=candle.ts,
                oc=oc,
                prev_oc=prev_oc,
                prev_index=idx - 1,
                prev_timestamp=prev_candle.ts
            ))
        
        results[offset] = iov_list
    
    return results
```

### IOV vs IOU: Tek Fark
**IOV:** `app120_iov/counter.py` (satır 376-378)
```python
# Zıt işaret kontrolü
if (oc > 0 and prev_oc > 0) or (oc < 0 and prev_oc < 0):
    continue  # Aynı işaretse skip (IOV DEĞİL)
```

**IOU:** `app120_iou/counter.py` (satır ~370)
```python
# Aynı işaret kontrolü
if not ((oc > 0 and prev_oc > 0) or (oc < 0 and prev_oc < 0)):
    continue  # Zıt işaretse skip (IOU DEĞİL)
```

## Temel Kavramlar
- **Sayı dizileri:** Sayım işlemleri belirlenmiş sabit dizilere göre ilerler. Şu an desteklenen diziler:
  - **S1:** `1, 3, 7, 13, 21, 31, 43, 57, 73, 91, 111, 133, 157`
  - **S2:** `1, 5, 9, 17, 25, 37, 49, 65, 81, 101, 121, 145, 169`
- **Mum verisi:** Sayım için giriş olarak CSV dosyaları kullanılır. Her satır bir mumdur.
- **Timeframe:** app321 için 60 dakikalık, app48 için 48 dakikalık, app72 için 72 dakikalık, app80 için 80 dakikalık, app120 için 120 dakikalık mumlar işlenir.
- **Varsayılan başlangıç saati:** Tüm uygulamalar varsayılan olarak 18:00 mumundan saymaya başlar.

## 📄 CSV Formatı ve Parsing Detayları

### Zorunlu Başlıklar (Headers)
**Kabul edilen header isimleri (case-insensitive, eş anlamlılar):**

| Alan | Kabul Edilen İsimler |
|------|---------------------|
| **Time** | `time`, `date`, `datetime`, `timestamp` |
| **Open** | `open` |
| **High** | `high` |
| **Low** | `low` |
| **Close** | `close`, `last` |

### Tarih-Saat Format Desteği
**Otomatik tespit edilen formatlar:**

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

### Ondalık Ayraç (Decimal Separator)
**Otomatik algılama:**

```python
# Nokta separator (standart)
1.23456 → 1.23456

# Virgül separator (Avrupa formatı)
"1,23456"  # Eğer sadece virgül varsa
→ Replace "," ile "."
→ 1.23456
```

### Eksik/Geçersiz Değerler
**Atlanır (skip):**
- Boş string: `""`
- `NaN`, `null`, `None` (case-insensitive)
- Parse edilemeyen değerler

### Örnek CSV
**Geçerli format:**

```csv
Time,Open,High,Low,Close
2025-01-05 18:00:00,1.09450,1.09580,1.09420,1.09520
2025-01-05 20:00:00,1.09520,1.09650,1.09500,1.09610
2025-01-05 22:00:00,1.09610,1.09720,1.09580,1.09680
2025-01-06 00:00:00,1.09680,1.09750,1.09650,1.09720
```

**Alternatif format (virgül separator):**

```csv
Time;Open;High;Low;Last
10.01.2025 18:00;1,09450;1,09580;1,09420;1,09520
10.01.2025 20:00;1,09520;1,09650;1,09500;1,09610
```

### CSV Sıralama
**Önemli:** CSV yüklendikten sonra **timestamp'e göre sıralanır** (ascending).

```python
candles.sort(key=lambda x: x.ts)
```

Bu sayede kullanıcı sırasız CSV yüklese bile doğru çalışır.

### Dialect Detection
**Otomatik delimiter algılama:**

```python
# csv.Sniffer kullanır
# Desteklenen: , ; \t
# Bulamazsa default: comma (,)
```

---

## Distorted Candle (DC) Tanımı
Bir mumun Distorted Candle (DC) sayılması için üç şart bir önceki muma göre aynı anda sağlanmalıdır:
1. `High` değeri bir önceki mumun `High` değerini aşmamalı (eşit olabilir).
2. `Low` değeri bir önceki mumun `Low` değerinin altına düşmemeli (eşit olabilir).
3. `Close (Last)` değeri bir önceki mumun `Open` ve `Close` değerleri aralığında kapanmalıdır.

DC mumları normal sayımda atlanır. Ek olarak global kurallar:
- 18:00 (varsayılan başlangıç mumu) hiçbir koşulda DC sayılmaz.
- Ardışık iki DC oluşamaz; önceki mum DC ise sıradaki mum otomatik olarak normal mum kabul edilir.
- Sayım tablolarında her gerçek mum için iki değer raporlanır:
  - **OC:** İlgili mumun `Close - Open` farkı.
  - **PrevOC:** Bir önceki mumun `Close - Open` farkı (mümkün değilse `-`).
  Tahmini satırlarda OC/PrevOC değerleri `-` olarak gösterilir.

### İstisnai Kapsayıcı Kural
Sayım sırasında diziye ait bir adım bir DC mumuna denk gelirse, o adımın zamanı ilgili DC mumunun saati olarak kaydedilir. Bu eşleme yalnızca DC kuralı nedeniyle atlanması gereken mum tam olarak ilgili dizin adımını tamamlayacağı anda yapılır.

## Offset Mantığı (2025-10-07 Güncellemesi)

### 🔑 Temel Kural: Offset = Non-DC Mum Sayısı

**Offset hesaplama, DC'leri atlayarak yapılır.** Her offset, base mumundan (18:00) itibaren kaç non-DC mum sayılacağını belirtir.

### Offset Değerleri
- Offset aralığı: **-3 ile +3** (`-3, -2, -1, 0, +1, +2, +3`)
- Her offset benzersiz bir non-DC muma denk gelir
- **İki farklı offset asla aynı muma denk gelemez**

### Offset Hesaplama Algoritması

1. **Base Mumu Belirle:** Verideki ilk 18:00 mumu (base_idx=0)

2. **Non-DC Index Oluştur:**
   - Base mumundan başlayarak non-DC mumları say
   - DC mumlar atlanır, sayıma dahil edilmez
   - Her non-DC muma bir index ata (0, 1, 2, 3, ...)

3. **Offset → Non-DC Index Mapping:**
   ```
   Offset -3 → Non-DC Index -3 (base'den 3 mum geriye)
   Offset -2 → Non-DC Index -2 (base'den 2 mum geriye)
   Offset -1 → Non-DC Index -1 (base'den 1 mum geriye)
   Offset  0 → Non-DC Index  0 (base mumu, 18:00)
   Offset +1 → Non-DC Index +1 (base'den 1 non-DC mum ileriye)
   Offset +2 → Non-DC Index +2 (base'den 2 non-DC mum ileriye)
   Offset +3 → Non-DC Index +3 (base'den 3 non-DC mum ileriye)
   ```

4. **Hedef Mumun Belirlenmesi:**
   - Hedef non-DC index'e karşılık gelen gerçek mum bulunur
   - Bu mum, o offset için sequence sayımının **başlangıç noktası**dır

### 📚 Detaylı Örnekler

#### Örnek 1: Sadece 22:00 DC

**Veri:**
```
18:00 (DC değil) - base mumu
20:00 (DC değil)
22:00 (DC ✓)     - Distorted Candle
00:00 (DC değil)
02:00 (DC değil)
04:00 (DC değil)
```

**Non-DC Index Sayımı:**
```
Non-DC Index 0 → 18:00 (Offset 0)
Non-DC Index 1 → 20:00 (Offset +1)
Non-DC Index 2 → 22:00 DC ATLA → 00:00 (Offset +2)
Non-DC Index 3 → 02:00 (Offset +3)
```

**Sonuç:**
- **Offset 0:** 18:00'dan başlar
- **Offset +1:** 20:00'dan başlar
- **Offset +2:** 00:00'dan başlar (22:00 hedeflendi ama DC, atlandı)
- **Offset +3:** 02:00'dan başlar

#### Örnek 2: 20:00 ve 00:00 DC

**Veri:**
```
18:00 (DC değil)
20:00 (DC ✓)
22:00 (DC değil)
00:00 (DC ✓)
02:00 (DC değil)
04:00 (DC değil)
```

**Non-DC Index Sayımı:**
```
Non-DC Index 0 → 18:00 (Offset 0)
Non-DC Index 1 → 20:00 DC ATLA → 22:00 (Offset +1)
Non-DC Index 2 → 00:00 DC ATLA → 02:00 (Offset +2)
Non-DC Index 3 → 04:00 (Offset +3)
```

**Sonuç:**
- **Offset 0:** 18:00
- **Offset +1:** 22:00 (20:00 hedeflendi ama DC)
- **Offset +2:** 02:00 (00:00 hedeflendi ama DC)
- **Offset +3:** 04:00

#### Örnek 3: 22:00 ve 04:00 DC (jun01.csv gerçek verisi)

**Veri:**
```
18:00 (DC değil)
20:00 (DC değil)
22:00 (DC ✓)
00:00 (DC değil)
02:00 (DC değil)
04:00 (DC ✓)
06:00 (DC değil)
```

**Non-DC Index Sayımı:**
```
Non-DC Index 0 → 18:00 (Offset 0)
Non-DC Index 1 → 20:00 (Offset +1)
Non-DC Index 2 → 22:00 DC ATLA → 00:00 (Offset +2)
Non-DC Index 3 → 02:00 (Offset +3)
Non-DC Index 4 → 04:00 DC ATLA → 06:00 (Offset +4)
```

**Sonuç:**
- **Offset 0:** 18:00
- **Offset +1:** 20:00
- **Offset +2:** 00:00 (22:00 DC olduğu için atlandı)
- **Offset +3:** 02:00

### ⚠️ Kritik Notlar

1. **DC Atlanır, Zaman Kayar:** Hedef zaman DC ise, offset bir sonraki non-DC muma otomatik olarak kayar
   
2. **Benzersizlik Garantisi:** Her offset farklı bir non-DC muma denk gelir, iki offset asla aynı mumu işaret edemez

3. **Sayım Başlangıcı:** Offset sadece sequence sayımının **başlangıç noktasını** belirler. Sequence sayımı o noktadan itibaren DC kuralları uygulanarak devam eder

4. **Base Mumu (18:00):** Base mumu (Offset 0) ASLA DC olamaz (tüm uygulamalar için geçerli)

5. **Negatif Offsetler:** Negatif offsetler (-1, -2, -3) base mumundan **geriye doğru** non-DC mum sayar

### Eksik Veri Durumu (Missing Steps)
- Hedef offset mumu veride yoksa (veri eksikliği):
  - Hedef zamandan sonraki ilk mevcut mum bulunur
  - Missing steps hesaplanır (kaç mum eksik)
  - Eksik mumlar `pred` (predicted) olarak gösterilir
  - Sequence sayımı mevcut mumdan başlar

### Önceki Davranıştan Fark

**ESKI (Yanlış) Mantık:**
- Offset hedefi DC ise, o DC mumu "başlangıç mumu için sayılabilir" oluyordu
- Bu durum bazı offsetlerin aynı sequence değerlerinde aynı mumları göstermesine neden oluyordu

**YENİ (Doğru) Mantık:**
- Offset hedefi DC ise, **hiçbir koşulda sayılmaz**, bir sonraki non-DC muma kayar
- Her offset benzersiz bir başlangıç noktasına sahiptir
- DC kuralı evrenseldir: hangi offset olursa olsun DC mumlar atlanır

## Zaman Dilimleri
- Kullanıcı girişinde iki seçenek vardır: `UTC-5` ve `UTC-4`.
- **Giriş UTC-5 ise**, çıktılar UTC-4'e kaydırılır (tüm mumlar +1 saat).
- **Giriş UTC-4 ise** herhangi bir zaman kaydırması yapılmaz.

## DC İstisna Saatleri
- **app321 (60m):** **Pazar hariç** 13:00 ≤ t < 20:00 aralığındaki DC mumları normal mum gibi sayılır (20:00 dahil değil).
- **app48 (48m):** **Pazar hariç** 13:12 ≤ t < 19:36 aralığındaki DC mumları normal mum gibi sayılır (19:36 dahil değil).
- **app72 (72m):** 
  - **18:00 mumu ASLA DC olamaz** (Pazar günü dahil - 2 haftalık veri için 2. hafta başlangıcı)
  - **Cuma 16:48 mumu ASLA DC olamaz** (2 haftalık veri için 1. hafta bitimindeki son mum)
  - **Pazar hariç, 19:12 ve 20:24 mumları DC olamaz** (günlük cycle noktaları)
  - **Hafta kapanış mumu (Cuma 16:00) DC olamaz**
- **app80 (80m):**
  - **Pazar hariç, 18:00, 19:20 ve 20:40 mumları DC olamaz** (günlük cycle noktaları: 18:00, 18:00+80dk, 18:00+160dk)
  - **Hafta kapanış mumu (Cuma 16:40) DC olamaz** (80 dakikalık sistemde son mum)
- **app120 (120m):** DC istisnası yoktur; tüm DC mumlar saatten bağımsız şekilde atlanır (kapsayıcı kural geçerli). Hafta kapanışı sayılan 16:00 mumları (ardından >120 dakikalık boşluk başlayanlar) DC kabul edilmez.

İstisna dışında kalan DC mumları sayımda atlanır ancak kapsayıcı kural gereği ilgili adımın zamanı olarak yazılabilir.

## Uygulama Ayrıntıları

### app321
- Başlangıç noktası: Verideki ilk 18:00 mumu (UTC-4 referansı). Offset seçimi hedef zamanı bu mumdan itibaren kaydırır.
- Sayım adımları seçilen diziye göre ilerler (varsayılan S2).
- Her ofset için gerçek mumlar gösterilir; eksik adımlar `pred` etiketiyle tahmin edilir.
- **DC Listesi:** Yüklenen veri için tespit edilen tüm DC mumları listelenebilir. Saatler giriş verisinin ilgili zaman diliminde gösterilir (UTC-5 girişi gelirse liste UTC-4'e kaydırılır).
- **Tahmin:** Veride bulunmayan adımlar için tahmini saat her zaman ana tabloda gösterilir; ek sekmeye gerek yoktur.
- **Matrix Sekmesi:** Tüm offset değerleri (-3..+3) için aynı tabloda saatler ve tahminler sunulur. DC'den kaynaklanan eşleşmeler tabloda `(DC)` etiketiyle belirtilir.
- **Web Arayüzü (`python3 -m app321.web`, port: 2160):**
  1. **Counter:** 60m sayım, sequence/offset seçimi, OC/PrevOC, DC gösterimi (önceden "Analiz" idi).
  2. **DC List:** Tüm DC mumlarının listesi.
  3. **Matrix:** Tüm offset'ler (-3..+3) için tek ekranda özet tablo.

### app48
- 48 dakikalık mumlar kullanılır ve varsayılan başlangıç yine 18:00'dir.
- İlk sayım gününden sonraki her gün, piyasanın kapalı olduğu 18:00–19:36 aralığı için 18:00 ve 18:48 saatlerine yapay mumlar eklenir. Bu sayede sayım zinciri kesintiye uğramaz.
- DC kuralları ve offset davranışı app321 ile aynıdır; tek fark DC istisna saatlerinin 13:12–19:36 olmasıdır.
- Tahminler ve `pred` etiketi app321 ile aynı şekilde çalışır.
- **DC ve Matrix Listeleri:** app48 için de DC listesi ve matrix görünümü aynı mantıkla sunulur (48 dakikalık adımlar dikkate alınarak).
- **12m → 48m Converter:** app48 arayüzündeki yeni "12-48" sekmesi, UTC-5 12 dakikalık mumları UTC-4 48 dakikalık mumlara dönüştürür. Yüklenen veri önce +1 saat kaydırılır, ardından her gün 18:00'e hizalanan 48 dakikalık bloklar oluşturulur (18:00, 18:48, 19:36 ...). Her bloktaki close değeri bir sonraki bloğun open değerine eşitlenir; eğer bu değer bloktaki high/low sınırlarını aşıyorsa ilgili sınır close ile güncellenir. CSV çıktısında gereksiz sondaki sıfırlar kaldırılır.
- **Web Arayüzü (`python3 -m app48.web`, port: 2148):**
  1. **Counter:** 48m sayım, sequence/offset seçimi, OC/PrevOC, DC gösterimi (önceden "Analiz" idi).
  2. **12-48:** 12m → 48m converter (12 dakikalık mumları 48 dakikalık mumlara dönüştürür).
  3. **DC List:** Tüm DC mumlarının listesi.
  4. **Matrix:** Tüm offset'ler için tek tabloda özet görünüm.

### app72
- 72 dakikalık mumlar kullanılır; 18:00 başlangıç saati standart.
- **Sayım Mantığı:**
  - S1 ve S2 dizileri desteklenir (varsayılan S2).
  - Offset sistemi: -3 ile +3 arası (her adım 72 dakika).
  - **Özel DC Kuralları (2 Haftalık Veri İçin):**
    - **18:00 mumu ASLA DC olamaz** → Pazar günü dahil (ikinci hafta başlangıcı için kritik)
    - **Cuma 16:48 mumu ASLA DC olamaz** → Birinci hafta bitimindeki son mum (16:00 kapanıştan 12 dk önce)
    - **Pazar hariç 19:12 ve 20:24 DC olamaz** → Günlük cycle noktaları (18:00 + 72dk, 18:00 + 144dk)
    - **Cuma 16:00 (hafta kapanış) DC olamaz**
- **12m → 72m Converter (CLI: `python3 -m app72.main`):**
  - 12 dakikalık UTC-5 mumları alır, UTC-4 72 dakikalık mumlara dönüştürür.
  - Her 72 dakikalık mum 7 tane 12 dakikalık mumdan oluşur (7 × 12 = 84 ama offset mantığıyla 72 dakikaya düşer).
  - Hafta sonu boşluğu: Cumartesi mumları atlanır, Pazar 18:00'dan önce mumlar göz ardı edilir.
- **Web Arayüzü (`python3 -m app72.web`, port: 2172):**
  1. **Counter:** 72m sayım, sequence/offset seçimi, OC/PrevOC, DC gösterimi (önceden "Analiz" idi).
  2. **IOU:** IOU (Inverse OC - Uniform sign) analizi - aynı işaretli mumlar
  3. **DC List:** Tüm DC mumlarının listesi (2 haftalık veri kurallarına göre).
  4. **Matrix:** Tüm offset'ler (-3..+3) için tek ekranda özet tablo.
  5. **12→72 Converter:** 12m CSV yükle, 72m CSV indir.
- **IOU Özel XYZ Kuralı (app72):**
  - **16:48, 18:00, 19:12, 20:24 mumları XYZ elemesinden MUAFtır**
  - Bu saatler kritik cycle noktaları ve DC istisna saatleri
  - Bu saatlerdeki IOU'lar **haber varmış gibi işaretlenir** (offset'i elemez)
  - XYZ analizi: Bu saatlerde IOU varsa, haber olmasa bile offset elenmez

### app80
- 80 dakikalık mumlar kullanılır; 18:00 başlangıç saati standart.
- **Sayım Mantığı:**
  - S1 ve S2 dizileri desteklenir (varsayılan S2).
  - Offset sistemi: -3 ile +3 arası (her adım 80 dakika).
  - **DC Kuralları:**
    - **Pazar hariç, 18:00, 19:20 ve 20:40 mumları DC olamaz** → Günlük cycle noktaları (18:00, 18:00+80dk, 18:00+160dk)
    - **Hafta kapanış mumu (Cuma 16:40) DC olamaz** → 80 dakikalık sistemde son mum (14:00 → 15:20 → 16:40)
  - **Prediction Mantığı:**
    - Cuma 16:40'dan sonraki mum → Pazar 18:00 (haftasonu boşluğu)
    - `predict_next_candle_time` fonksiyonu haftasonu gap'i otomatik hesaplar
    - 80 dakikalık sistemde Cuma 16:00 mumu yok, son mum 16:40
- **20m → 80m Converter (CLI: `python3 -m app80.main`):**
  - 20 dakikalık UTC-5 mumları alır, UTC-4 80 dakikalık mumlara dönüştürür.
  - Her 80 dakikalık mum 4 tane 20 dakikalık mumdan oluşur (4 × 20 = 80).
  - Hafta sonu boşluğu: Cumartesi mumları atlanır, Pazar 18:00'dan önce mumlar göz ardı edilir.
  - Dönüştürme sırasında: Open = ilk mumun open, Close = son mumun close, High = max(high), Low = min(low).
- **Web Arayüzü (`python3 -m app80.web`, port: 2180):**
  1. **Counter:** 80m sayım, sequence/offset seçimi, OC/PrevOC, DC gösterimi (önceden "Analiz" idi).
  2. **DC List:** Tüm DC mumlarının listesi.
  3. **Matrix:** Tüm offset'ler (-3..+3) için tek ekranda özet tablo.
  4. **20→80 Converter:** 20m CSV yükle, 80m CSV indir.

### app120
- app321/app48 mantığındaki 120m sayımı, IOV/IOU analizlerini ve 60→120 dönüştürücüyü tek pakette birleşik sunar.
- **Sayım (CLI: `python3 -m app120.counter`):**
  - 120 dakikalık mumları 18:00 başlangıcına göre sayar; DC istisnası yoktur.
  - OC/PrevOC bilgilerini aynı formatta raporlar; tahmin satırları `OC=- PrevOC=-` şeklinde etiketlenir.
  - **Varsayılan sequence:** S1 (önceden S2 idi, değiştirildi)
- **Dönüştürücü (CLI: `python3 -m app120`):** 60m UTC-5 verisini UTC-4 120m mumlarına çevirir; gereksiz trailing sıfırları temizler. Cumartesi mumları ile Pazar 18:00 öncesi mumlar yok sayılır; Cuma 16:00 kapanışından sonra doğrudan Pazar 18:00 açılış mumuna geçilir.
- **Web Arayüzü (`python3 -m app120.web`, port: 2120):** Altı sekme içerir:
  1. **Counter:** 120m sayım, OC/PrevOC, DC bilgileri (önceden "Analiz" idi, "Counter" olarak değiştirildi).
  2. **DC List:** Tüm DC mumlarının listesi (UTC dönüşümü kullanılarak).
  3. **Matrix:** Tüm offset'ler için tek tabloda zaman/OC/PrevOC özetleri.
  4. **IOV:** IOV (Inverse OC Value) mum analizi - zıt işaretli mumlar (app120_iov entegrasyonu).
  5. **IOU:** IOU (Inverse OC - Uniform sign) mum analizi - aynı işaretli mumlar (app120_iou entegrasyonu).
  6. **60→120 Converter:** 60m CSV yükleyip dönüştürülmüş 120m CSV indirme.
- **Not:** IOV ve IOU sekmeleri artık app120 içinde entegre edilmiştir. Standalone app120_iov ve app120_iou uygulamaları hala CLI ve web olarak ayrıca kullanılabilir.

### app120_iov
- **IOV (Inverse OC Value)** mum analizi için özel 120m timeframe uygulaması.
- **Amaç:** 2 haftalık 120m veride, OC ve PrevOC değerlerinin belirli bir limit değerinin üstünde ve zıt işaretli olduğu özel mumları tespit etmek.
- **IOV Mum Tanımı:** Aşağıdaki 3 kriteri **birden** karşılayan mumlardır:
  1. **|OC| ≥ Limit** → Mumun open-close farkı (mutlak değer) limit değerinin üstünde
  2. **|PrevOC| ≥ Limit** → Önceki mumun open-close farkı (mutlak değer) limit değerinin üstünde
  3. **Zıt İşaret** → OC ve PrevOC'den birinin pozitif (+), diğerinin negatif (-) olması
- **Filtrelenmiş Sequence Değerleri:**
  - **S1 için:** `7, 13, 21, 31, 43, 57, 73, 91, 111, 133, 157` (1 ve 3 analiz edilmez)
  - **S2 için:** `9, 17, 25, 37, 49, 65, 81, 101, 121, 145, 169` (1 ve 5 analiz edilmez)
- **Etkisiz Mum:** OC veya PrevOC'den herhangi biri limit değerinin altındaysa, o mum IOV analizi için etkisiz sayılır.
- **Analiz Kapsamı:**
  - Tüm offsetler taranır: -3, -2, -1, 0, +1, +2, +3 (toplam 7 offset)
  - **Sadece IOV mum içeren offsetler gösterilir** (boş offsetler gizlenir, kalabalık yapmaz)
  - Her offset için ayrı IOV mumları listelenir
  - 2 haftalık veri desteği: 1. hafta Pazar 18:00 → 2. hafta Cuma 16:00
- **CLI Kullanımı (`python3 -m app120_iov.counter`):**
  ```bash
  python3 -m app120_iov.counter --csv data.csv --sequence S1 --limit 0.1
  ```
  - `--csv`: 2 haftalık 120m CSV dosyası
  - `--sequence`: S1 veya S2 (varsayılan: **S1** - değiştirildi, önceden S2 idi)
  - `--limit`: IOV limit değeri (varsayılan: 0.1)
- **Web Arayüzü (`python3 -m app120_iov.web`, port: 2121):**
  - **Çoklu dosya yükleme:** En fazla 25 CSV dosyası tek seferde yüklenebilir
  - Sequence seçimi (S1/S2)
  - Limit değeri girişi
  - **Kompakt görünüm:** Her dosya için tek tablo, tüm offsetler tek tabloda
  - Offset bilgisi her satırda gösterilir (Ofs kolonu)
  - Her IOV mum için: Offset, Seq değeri, Index, Timestamp (kısa format), OC, PrevOC, Prev Index
  - IOV bulunamayan dosyalar "IOV yok" olarak gösterilir
- **Örnek Çıktı:**
  ```
  Offset: 0
    Seq=31, Index=34, Time=2025-08-20 14:00:00
      OC: +0.15200, PrevOC: -0.16900
  ```
- **DC Hesaplama:** DC (Distorted Candle) hesaplaması mevcut app120 mantığı ile aynıdır; ancak IOV analizinde sadece sequence allocation için kullanılır, IOV kriterleri sadece OC/PrevOC değerlerine bakar.
- **Offset Handling:** IOV analizi, app120'nin missing_steps ve synthetic sequence mantığını kullanır. Hedef offset mumu eksikse, bir sonraki mevcut mumdan başlanır ve eksik adımlar hesaplanarak sequence allocation yapılır.
- **Entegrasyon:** app120_iov artık app120 web arayüzüne "IOV" sekmesi olarak entegre edilmiştir. Standalone uygulama hala CLI ve web olarak kullanılabilir.
- **Çoklu Dosya Desteği (app120 entegrasyonu):**
  - En fazla 25 dosya tek seferde analiz edilebilir
  - Her dosya bağımsız analiz edilir
  - Bir dosyada hata olsa diğerleri çalışmaya devam eder
  - Kompakt tek tablo görünümü (offset kolonu ile)

### app120_iou
- **IOU (Inverse OC - Uniform sign)** mum analizi için özel 120m timeframe uygulaması.
- **Amaç:** 2 haftalık 120m veride, OC ve PrevOC değerlerinin belirli bir limit değerinin üstünde ve **aynı işaretli** olduğu özel mumları tespit etmek.
- **IOU Mum Tanımı:** Aşağıdaki 5 kriteri **birden** karşılayan mumlardır:
  1. **|OC| ≥ Limit** → Mumun open-close farkı (mutlak değer) limit değerinin üstünde
  2. **|PrevOC| ≥ Limit** → Önceki mumun open-close farkı (mutlak değer) limit değerinin üstünde
  3. **|OC - Limit| ≥ Tolerance** → OC'nin limit'e olan uzaklığı tolerance'tan büyük olmalı (güvenlik payı)
  4. **|PrevOC - Limit| ≥ Tolerance** → PrevOC'nin limit'e olan uzaklığı tolerance'tan büyük olmalı
  5. **Aynı İşaret** → OC ve PrevOC'nin **her ikisi de pozitif (+) VEYA her ikisi de negatif (-)** olması
- **Tolerance (Güvenlik Payı):** Limit değerine çok yakın olan OC/PrevOC değerleri güvenilmez kabul edilir ve elenir
  - **Varsayılan tolerance:** 0.005
  - **Örnek (Limit=0.1, Tolerance=0.005):**
    - OC = 0.103 → |0.103 - 0.1| = 0.003 < 0.005 → **ELEME** (limit'e çok yakın)
    - OC = 0.106 → |0.106 - 0.1| = 0.006 ≥ 0.005 → **GEÇİYOR** ✓
    - OC = 0.098 → 0.098 < 0.1 → **ELEME** (limit altı)
  - Tüm web formlarında tolerance input mevcuttur
- **IOV ile Farkı:** IOV **zıt işaret** (+ ve -) ararken, IOU **aynı işaret** (++ veya --) arar. IOU, IOV'nin tamamlayıcısıdır.
- **Filtrelenmiş Sequence Değerleri:**
  - **S1 için:** `7, 13, 21, 31, 43, 57, 73, 91, 111, 133, 157` (1 ve 3 analiz edilmez)
  - **S2 için:** `9, 17, 25, 37, 49, 65, 81, 101, 121, 145, 169` (1 ve 5 analiz edilmez)
- **Etkisiz Mum:** OC veya PrevOC'den herhangi biri limit değerinin altındaysa, o mum IOU analizi için etkisiz sayılır.
- **Analiz Kapsamı:**
  - Tüm offsetler taranır: -3, -2, -1, 0, +1, +2, +3 (toplam 7 offset)
  - **Sadece IOU mum içeren offsetler gösterilir** (boş offsetler gizlenir)
  - Her offset için ayrı IOU mumları listelenir
  - 2 haftalık veri desteği: 1. hafta Pazar 18:00 → 2. hafta Cuma 16:00
- **CLI Kullanımı (`python3 -m app120_iou.counter`):**
  ```bash
  python3 -m app120_iou.counter --csv data.csv --sequence S1 --limit 0.1 --tolerance 0.005
  ```
  - `--csv`: 2 haftalık 120m CSV dosyası
  - `--sequence`: S1 veya S2 (varsayılan: **S1**)
  - `--limit`: IOU limit değeri (varsayılan: 0.1)
  - `--tolerance`: Güvenlik payı (varsayılan: 0.005)
- **Web Arayüzü (`python3 -m app120_iou.web`, port: 2122):**
  - **Çoklu dosya yükleme:** En fazla 25 CSV dosyası tek seferde yüklenebilir
  - Sequence seçimi (S1/S2)
  - Limit değeri girişi
  - Tolerance (güvenlik payı) girişi (varsayılan: 0.005)
  - **Kompakt görünüm:** Her dosya için tek tablo, tüm offsetler tek tabloda
  - Offset bilgisi her satırda gösterilir (Ofs kolonu)
  - Her IOU mum için: Offset, Seq değeri, Index, Timestamp (kısa format), OC, PrevOC, Prev Index
  - IOU bulunamayan dosyalar "IOU yok" olarak gösterilir
- **Örnek Çıktı:**
  ```
  Offset: -2
    Seq=31, Index=31, Time=2025-08-06 08:00:00
      OC: -0.20700, PrevOC: -0.15200  (aynı işaret: her ikisi negatif)
  
  Offset: +0
    Seq=73, Index=80, Time=2025-08-12 10:00:00
      OC: -0.18400, PrevOC: -0.32200  (aynı işaret: her ikisi negatif)
  ```
- **DC Hesaplama:** DC (Distorted Candle) hesaplaması mevcut app120 mantığı ile aynıdır; ancak IOU analizinde sadece sequence allocation için kullanılır, IOU kriterleri sadece OC/PrevOC değerlerine bakar.
- **Offset Handling:** IOU analizi, app120'nin missing_steps ve synthetic sequence mantığını kullanır (IOV ile aynı).
- **Entegrasyon:** app120_iou artık app120 web arayüzüne "IOU" sekmesi olarak entegre edilmiştir. Standalone uygulama hala CLI ve web olarak kullanılabilir.
- **Çoklu Dosya Desteği (app120 entegrasyonu):**
  - En fazla 25 dosya tek seferde analiz edilebilir
  - Her dosya bağımsız analiz edilir
  - Bir dosyada hata olsa diğerleri çalışmaya devam eder
  - Kompakt tek tablo görünümü (offset kolonu ile)

## Özet
- Giriş CSV’si düzgün formatlanmış olmalı ve zorunlu kolonları içermelidir.
- Varsayılan başlangıç 18:00 mumu olup offset bu zaman üzerinden uygulanır.
- **DC Kuralları Özeti:**
  - **app321:** 13:00–20:00 DC istisna saatleri
  - **app48:** 13:12–19:36 DC istisna saatleri
  - **app72:** 18:00 (Pazar dahil) ve Cuma 16:48 ASLA DC olamaz; Pazar hariç 19:12 ve 20:24 DC olamaz
  - **app80:** Pazar hariç 18:00, 19:20, 20:40 DC olamaz; Cuma 16:40 DC olamaz (hafta kapanışı)
  - **app120:** DC istisnası yok, tüm DC'ler atılır
  - **app120_iov:** DC sadece sequence allocation için kullanılır, IOV kriterleri DC'den bağımsızdır
  - **app120_iou:** DC sadece sequence allocation için kullanılır, IOU kriterleri DC'den bağımsızdır
- 18:00 mumu genelde DC olamaz (app72'de Pazar dahil) ve ardışık iki DC bulunmaz.
- **Web Arayüzü Sekme Adı Değişikliği:** Tüm uygulamalarda (app48, app72, app80, app120, app321) "Analiz" sekmesi "Counter" olarak değiştirilmiştir. Bu değişiklik sayımın (counting) temel işlevi daha iyi yansıtmak için yapılmıştır.
- Her gerçek adım, mumun OC ve PrevOC değerleri ile birlikte raporlanır; tahmini satırlarda değerler `-` olarak gösterilir.
- Eksik veriler tahmini zamanlarla (`pred`) gösterilir.
- Tüm uygulamalar UTC-4/UTC-5 girişlerine uygun şekilde çıktı üretir.
- **Converter Özeti:**
  - **app48:** 12m → 48m (4 × 12m = 48m)
  - **app72:** 12m → 72m (7 × 12m ≈ 72m)
  - **app80:** 20m → 80m (4 × 20m = 80m)
  - **app120:** 60m → 120m (2 × 60m = 120m)
- **IOV Analizi (app120_iov):**
  - Filtrelenmiş sequence değerleri: S1 (1,3 hariç), S2 (1,5 hariç)
  - IOV kriteri: |OC| ≥ limit AND |PrevOC| ≥ limit AND **zıt işaret** (+ ve -)
  - Varsayılan sequence: **S1** (değiştirildi, önceden S2 idi)
  - Tüm offsetler (-3..+3) taranır, **sadece IOV bulunan offsetler gösterilir**
  - 2 haftalık 120m veri desteği
  - app120 web arayüzüne "IOV" sekmesi olarak entegre edildi
  - **Çoklu dosya yükleme:** 25 dosyaya kadar, kompakt tek tablo görünümü
- **IOU Analizi (app120_iou):**
  - Filtrelenmiş sequence değerleri: S1 (1,3 hariç), S2 (1,5 hariç)
  - IOU kriteri: |OC| ≥ limit AND |PrevOC| ≥ limit AND **aynı işaret** (++ veya --)
  - Varsayılan sequence: **S1**
  - Tüm offsetler (-3..+3) taranır, **sadece IOU bulunan offsetler gösterilir**
  - 2 haftalık 120m veri desteği
  - app120 web arayüzüne "IOU" sekmesi olarak entegre edildi
  - **IOV'nin tamamlayıcısıdır:** IOV zıt işaret, IOU aynı işaret
  - **Çoklu dosya yükleme:** 25 dosyaya kadar, kompakt tek tablo görünümü

## 🆕 Son Güncellemeler

### 2025-01-10: 🎯 app72 IOU - Özel Saatler XYZ Elemesinden Muaf
**Dosya:** `app72/web.py`  
**Commit:** `86c60da`

**Değişiklik:** app72 IOU için özel XYZ eleme kuralı eklendi.

**Muaf Saatler:**
- **16:48** - Cuma hafta kapanış mumu
- **18:00** - Base mumu (asla DC olamaz)
- **19:12** - DC istisna saati (cycle noktası)
- **20:24** - DC istisna saati (cycle noktası)

**Kural:**
```python
excluded_times = {time(hour=16, minute=48), time(hour=18, minute=0), 
                 time(hour=19, minute=12), time(hour=20, minute=24)}

# Bu saatler "haber varmış" gibi sayılır
if has_news or is_excluded_time:
    file_xyz_data[offset]["with_news"] += 1
```

**Örnek:**
- Offset +2'de 19:12 saatinde IOU var, haber yok
- **ESKI:** Haber yok → news_free → **Offset +2 ELENİR** ❌
- **YENİ:** 19:12 özel saat → with_news → **Offset +2 XYZ'DE** ✅

**Sebep:** Bu saatler app72'nin kritik cycle noktaları. Yapısal olarak önemli oldukları için habersiz bile olsa offset'i elememelidir.

**Etki:**
- XYZ analizi daha dengeli
- Kritik saatlerdeki IOU'lar korunur
- Offset eleme daha akıllı

---

### 2025-01-10: 🔧 IOU Tolerance (Güvenlik Payı) Eklendi
**Dosyalar:** `app321/main.py`, `app48/main.py`, `app72/counter.py`, `app80/counter.py`, `app120/iou/counter.py`, tüm web.py dosyaları  
**Commit:** `a30296e` (critical fix), `9ef124a` (initial)

**Değişiklik:** IOU analizine tolerance (güvenlik payı) parametresi eklendi.

**Sorun:**
- Limit değerine çok yakın OC/PrevOC değerleri (örn: 0.103, limit=0.1) güvenilmezdi
- Bu mumlar IOU olarak kabul ediliyordu ama hata payı içindeydiler

**Çözüm - 2 Ayrı Kontrol:**
```python
# 1. Temel limit kontrolü
if abs(oc) < limit or abs(prev_oc) < limit:
    continue  # Limit altı, IOU değil

# 2. Tolerance kontrolü (YENİ!)
if abs(abs(oc) - limit) < tolerance or abs(abs(prev_oc) - limit) < tolerance:
    continue  # Limit'e çok yakın, güvenilmez
```

**Örnekler (Limit=0.1, Tolerance=0.005):**
- OC = 0.006 → Kontrol 1: 0.006 < 0.1 → **ELEME** ❌
- OC = 0.098 → Kontrol 1: 0.098 < 0.1 → **ELEME** ❌
- OC = 0.103 → Kontrol 2: |0.103-0.1| = 0.003 < 0.005 → **ELEME** ❌
- OC = 0.106 → Her iki kontrol geçiyor → **IOU!** ✅

**Implementation:**
- Tüm `analyze_iou()` fonksiyonlarına `tolerance` parametresi eklendi (default: 0.005)
- Tüm IOU web formlarına tolerance input eklendi
- CLI'larda `--tolerance` parametresi mevcut

**Critical Bug Fix (commit a30296e):**
- İlk implementasyonda yanlışlıkla temel limit kontrolü kaldırılmıştı
- Sonuç: 4 IOU yerine 41 IOU çıkıyordu
- Düzeltme: Her iki kontrol de artık aktif

**Etki:**
- IOU sonuçları daha güvenilir
- XYZ küme analizi daha kararlı
- Limit'e yakın belirsiz mumlar artık elenmiyor

---

### 2025-10-07: 🔧 DC İstisna Kuralları Düzeltmeleri
**Dosyalar:** `app321/main.py`, `app48/main.py`  
**Commit:** `8ac7950` (range fix), `05be987` (Sunday exclusion)

**Değişiklik 1: Pazar Günü İstisnası**
- app321 ve app48'deki DC istisna kuralları Pazar günü için geçerli değildi
- Pazar günü tüm mumlar artık normal DC kurallarına tabi
- `weekday() != 6` kontrolü eklendi

**Değişiklik 2: Aralık Sonu Düzeltmesi**
- app321: `13:00 <= t <= 20:00` → `13:00 <= t < 20:00` (20:00 hariç)
- app48: `13:12 <= t <= 19:36` → `13:12 <= t < 19:36` (19:36 hariç)
- Aralık sonu mumları artık normal DC kurallarına tabi

**Etki:**
- Pazar 18:48, 19:00, 19:36, 20:00 gibi mumlar artık DC olabilir
- DC istisna kuralları sadece Pazartesi-Cumartesi için geçerli

### 2025-10-07: ⭐ Offset Mantığı Değişikliği (MAJOR UPDATE)
**Dosyalar:** `agents.md` (satır 305-450)  
**Etkilenen Uygulamalar:** Tüm applar (app321, app48, app72, app80, app120, app120_iov, app120_iou)

**Değişiklik:** Offset hesaplama mantığı tamamen değiştirildi.

**ESKI Mantık (Yanlış):**
- Offset hedefi DC ise, o mum "başlangıç için sayılabilir" oluyordu
- Bazı offsetler aynı sequence değerlerinde aynı mumları gösteriyordu
- Tutarsızlıklar oluşuyordu

**YENİ Mantık (Doğru):**
- **Offset = Non-DC mum sayısı**
- Base mumundan (18:00) itibaren non-DC mumlar sayılır
- Hedef mum DC ise, bir sonraki non-DC muma otomatik olarak kayar
- Her offset benzersiz bir başlangıç noktasına sahip
- İki offset asla aynı muma denk gelemez

**Örnek (22:00 DC):**
```
Offset +1 → 20:00 (non-DC index 1)
Offset +2 → 00:00 (22:00 hedeflendi ama DC, atlandı)
Offset +3 → 02:00 (non-DC index 3)
```

**Kritik:** Bu değişiklik tüm uygulamaların offset davranışını etkiler. Kod implementasyonu yapılacak.

### 2025-10-06: Çoklu Dosya & Kompakt Görünüm

### 1. ⭐ Çoklu Dosya Yükleme (Multiple File Upload)
**Dosyalar:** `app120/web.py` (satır 391-429, 502-577, 579-654)  
**Özellik:** IOV ve IOU için **25 dosyaya kadar** çoklu dosya yükleme desteği

**Implementation:**
- Yeni fonksiyon: `parse_multipart_with_multiple_files()`
- HTML `<input type='file' multiple>` attribute
- Her dosya bağımsız analiz, bir dosya hata verse diğerleri çalışır
- File-level error handling (try/except per file)

**Kritik Kod:**
```python
def parse_multipart_with_multiple_files(handler) -> Dict[str, Any]:
    # Returns: {files: List[Dict], params: Dict}
    # BytesParser ile multipart form parse
    # Filename olan parts → files
    # Filename olmayan parts → params
```

**Path-based Handler:**
```python
if self.path in ["/iov", "/iou"]:
    form_data = parse_multipart_with_multiple_files(self)
else:
    form = parse_multipart(self)  # Single file (eski parser)
```

### 2. ⭐ Kompakt Görünüm (Compact View)
**Dosyalar:** `app120/web.py` (satır 559-575, 637-653)

**Sorun:** 25 dosya × 7 offset = 175 ayrı kart (çok uzun!)  
**Çözüm:** Her dosya için **tek tablo**, tüm offsetler tek tabloda

**Değişiklikler:**
- Offset her satırın başında (Ofs kolonu)
- Timestamp kısa format: `%m-%d %H:%M` (08-20 14:00)
- Kolon isimleri kısaltıldı: Index→Idx, Prev Index→PIdx
- IOV/IOU yoksa minimal gösterim: `📄 file.csv - IOV yok`

**HTML Yapısı:**
```html
<div class='card'>
  <strong>📄 file.csv</strong> - 120 mum, 5 IOV
  <table>
    <tr><th>Ofs</th><th>Seq</th><th>Idx</th><th>Timestamp</th>...</tr>
    <tr><td>-1</td><td>31</td><td>34</td><td>08-20 14:00</td>...</tr>
    <tr><td>+2</td><td>73</td><td>80</td><td>08-23 06:00</td>...</tr>
  </table>
</div>
```

### 3. ⭐ Sequence Validation
**Dosyalar:** `app120/web.py` (satır 467-468, 516-517)

**Sorun:** Form manipülasyonu ile `S3` gönderilebilir → `KeyError` → crash  
**Çözüm:** Validation + fallback to S1

```python
sequence = (params.get("sequence") or "S1").strip()
if sequence not in SEQUENCES_FILTERED:
    sequence = "S1"
```

**Import:**
```python
from app120_iov.counter import SEQUENCES_FILTERED
# {"S1": [7, 13, ...], "S2": [9, 17, ...]}
```

### 4. Emoji Kaldırma
**Dosyalar:** `app120/web.py`, `agents.md`, `app120_iov/README.md`, `landing/web.py`, `appsuite/web.py`

- `🎯 IOV` → `IOV`
- `🔵 IOU` → `IOU`

### 5. app120_iou Eklendi
IOV'nin tamamlayıcı uygulaması (aynı işaret kontrolü, ++ veya --)

### 6. Varsayılan Sequence Değişikliği
IOV ve IOU için S2 → **S1** (daha çok kullanılıyor)

### 7. Boş Offset Gizleme
IOV/IOU içermeyen offsetler gösterilmiyor (kalabalık önlenir)

### 8. Sekme Adı Değişikliği
Tüm uygulamalarda "Analiz" → **"Counter"** (counting işlevini yansıtır)

### 9. app120 Entegrasyonu
IOV ve IOU artık app120 web arayüzünde (sekme 4 ve 5)

Bu rehber, uygulamaların geliştirme ve kullanımında referans kabul edilmelidir.

---

## 🌐 Web Server Routes ve Endpoints

### Port Mapping (Tüm Uygulamalar)
```
app321     → localhost:2160  # 60m
app48      → localhost:2148  # 48m
app72      → localhost:2172  # 72m
app80      → localhost:2180  # 80m
app120     → localhost:2120  # 120m (merkezi)
app120_iov → localhost:2121  # IOV standalone
app120_iou → localhost:2122  # IOU standalone
landing    → localhost:8000  # Ana sayfa
appsuite   → localhost:7000  # Reverse proxy (tüm applar)
```

### HTTP Request Handler Pattern
**Tüm uygulamalar `BaseHTTPRequestHandler` kullanır**

```python
from http.server import BaseHTTPRequestHandler, HTTPServer

class AppXXHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Route matching
        if self.path == "/":
            # Render index page
        elif self.path == "/iou":
            # Render IOU page
        elif self.path.startswith("/favicon"):
            # Serve favicon
        else:
            # 404
    
    def do_POST(self):
        # Form submission handling
        if self.path == "/analyze":
            # Counter analysis
        elif self.path == "/iou":
            # IOU analysis
        elif self.path == "/matrix":
            # Matrix analysis
        # ...
```

### Route Table (app120 örneği)

| Method | Path | Açıklama |
|--------|------|----------|
| GET | `/` | Ana sayfa (Counter formu) |
| POST | `/analyze` | Counter analizi (CSV işle) |
| GET | `/dc` | DC List sayfası |
| POST | `/dc` | DC List sonuçları |
| GET | `/matrix` | Matrix sayfası |
| POST | `/matrix` | Matrix sonuçları |
| GET | `/iov` | IOV sayfası (entegre) |
| POST | `/iov` | IOV analizi (çoklu dosya) |
| GET | `/iou` | IOU sayfası (entegre) |
| POST | `/iou` | IOU analizi (çoklu dosya) |
| GET | `/convert` | 60→120 Converter sayfası |
| POST | `/convert` | Conversion işlemi |
| GET | `/favicon/*` | Favicon servisi |

### Response Format
**Tüm responses HTML:**

```python
# Success response
self.send_response(200)
self.send_header("Content-Type", "text/html; charset=utf-8")
self.end_headers()
self.wfile.write(page("Title", body_html, active_tab="counter"))

# Error response
self.send_response(400)  # or 500
self.send_header("Content-Type", "text/html; charset=utf-8")
self.end_headers()
error_html = f"<div class='card'><h3>Hata</h3><p>{error_msg}</p></div>"
self.wfile.write(page("Hata", error_html))
```

### HTML Template Structure

```python
def page(title: str, body: str, active_tab: str = "analyze") -> bytes:
    """
    Ana HTML template wrapper.
    
    Args:
        title: Page title
        body: HTML body içeriği
        active_tab: Aktif sekme ("analyze", "dc", "matrix", "iov", "iou")
    
    Returns:
        UTF-8 encoded HTML bytes
    """
    html = f"""<!doctype html>
    <html>
      <head>
        <meta charset='utf-8'>
        <title>{title}</title>
        <style>
          /* Inline CSS... */
        </style>
      </head>
      <body>
        <header>
          <h2>app120</h2>
        </header>
        <nav class='tabs'>
          <a href='/' class='{"active" if active_tab=="analyze" else ""}'>Counter</a>
          <a href='/iov' class='{"active" if active_tab=="iov" else ""}'>IOV</a>
          <!-- ... -->
        </nav>
        {body}
      </body>
    </html>"""
    return html.encode("utf-8")
```

---

**Son:** agents.md artık EKSİKSİZ bir teknik referans dokümandır. Başka bir LLM veya developer bu dosyayla projeyi tamamen anlayabilir ve implement edebilir.
