# x1 Codebase - Complete Technical Documentation

> **Purpose:** Bu dokümantasyon, x1 reposundaki tüm kod detaylarını bir sonraki AI context'inin tam olarak anlayabileceği şekilde açıklar.
> 
> **Last Updated:** 2025-01-31
> 
> **Status:** 🚧 IN PROGRESS - Section by section being filled

---

## 📑 Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture & Deployment](#2-architecture--deployment)
3. [Common Core Concepts](#3-common-core-concepts)
4. [Timeframe Applications (7 Apps)](#4-timeframe-applications-7-apps)
5. [Helper Modules](#5-helper-modules)
6. [Data Files & Resources](#6-data-files--resources)
7. [Code Patterns & Standards](#7-code-patterns--standards)
8. [Critical Implementation Details](#8-critical-implementation-details)
9. [Testing & Debugging](#9-testing--debugging)
10. [Future Reference Notes](#10-future-reference-notes)

---

## 1. Project Overview

### 1.1 What is x1?
x1, forex piyasası için çoklu timeframe (48m, 72m, 80m, 90m, 96m, 120m, 60m) bazlı mum analiz sistemidir. Her timeframe için:
- Sequence-based counting (S1/S2 dizileri kullanılarak mum sayımı)
- DC (Distorted Candle) detection ve filtreleme
- Offset sistemli (-3 ile +3 arası) çoklu başlangıç noktası analizi
- IOU/IOV (Inverse OC) analizi (aynı/zıt yönlü momentum tespiti)
- Economic calendar (ForexFactory) haber entegrasyonu
- Pattern analysis (XYZ offset kümeleri üzerinde)

**Temel Amaç:** Haftalık trading cycle'ları belirli matematiksel sequence'lar üzerinden takip etmek, DC mumlarını filtreleyerek "temiz" sayım yapmak ve haber etkilerini analiz etmek.

### 1.2 Technology Stack
- **Python 3.11+** (type hints, dataclasses)
- **Stdlib only** - harici dependency yok (csv, datetime, http.server, argparse, dataclasses, email.parser)
- Web server: http.server.BaseHTTPRequestHandler (development), gunicorn opsiyonel (production)
- Veri formatı: CSV (flexible parsing), JSON (news data)
- Deploy: Docker, Railway, Render.com ready

### 1.3 Repository Structure
```
x1/
├── app48/          # 48 dakika TF (sentetik mum ekleme özelliği)
├── app72/          # 72 dakika TF (2 haftalık veri odaklı)
├── app80/          # 80 dakika TF (Cuma 16:40 kritik)
├── app90/          # 90 dakika TF (iou/ alt modülü)
├── app96/          # 96 dakika TF (iou/ alt modülü)
├── app120/         # 120 dakika TF (iou/ ve iov/ alt modülleri)
├── app321/         # 60 dakika TF (referans, converter yok)
├── appsuite/       # Reverse proxy (tüm app'leri birleştirir)
├── landing/        # Ana giriş sayfası HTML generator
├── news_converter/ # Markdown → JSON parser
├── news_data/      # Economic calendar JSON files (11 adet)
├── ornek/          # Örnek CSV files (7 TF için)
├── favicon/        # PWA assets
├── photos/         # Görsel kaynaklar
├── Dockerfile      # Container build
├── railway.toml    # Railway deployment
├── render.yaml     # Render.com deployment
├── Procfile        # Heroku-style process
└── requirements.txt # (boş - stdlib only)
```

### 1.4 Key Features
- **7 farklı timeframe** desteği (48m, 72m, 80m, 90m, 96m, 120m, 60m)
- **Unified web interface** (appsuite reverse proxy)
- **CSV converter** (küçük TF → büyük TF, örn: 12m → 48m)
- **DC filtering** (her TF için özelleştirilmiş kurallar)
- **Sequence counting** (S1/S2 dizileri, DC'ler atlanır)
- **Offset system** (7 farklı başlangıç noktası analizi: -3..+3)
- **IOU/IOV analysis** (momentum direction tespiti)
- **News integration** (mum bazında haber gösterimi)
- **Pattern matching** (app48: XYZ offset kümeleri, triplet rules)
- **Multi-file upload** (25-50 dosya, ZIP çıktı)
- **Prediction** (hafta sonu gap-aware tahmin)

---

## 2. Architecture & Deployment

### 2.1 Deployment Configurations
**Dockerfile:** Python 3.11-slim base, COPY requirements.txt + app code, CMD: `python -m appsuite.web --host 0.0.0.0 --port ${PORT:-8080}`

**railway.toml:** Builder: NIXPACKS, Start command: `sh -c 'python -m appsuite.web --host 0.0.0.0 --port $PORT'`

**render.yaml:** Web service "candles-trading-suite", Python 3.11.0, Build: `pip install -r requirements.txt`, Start: `sh -c 'python -m appsuite.web --host 0.0.0.0 --port $PORT'`, Health check: `/health`

**Procfile:** `web: python -m appsuite.web --host 0.0.0.0 --port $PORT`

Tüm deployment'lar appsuite.web'i entry point olarak kullanır.

### 2.2 appsuite - Reverse Proxy Architecture
appsuite.web, 8 backend servisi ayrı thread'lerde başlatır ve HTTP reverse proxy görevi görür:

**Backend Başlatma:**
- Her app kendi run() fonksiyonu ile 127.0.0.1:920X portunda başlatılır
- wait_for_port() ile backend hazır olana kadar beklenir (5s timeout)
- Frontend: $PORT (production) veya 2000 (default)

**Routing Logic:**
- Gelen request path'e göre backend eşleşmesi yapılır (prefix matching)
- Örnek: `/app48/analyze` → backend 127.0.0.1:9200'e yönlendirilir, sub-path: `/analyze`
- HTML rewriting: href/action attributelerini prefix ile birleştirir (`/analyze` → `/app48/analyze`)

**Static Assets:**
- `/favicon/*` → favicon/ klasörü
- `/photos/*` → photos/ klasörü  
- `/stars.gif` → photos/stars.gif
- `/` → landing page HTML

**Hop-by-hop header'lar:** Connection, Keep-Alive, Transfer-Encoding gibi header'lar proxy sırasında strip edilir.

### 2.3 Port Assignments
| Service | Internal Port | External Prefix | Description |
|---------|---------------|-----------------|-------------|
| appsuite | $PORT (8080) | / | Reverse proxy frontend |
| app48 | 9200 | /app48 | 48 min timeframe |
| app72 | 9201 | /app72 | 72 min timeframe |
| app80 | 9202 | /app80 | 80 min timeframe |
| app90 | 9203 | /app90 | 90 min timeframe |
| app96 | 9204 | /app96 | 96 min timeframe |
| app120 | 9205 | /app120 | 120 min timeframe |
| app321 | 9206 | /app321 | 60 min reference |
| news_converter | 9207 | /news | MD→JSON converter |

**Standalone modda:** Her app kendi CLI ile doğrudan çalıştırılabilir (örn: `python -m app48.web --port 2020`)

### 2.4 Health Checks & Monitoring
**Endpoint:** `/health` → `200 OK`, body: `"ok"`

**Backend Startup:**
- Her backend thread ile başlatılır
- wait_for_port() ile socket connection test edilir (0.5s interval, 5s timeout)
- Başarısız olursa RuntimeError raise edilir

**Logging:** Minimal, http.server default logging (request/response lines)

---

## 3. Common Core Concepts

### 3.1 Sequences (S1/S2)
**S1:** `[1, 3, 7, 13, 21, 31, 43, 57, 73, 91, 111, 133, 157]`
**S2:** `[1, 5, 9, 17, 25, 37, 49, 65, 81, 101, 121, 145, 169]`

**Kullanım:** Hafta başlangıcından (Pazar 18:00) itibaren non-DC mumlar sayılır. Sequence değeri, o pozisyondaki mumun indexini belirtir.

**Filtered Sequences (IOU için):**
- **S1_filtered:** `[7, 13, 21, 31, ...]` → İlk 2 değer (1,3) hariç
- **S2_filtered:** `[9, 17, 25, 37, ...]` → İlk 2 değer (1,5) hariç
- **Sebep:** Erken değerler unreliable kabul edilir, IOU analizinde kullanılmaz.

### 3.2 DC (Distorted Candle) Rules
**Temel Kural (Tüm App'ler):**
```
current.high ≤ previous.high
current.low ≥ previous.low
current.close ∈ [min(prev.open, prev.close), max(prev.open, prev.close)]
```

**Evrensel İstisnalar:**
1. **Ardışık DC yasak:** Önceki mum DC ise, şimdiki mum DC olamaz
2. **18:00 mumu ASLA DC olamaz** (tüm app'ler, Pazar dahil)

**App-Specific İstisnalar:** (Section 4'te detaylı)

**DC Etkisi:**
- Sayımda atlanır (non-DC mumlar sayılır)
- Allocation sırasında "used_dc" flag ile işaretlenebilir (son adımda tek DC kullanılabilir)

### 3.3 Offset System (-3..+3)
**YENİ MANTIK (2025-10-07 değişikliği):**
- Offset = **Non-DC mum sayısı** (dakika bazlı değil!)
- Base point: İlk 18:00 mumu (base_idx)
- Offset hesaplama: Base'den itibaren non-DC mumlar sayılır, DC'ler atlanır

**Örnek (offset +2):**
- Base: 18:00 (idx 0)
- idx 1: DC değil → count=1
- idx 2: DC → atla
- idx 3: DC değil → count=2 → OFFSET +2 BURASI

**Eski Mantık (artık kullanılmıyor):**
- Dakika bazlı: `target_ts = base_ts + (offset × TF_minutes)`

**determine_offset_start() Fonksiyonu:**
- Input: candles, base_idx, offset, TF_minutes, dc_flags
- Output: (start_idx, target_ts, status)
- Status: "aligned", "before-data", "after-data", "no-data"

### 3.4 IOU Analysis (Inverse OC - Uniform sign)
**IOU = Aynı yönlü momentum:** Ardışık iki mum, aynı direction'da güçlü hareket.

**Kriterler:**
```
|OC| ≥ limit (default: 0.1)
|PrevOC| ≥ limit
OC ve PrevOC AYNI işaret (++ veya --)
abs(|OC| - limit) ≥ tolerance (default: 0.005)  # Limitte çok yakın elenir
```

**Zaman Kısıtlamaları (app-specific):**
- 18:00: IOU olamaz (tüm app'ler)
- 20:00: IOU olamaz (bazı app'ler)
- Cuma hafta kapanışı: IOU olamaz
- 2. Pazar istisnası: app72'de 2. hafta Pazar günü için bazı kısıtlamalar kaldırılır

**IOU Geçersiz Saatler (Her Gün):**
- **app72:** 15:36, 16:48 ❌ IOU olamaz
- **app80:** 15:20, 16:40 ❌ IOU olamaz
- **app90:** 15:00, 16:40 ❌ IOU olamaz
- **app96:** 14:48, 16:24 ❌ IOU olamaz
- **app120:** 16:00 ❌ IOU olamaz

**News Integration:**
- `news_data/*.json` dosyaları otomatik merge edilir
- Mum başlangıç zamanından TF süresi boyunca haberler taranır
- **Null-value events (speeches):** 1 saat öncesinden başlar
- **Kategoriler:** HOLIDAY (tüm gün), SPEECH (null value), ALLDAY (tam gün), NORMAL

**XYZ Filtresi:**
- IOU olan offsetler → XYZ adayı
- Habersiz IOU'lar elenir
- Kalan offsetler → XYZ kümesi (pattern analizi için)

### 3.5 IOV Analysis (Inverse OC - Opposite sign)
**Sadece app120/iov/** modülünde.

**IOV = Zıt yönlü momentum:** Ardışık iki mum, opposite direction'da güçlü hareket.

**Kriterler:**
```
|OC| ≥ limit
|PrevOC| ≥ limit
OC ve PrevOC ZITT işaret (+- veya -+)
```

Diğer tüm kurallar IOU ile aynı (zaman kısıtlamaları, haber entegrasyonu).

### 3.6 Pattern Analysis
**Sadece app48'de tam implementasyon.**

**XYZ Offset Kümeleri:**
- Her dosya için offsetler (habersiz IOU elenir) → XYZ kümesi oluşur
- Örnek: `file1: [0, +1, +3]`, `file2: [-2, 0, +2]`

**Pattern Rules:**
1. **0 (zero) = reset:** Pattern 0'da sıfırlanır, yeni pattern başlar
2. **Triplet matching:**
   - Forward: `1→2→3` veya `-1→-2→-3`
   - Reverse: `3→2→1` veya `-3→-2→-1`
3. **No gaps:** Ardışık değerler olmalı (1→3 olmaz, 1→2→3 olmalı)

**Branch Exploration:**
- Her file sequence için branch'ler explore edilir
- Max 1000 branch (performans limit)
- State: current position, branch history, expected next

**Joker System:**
- Boş XYZ dosyaları → tüm offsetlerde kullanılabilir (joker)
- Auto-detect: XYZ listesi empty olan dosyalar

### 3.7 Timezone Handling
**Kural:** Tüm sistem UTC-4 view kullanır.

**Input Normalization:**
- Girdi UTC-5 ise → +1 saat eklenir
- Girdi UTC-4 ise → değişiklik yok
- CSV'de timezone info varsa → drop edilir (naive datetime)

**Conversion Logic:**
```python
if input_tz in {"UTC-5", "UTC-05"}:
    candle.ts = candle.ts + timedelta(hours=1)
```

### 3.8 CSV Parsing
**Dialect Detection:** csv.Sniffer ile delimiter auto-detect (`,` `;` `\t`)

**Header Aliases (normalize_key ile lowercase):**
- Time: `time`, `timestamp`, `date`, `datetime`
- Open: `open`, `o`, `open (first)`
- High: `high`, `h`
- Low: `low`, `l`
- Close: `close (last)`, `close`, `last`, `c`, `close last`, `close(last)`

**Decimal Normalization:**
```
"1,23456" → "1.23456" (Avrupa formatı)
"" / "nan" / "null" → None (skip row)
```

**Sıralama:** ts ascending (datetime olarak)

### 3.9 Prediction Logic
**48m, 321 (60m):** Basit addition → `next_ts = current_ts + timedelta(minutes=TF)`

**72m, 80m, 90m, 96m, 120m:** Weekend gap-aware prediction:

**predict_next_candle_time() Mantığı:**
1. Normal ekle: `next_ts = current_ts + TF_minutes`
2. **Cuma 16:00 sonrası check:**
   - Eğer current_ts Cuma 16:00 ise → next_ts = Pazar 18:00
3. **Cumartesi/Pazar kontrolü:**
   - Cumartesi → Pazar 18:00'a atla
   - Pazar 18:00 öncesi → Pazar 18:00'a ayarla
4. **Cuma 16:XX geçme:**
   - Next_ts Cuma 16:XX'ı geçecekse → Pazar 18:00'a atla

**DC Counting in Prediction:**
- Prediction, veri dışındaysa son gerçek mumdan başlar
- Son sequence değerinden son gerçek muma kadar non-DC sayılır
- Kalan adımlar üzerine eklenir

---

## 4. Timeframe Applications (7 Apps)

### 4.1 app48 - 48 Minute System
**Port:** 2020 (standalone) / 9200 (appsuite)
**Converter:** 12m → 48m (4 tane 12m = 1 tane 48m + interpolasyon)

**ÖNEMLİ ÖZEL ÖZELLİK: Sentetik Mum Ekleme**
- **İlk gün HARİÇ**, her gün 18:00 ve 18:48'e sentetik mumlar eklenir
- **Interpolasyon:** 17:12 ve 19:36 mumları arasında OHLC interpolate edilir
- **Marking:** `Candle.synthetic = True` flag eklenir
- **Sebep:** 48m TF'de hafta açılışı (18:00) ve cycle başlangıcı (18:48) eksik olur, bu yüzden sentetik eklenir

**DC Kuralları:**
- 18:00: DC olamaz (sentetik olsa bile)
- 18:48: DC olamaz (sentetik olsa bile)
- 19:36: İlk gün hariç DC olamaz
- 13:12-19:36 arası: Özel kural yok (DC olabilir)

**Modüller:**
- `main.py`: Converter + sentetik ekleme
- `pattern.py`: XYZ pattern analysis (find_valid_patterns)
- `web.py`: IOU analizi, Joker selection, Pattern results HTML

**Web Interface:**
- Counter, DC List, Matrix, IOU, 12→48 Converter, Pattern Analysis

### 4.2 app72 - 72 Minute System
**Port:** 2172 / 9201
**Converter:** 12m → 72m (6 tane 12m = 1 tane 72m)

**2 Haftalık Veri Odaklı:**
- 2. Pazar tespit edilir (sunday detection)
- 2. Pazar için bazı DC ve IOU kısıtlamaları gevşetilir

**DC Kuralları:**
- **18:00:** ASLA DC olamaz (Pazar dahil, 2. hafta başlangıcı)
- **Pazar hariç:** 19:12 ve 20:24 DC olamaz (günlük cycle noktaları)
- **Cuma 16:48:** ASLA DC olamaz (1. hafta bitimi, son mum)
- **Hafta kapanışı (16:00):** Gap varsa DC olamaz

**IOU Restrictions:**
- 18:00, 19:12, 20:24: IOU olamaz (2. Pazar hariç)
- Cuma 16:48: IOU olamaz
- **15:36, 16:48:** IOU olamaz (her gün)

**Converter:** 72 dakikalık blocklara 18:00 anchor ile hizalama

### 4.3 app80 - 80 Minute System ⚠️
**Port:** 2180 / 9202
**Converter:** 20m → 80m (4 tane 20m = 1 tane 80m)

**⚠️ KRİTİK DC KURALI (Memory'den):**
- **Cuma 16:40:** ASLA DC olamaz (80m'de son mum)
- **16:00 YOK!** → Doğru sıra: 14:00 → 15:20 → **16:40**
- **Yanlış düzeltme:** Eski kod "16:00 veya 16:40" kontrol ediyordu → Sadece "16:40" olmalı

**DC Kuralları:**
- 18:00: DC olamaz (Pazar dahil)
- Pazar hariç: 19:20 ve 20:40 DC olamaz
- **Cuma 16:40:** DC olamaz (hafta kapanışı)

**IOU Restrictions:**
- **15:20, 16:40:** IOU olamaz (her gün)

**Hafta Kapanışı:** Cuma 16:40 (yeterli gap varsa)

### 4.4 app90 - 90 Minute System
**Port:** 2190 / 9203
**Converter:** 30m → 90m (3 tane 30m = 1 tane 90m)

**DC Kuralları:**
- 18:00: DC olamaz
- 19:30: Pazar hariç DC olamaz
- Cuma 16:30: DC olamaz

**IOU Restrictions:**
- **15:00, 16:40:** IOU olamaz (her gün)

**Modüller:**
- `iou/`: IOU counter, pattern analysis, web interface

### 4.5 app96 - 96 Minute System
**Port:** 2196 / 9204
**Converter:** 12m → 96m (8 tane 12m = 1 tane 96m)

**DC Kuralları:**
- 18:00: DC olamaz
- 19:36: Pazar hariç DC olamaz
- Cuma 16:24: DC olamaz

**IOU Restrictions:**
- **14:48, 16:24:** IOU olamaz (her gün)

**Modüller:**
- `iou/`: IOU counter, pattern analysis, web interface

### 4.6 app120 - 120 Minute System
**Port:** 2120 / 9205
**Converter:** 60m → 120m (2 tane 60m = 1 tane 120m)

**DC Kuralları:**
- 18:00: DC olamaz (Pazar dahil)
- 20:00: Pazar hariç DC olamaz
- Cuma 16:00: Hafta kapanışı (gap varsa) DC olamaz

**IOU Restrictions:**
- **16:00:** IOU olamaz (her gün)

**Modüller:**
- `iou/`: IOU counter, pattern, web
- `iov/`: IOV counter, web (Inverse OC - Opposite sign)
- `iov/README.md` mevcut

### 4.7 app321 - 60 Minute System (Reference)
**Port:** 2019 / 9206
**Converter:** YOK (sadece counter)

**DC Kuralları:**
- **Pazar HARİÇ:** 20:00 DC olamaz
- 13:00-20:00 arası istisna kuralları var (kod içinde, detay compute_sequence_allocations'da)

**Not:** Referans app olarak kullanılır, converter implementasyonu yok

---

## 5. Helper Modules

### 5.1 appsuite - Unified Web Service
**Detaylar Section 2.2'de**

### 5.2 landing - Main Entry Page
**Fonksiyon:** `build_html()` - Tüm app'lere link veren HTML sayfası oluşturur

**İçerik:**
- Her app için kart (port, açıklama, link)
- Favicon ve görsel entegrasyonu
- Inline CSS (modern, responsive)

### 5.3 news_converter - MD→JSON Converter
**Port:** 2199 / 9207

**Fonksiyon:** ForexFactory tarzı Markdown → JSON parser

**Web Interface:**
- Tek dosya yükle → JSON indir
- Çoklu dosya yükle → ZIP indir
- `parser.py`: Markdown parsing logic (regex-based)

**JSON Format:**
```
{
  "meta": {"source": "forex_factory", "year": 2025},
  "days": [
    {
      "date": "2025-03-17",
      "weekday": "Mon",
      "events": [
        {
          "time_24h": "08:30",
          "currency": "USD",
          "title": "Core Retail Sales m/m",
          "values": {"actual": "0.3%", "forecast": "0.3%", "previous": "-0.6%"}
        }
      ]
    }
  ]
}
```

---

## 6. Data Files & Resources

### 6.1 news_data/ - Economic Calendar
**11 JSON dosyası:** `01janto02mar.json`, `1junto5jul.json`, `2marto29mar.json`, `2marto30mar.json`, `2novto27dec.json`, `30marto3may.json`, `3augto6sep.json`, `4mayto31may.json`, `5octto1nov.json`, `6julto2aug.json`, `7septo4oct.json`

**Otomatik Merge:** Tüm JSON dosyaları okunur, `days` array'leri birleştirilir, event_map oluşturulur

**Kullanım:** IOU analizinde mum bazında haber gösterimi

### 6.2 ornek/ - Sample CSV Files
**7 örnek dosya:** `ornek48m.csv`, `ornek60m.csv`, `ornek72m.csv`, `ornek80m.csv`, `ornek90mS.csv`, `ornek96m.csv`, `ornek120m.csv`

**Format:** Standard OHLC CSV (Time, Open, High, Low, Close (Last))

### 6.3 favicon/ - PWA Assets
**7 dosya:** `android-chrome-192x192.png`, `android-chrome-512x512.png`, `apple-touch-icon.png`, `favicon-16x16.png`, `favicon-32x32.png`, `favicon.ico`, `site.webmanifest`

**Servis:** appsuite tarafından `/favicon/*` endpoint'lerinden sunulur

### 6.4 photos/ - Images
**13 görsel:** ICT.jpg, chud.jpeg, kan.jpeg, kits.jpg, lobotomy.jpg, neh.jpeg, penguins.jpg, pussy.png, romantizma.png, silkroad.jpg, stars.gif, suicide.png, umt.jpg

**Kullanım:** Landing page ve app'lerde dekoratif, `/photos/*` ve `/stars.gif` endpoint'leri

---

## 7. Code Patterns & Standards

### 7.1 File Structure Pattern
**Her app klasörü:**
- `__init__.py`: Minimal veya boş
- `counter.py`: Sequence counting, DC logic, CLI entry point
- `main.py`: Converter logic (küçük TF → büyük TF)
- `web.py`: HTTP server, form parsing, HTML generation
- `pattern.py`: (48, 90, 96, 120/iou) Pattern analysis
- `iou/`: (90, 96, 120) IOU submodule
- `iov/`: (120) IOV submodule

### 7.2 Dataclass Usage
**Candle:**
```python
@dataclass
class Candle:
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    synthetic: bool = False  # app48 only
```

**SequenceAllocation:**
```python
@dataclass
class SequenceAllocation:
    idx: Optional[int]
    ts: Optional[datetime]
    used_dc: bool
```

**OffsetComputation:**
```python
@dataclass
class OffsetComputation:
    target_ts: datetime
    offset_status: str
    start_idx: Optional[int]
    actual_ts: Optional[datetime]
    start_ref_ts: datetime
    missing_steps: int
    hits: List[SequenceAllocation]
```

**IOUResult, PatternBranch, PatternResult:** (app-specific, Section 8'de detay)

### 7.3 Type Hints
**Comprehensive typing:**
- `Optional[T]` için None checks
- `List[T]`, `Dict[K, V]`, `Tuple[...]` için collections
- Return types açıkça belirtilir
- Function signatures tam

**Örnek:**
```python
def load_candles(path: str) -> List[Candle]: ...
def compute_dc_flags(candles: List[Candle]) -> List[Optional[bool]]: ...
```

### 7.4 Error Handling
**CSV Parsing:**
- Try-except ile sniffer fallback
- None checks her row için
- ValueError/KeyError yakalanır

**Multipart Parsing:**
- Content-Type ve boundary parsing
- Binary data handling
- Invalid format → empty dict döner

**Validation:**
- Header eksikliği → ValueError raise
- Empty data → warning print
- Out of bounds → None allocation

### 7.5 HTML Generation
**Inline HTML in Python strings:**
- f-string veya % formatting
- CSS inline `<style>` block
- Table-based layouts (IOU, Matrix, Pattern results)
- Form handling: POST → multipart/form-data

**Örnek Pattern:**
```python
html = f"""<!DOCTYPE html>
<html><head><title>{title}</title><style>{css}</style></head>
<body><h1>{heading}</h1>{table_html}</body></html>"""
```

---

## 8. Critical Implementation Details

### 8.1 Synthetic Candle Insertion (app48)
**insert_synthetic_48m() Fonksiyonu:**
1. İlk günü tespit et (min candle date)
2. İlk gün HARİÇ, her gün için:
   - 17:12 ve 19:36 mumlarını bul
   - 18:00 ve 18:48'de mum yoksa → interpolate et
3. **Interpolasyon:**
   - Open: Linear interpolate
   - High: max(prev_high, next_high)
   - Low: min(prev_low, next_low)
   - Close: Linear interpolate
4. `synthetic=True` flag ekle

**Mantık:** 48m TF'de hafta açılışı (18:00) ve cycle başlangıcı (18:48) naturally oluşmaz, bu yüzden sentetik eklenir.

### 8.2 Offset Determination - NEW Logic
**determine_offset_start():** (Detaylar Section 3.3'te)
- Non-DC mum sayısı bazlı
- DC'ler atlanır, sadece non-DC'ler sayılır
- Base'den forward/backward iteration

### 8.3 Sequence Allocation Algorithm
**compute_sequence_allocations():**
1. İlk sequence değeri → start_idx'e ata
2. Her sonraki sequence değeri için:
   - Önceki değerden fark hesapla (steps_needed)
   - DC olmayan mumları say, DC'leri atla
   - **İstisna:** Son adımda tek DC kullanılabilir (used_dc flag)
3. Bulunamazsa → None allocation

**DC Exception Mantığı:**
- Normal: DC'ler atlanır
- Son adım: Eğer counted == steps_needed - 1 ve sonraki mum DC ise → DC kullanılabilir

### 8.4 DC Flag Computation
**compute_dc_flags():**
1. Her mum için prev mum ile karşılaştır
2. Temel DC kuralını kontrol et
3. App-specific zaman istisnalarını uygula
4. Ardışık DC check (prev DC ise, şimdiki DC olamaz)
5. Hafta kapanışı check (gap varsa DC olamaz)

**Edge Cases:**
- İlk mum: None (prev yok)
- Hafta sonu mumları: Zaten filtrelenmiş
- Sentetik mumlar (app48): DC flag normal hesaplanır

### 8.5 IOU Filtering & XYZ Analysis
**analyze_iou():**
1. Tüm offsetler için (-3..+3):
   - Offset start bulunur
   - Filtered sequence üzerinde allocation yapılır
2. Her allocation için IOU kriterleri check edilir
3. Zaman kısıtlamaları uygulanır (18:00, 20:00, etc.)
4. News matching: mum ts'den TF süresi boyunca haberler taranır
5. **XYZ Filtresi:** Habersiz IOU'lar elenir

**News Matching Logic:**
- Null-value (speech) events: 1 saat öncesinden başlar
- Normal events: mum ts + TF minutes içinde
- Kategoriler: HOLIDAY, SPEECH, ALLDAY, NORMAL

### 8.6 Pattern Matching (app48)
**find_valid_patterns():**
1. Her file için XYZ offset kümesi oluşturulur
2. Branch exploration başlatılır (initial branches = XYZ[0])
3. Her branch için:
   - Current state'den next file'a geçiş explore edilir
   - **0 (zero):** Reset, yeni pattern başlar
   - **Triplet:** 1→2→3 veya 3→2→1 check edilir
   - **Gap check:** Ardışık değerler olmalı
4. Max 1000 branch (limit)
5. Final results: PatternResult list (branch_id, file_offsets, success/fail)

### 8.7 Multipart Form Parsing
**_parse_multipart_multiple_files():**
1. Content-Type'dan boundary parse et
2. Body'yi boundary ile split et
3. Her part için:
   - Content-Disposition header parse et
   - filename varsa → file part
   - Binary data extract et
4. Return: `Dict[filename, bytes]`

**Edge Cases:**
- Invalid boundary → empty dict
- Missing Content-Disposition → skip part
- Binary data içinde boundary sequence varsa → problem (nadir)

### 8.8 Timeframe Conversion
**Genel Mantık:**
1. Küçük TF mumları group by TF_block (anchor: 18:00)
2. Her block için aggregate:
   - Open: first candle open
   - Close: last candle close
   - High: max(all highs)
   - Low: min(all lows)
3. Hafta sonu filtreleme (Cumartesi, Pazar 18:00 öncesi)
4. **Önemli:** Next candle open ile current close fix edilir (overlap)

**app48 Özel:**
- 12m → 48m: 4 candle group + interpolasyon
- Sentetik mum ekleme post-process

---

## 9. Testing & Debugging

### 9.1 No Automated Tests
**Current State:** Repoda pytest veya unittest suite yok.

**Manual Testing:**
- CLI ile counter output check
- Web interface üzerinden upload/download test
- ornek/ CSV dosyaları ile referans test

### 9.2 Debug Flags
**CLI Flags:**
- `--show-dc`: DC flag'lerini output'a ekler
- `--predict <value>`: Belirli sequence değerinin tahminini gösterir
- `--predict-next`: Sonraki sequence değerinin tahminini gösterir

**Output Format:**
```
<seq_value> -> idx=<N> ts=<YYYY-MM-DD HH:MM:SS> OC=<±X.XXXXX> PrevOC=<±X.XXXXX> [DC=<bool>] [used_dc=<bool>]
```

### 9.3 Common Issues & Fixes
**CSV Parsing Errors:**
- **Problem:** Header eşleşmemiyor
- **Fix:** normalize_key() ile lowercase, alias check

**DC Edge Cases:**
- **Problem:** Hafta kapanışı yanlış tespit edilir
- **Fix:** Gap minutes check (> TF_minutes)

**Offset Misalignment:**
- **Problem:** OLD logic ile NEW logic karışıyor
- **Fix:** determine_offset_start() consistently kullan, dakika-based hesaplama yapma

**IOU Missing:**
- **Problem:** Time restrictions yanlış uygulanmış
- **Fix:** Weekday check (6 = Pazar), 2. Pazar exception (app72)

---

## 10. Future Reference Notes

### 10.1 Known Bugs & Limitations
- **Multipart boundary collision:** Binary data içinde boundary sequence varsa parsing fail olabilir (nadir)
- **No automated tests:** Manuel testing'e bağımlı
- **Max branch limit:** Pattern analysis 1000 branch ile sınırlı (performans)
- **Timezone assumption:** Girdi UTC-5 veya UTC-4 olmalı, diğer timezone'lar desteklenmez

### 10.2 Design Decisions
**Neden Stdlib Only:**
- Deployment basitliği (dependency yok)
- Minimal production footprint

**Neden DC Exception (son adımda):**
- Real-world data'da bazı sequence değerleri DC'ye denk gelebilir
- Son adımda tek DC kullanarak data loss önlenir

**Neden Sentetik Mum (app48):**
- 48m TF'de 18:00 ve 18:48 naturally oluşmaz
- Cycle analysis için kritik noktalar

**Neden Offset = Non-DC Count (NEW):**
- Dakika-based offset DC'leri dikkate almıyor
- Non-DC count, sequence allocation ile consistent

### 10.3 Memory from Previous Sessions
**app80 DC Fix (2025-10-07):**
- **Problem:** Cuma hafta kapanışı için "16:00 veya 16:40" kontrolü yapılıyordu
- **Gerçek:** 80m sistemde Cuma son mum 16:40 (16:00 YOK)
- **Sıra:** 14:00 → 15:20 → 16:40
- **Fix:** counter.py, README.md, web.py, agents.md düzeltildi

**IOU Invalid Times Added (2025-01-31):**
- **Değişiklik:** Her app için günlük DC saatinden önceki belirli mumlar artık IOU olamaz
- **Sebep:** Bu saatler geçersiz kabul ediliyor, IOU analizinden hariç tutulmalı
- **Eklenen saatler:**
  - app72: 15:36, 16:48
  - app80: 15:20, 16:40
  - app90: 15:00, 16:40
  - app96: 14:48, 16:24
  - app120: 16:00
- **Kapsam:** Her gün için geçerli (sadece Cuma değil)
- **Dosyalar:** app72/counter.py, app80/counter.py, app90/iou/counter.py, app96/iou/counter.py, app120/iou/counter.py

### 10.4 TODOs & Improvements
- **Automated tests:** Pytest suite eklenebilir (DC rules, offset logic, pattern matching)
- **Performance:** Pattern matching branch exploration optimize edilebilir
- **Timezone:** Otomatik timezone detection (input CSV'den)
- **Web UI:** Modern frontend framework (React/Vue) ile yeniden yazılabilir
- **API:** RESTful API endpoint'leri (JSON input/output)
- **Docker Compose:** Multi-container setup (appsuite + backends ayrı container'lar)

---

## Quick Reference Tables

### Port Mapping
| App | Standalone | Appsuite Internal | TF (minutes) | Converter |
|-----|------------|-------------------|--------------|-----------|
| app48 | 2020 | 9200 | 48 | 12m→48m |
| app72 | 2172 | 9201 | 72 | 12m→72m |
| app80 | 2180 | 9202 | 80 | 20m→80m |
| app90 | 2190 | 9203 | 90 | 30m→90m |
| app96 | 2196 | 9204 | 96 | 12m→96m |
| app120 | 2120 | 9205 | 120 | 60m→120m |
| app321 | 2019 | 9206 | 60 | NO |
| news | 2199 | 9207 | - | MD→JSON |
| appsuite | 2000 | - | - | Reverse Proxy |

### DC Rules Summary
| App | 18:00 | Other Time Restrictions | Friday Week Close | Notes |
|-----|-------|-------------------------|-------------------|-------|
| **app48** | ❌ | 18:48❌, 19:36❌ (ilk gün hariç) | - | Sentetik mumlar da DC olamaz |
| **app72** | ❌ | 19:12❌ 20:24❌ (Pazar hariç), Cuma 16:48❌ | 16:00 (gap check) | 2 haftalık veri |
| **app80** | ❌ | 19:20❌ 20:40❌ (Pazar hariç) | **16:40❌** (16:00 YOK!) | ⚠️ KRİTİK |
| **app90** | ❌ | 19:30❌ (Pazar hariç), Cuma 16:30❌ | - | - |
| **app96** | ❌ | 19:36❌ (Pazar hariç), Cuma 16:24❌ | - | - |
| **app120** | ❌ | 20:00❌ (Pazar hariç) | 16:00 (gap check) | IOU+IOV |
| **app321** | - | 20:00❌ (Pazar hariç) | - | 13:00-20:00 istisna |

**Evrensel:** Ardışık DC yasak, temel DC kuralı (high≤prev, low≥prev, close∈range)

### Sequence Values
**S1:** 1, 3, 7, 13, 21, 31, 43, 57, 73, 91, 111, 133, 157
**S2:** 1, 5, 9, 17, 25, 37, 49, 65, 81, 101, 121, 145, 169

**S1_filtered (IOU):** 7, 13, 21, 31, 43, 57, 73, 91, 111, 133, 157
**S2_filtered (IOU):** 9, 17, 25, 37, 49, 65, 81, 101, 121, 145, 169

### File Locations
| Path | Purpose |
|------|---------|
| `app{X}/counter.py` | Sequence counting, DC logic, CLI |
| `app{X}/main.py` | Timeframe converter |
| `app{X}/web.py` | Web interface, HTTP server |
| `app{X}/pattern.py` | Pattern analysis (48, 90, 96, 120/iou) |
| `app{X}/iou/` | IOU submodule (90, 96, 120) |
| `app120/iov/` | IOV submodule |
| `appsuite/web.py` | Reverse proxy entry point |
| `landing/web.py` | Landing page HTML generator |
| `news_converter/parser.py` | MD→JSON parser |
| `news_data/*.json` | Economic calendar data |
| `ornek/*.csv` | Sample CSV files |
| `Dockerfile` | Container build config |
| `render.yaml` | Render.com deployment |
| `railway.toml` | Railway deployment |

---

## Code Snippets Index

### Critical Functions
| Function | Location | Description |
|----------|----------|-------------|
| `load_candles()` | all `counter.py` | CSV parse, flexible header matching |
| `compute_dc_flags()` | all `counter.py` | DC detection with app-specific rules |
| `determine_offset_start()` | all `counter.py` | NEW offset logic (non-DC count) |
| `compute_sequence_allocations()` | all `counter.py` | Sequence mapping, DC exception |
| `insert_synthetic_48m()` | `app48/main.py` | Synthetic candle insertion + interpolation |
| `analyze_iou()` | `app72/counter.py` | IOU analysis with news integration |
| `find_valid_patterns()` | `app48/pattern.py` | XYZ pattern matching, branch exploration |
| `_parse_multipart_multiple_files()` | all `web.py` | Multipart form parsing |
| `convert_12m_to_48m()` | `app48/main.py` | 12m→48m conversion |
| `predict_next_candle_time()` | `counter.py` | Weekend gap-aware prediction |

### Common Patterns
**CSV Parse + Normalize:**
```python
candles = load_candles(csv_path)
dc_flags = compute_dc_flags(candles)
base_idx, status = find_start_index(candles, DEFAULT_START_TOD)
```

**Offset + Sequence Allocation:**
```python
alignment = compute_offset_alignment(candles, dc_flags, base_idx, seq_values, offset)
start_idx = alignment.start_idx
hits = alignment.hits  # List[SequenceAllocation]
```

**IOU Analysis Loop:**
```python
for offset in range(-3, 4):
    # Determine offset start
    # Allocate sequences
    # Check IOU criteria
    # Match news events
    # Filter by XYZ
```

**Multipart Upload Handling:**
```python
files = self._parse_multipart_multiple_files()
for filename, content in files.items():
    candles = parse_csv_from_bytes(content)
    # Process...
```

---

## ✅ Document Status: COMPLETE

**Total Lines:** ~920
**Last Updated:** 2025-01-31
**Sections Filled:** 10/10 + Quick Reference + Code Index

**Key Achievements:**
- ✅ All 7 timeframe apps documented
- ✅ DC rules clarified (incl. app80 critical fix)
- ✅ Offset system NEW logic explained
- ✅ IOU/IOV/Pattern analysis detailed
- ✅ IOU invalid times added (2025-01-31)
- ✅ Deployment configs covered
- ✅ Quick reference tables added

**Next AI Context:** Bu dokümantasyon, x1 codebase'inin tüm detaylarını içerir. Yeni bir görev için bu dosyayı okuyarak context kazanabilirsiniz.
