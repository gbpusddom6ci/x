# 📘 x1 — Teknik Rehber (AGENTS)

Son Güncelleme: 2025-10-23
Versiyon: 3.3
Amaç: Agent’lar için doğru, öz ve bakımı kolay referans (200–500 satır arası).

Not: Detaylı örnekler ve uzun anlatımlar WARP.md ve app modüllerindedir. Bu belge; kurallar, sapmayan kararlar (invariants), app‑bazı farklar ve hızlı çalışma akışını içerir.

---

## 🚀 Hızlı Bakış

- Uygulamalar (TF): app48(48m), app72(72m), app80(80m), app90(90m), app96(96m), app120(120m), app321(60m)
- Suite (tek kapı): `python -m appsuite.web --host 0.0.0.0 --port 2000`
- Portlar (varsayılan): app48 2020, app72 2172, app80 2180, app90 2190, app96 2196, app120 2120, app321 2019
- Zaman: UTC‑4 (naive). Girdi UTC‑5 ise converter/`--input-tz` ile +1h normalize edilir.
- Anchor: 18:00. Ofset: −3..+3 (sadece non‑DC sayılır, 2025‑10‑07).
- İlgili belgeler: WARP.md (çalıştırma/komutlar), her app’in `counter.py`/`main.py`/`web.py`/`iou/`/`iov/` dosyaları.

---

## 📂 Klasör & Servis Özeti

- app48/app72/app80/app90/app96/app120/app321: CLI counter + http.server tabanlı web UI.
- iou/: app90, app96, app120 için IOU analiz modülleri; app120’de ek olarak iov/.
- landing: görsel giriş; appsuite: reverse proxy (tüm servisleri tek portta sunar).
- news_converter: ForexFactory benzeri Markdown→JSON üretir; IOU UIs `news_data/` klasörünü okur.

Port Haritası (appsuite varsayılanları)
- Dış: appsuite 0.0.0.0:2000 (landing `/`, health `/health`, statik `/favicon/*`, `/photos/*`)
- İç: 127.0.0.1:9200–9207 (app48…app321, news_converter), proxy altında `/app48`, `/app72`, …, `/news` olarak sunulur.

---

## 🧭 Değişmezler (Invariants)

- Sequence’ler: S1=[1,3,7,13,21,31,43,57,73,91,111,133,157], S2=[1,5,9,17,25,37,49,65,81,101,121,145,169]
- IOU’da filtre: S1 erken [1,3], S2 erken [1,5] hariç.
- DC baz kuralı: high≤prev.high, low≥prev.low, close∈[prev.open, prev.close]. Ardışık DC yasak.
- Ofset belirleme: base=18:00’dan yalnız non‑DC mum sayılır (− geriye, + ileri). `offset==0` → base.
- Sayım (sequence allocation): DC’ler atlanır; son adım DC ise o DC kullanılabilir (`used_dc=True`).
- Missing steps: `target_ts` yoksa `ts ≥ target_ts` ilk mum seçilir; `missing = ⌊Δ/TF⌋`; dizi `missing+1` ile başlatılır, `≤missing` değerler veri dışıdır.
- Tahmin: 72/80/90/96/120 haftasonu atlar (Cuma 16:00 → Pazar 18:00); 48/321 doğrudan dakika ekler.

Veri Yapıları (özet)
- Candle: `ts, open, high, low, close` (UTC‑4). app48’de ek: `synthetic: bool`.
- SequenceAllocation: `idx, ts, used_dc`.
- IOUResult: `seq_value, index, timestamp, oc, prev_oc, prev_index, prev_timestamp`.

Sequence Kullanımı
- Genel analizde SEQUENCES (tam dizi), IOU’da SEQUENCES_FILTERED (erken değerler hariç) kullanılır.

---

## 🕐 DC İstisnaları (App Bazlı Kural Özeti)

Temel DC kuralı ve ardışık DC yasağı tüm app’lerde geçerlidir. Aşağıdaki istisnalar DC tespitinde “DC olamaz” olarak uygulanır. Ayrıca bazı app’lerde sayım sırasında belirli saat aralıklarında DC, “DC gibi sayılmama” (yani atlanmama) istisnasına tabidir.

- app321 (60m)
  - DC tespiti: Pazar HARİÇ 20:00 DC olamaz.
  - Sayım istisnası: Pazar hariç 13:00–20:00 aralığında DC’ler “DC gibi” muamele görmez; normal mum gibi sayılır (skiplanmaz).

- app48 (48m)
  - DC tespiti: İlk gün HARİÇ 18:00, 18:48, 19:36 DC olamaz.
  - Sayım istisnası: Pazar hariç 13:12–19:36 aralığındaki DC’ler “DC gibi” muamele görmez; normal mum gibi sayılır.

- app72 (72m)
  - DC tespiti: 18:00 asla; Pazar HARİÇ 19:12 ve 20:24 DC olamaz.
  - Ek: Cuma 16:48 asla DC değil; 16:00 haftasonu kapanışı (bir sonraki mumla gap>72) DC değil.

- app80 (80m)
  - DC tespiti: 18:00 asla; Pazar HARİÇ 19:20 ve 20:40 DC olamaz.
  - Ek: Cuma 16:40 (gap>80 ile haftasonu kapanışı) DC değil.

- app120 (120m)
  - DC tespiti: 18:00 asla; 20:00 Pazar HARİÇ DC olamaz.
  - Ek: Cuma 16:00 (gap>120) DC değil. Günlük cycle özel saat istisnası yok.

- app90 (90m)
  - DC tespiti: 18:00 asla; 19:30 Pazar HARİÇ DC olamaz; Cuma 16:30 asla DC değil.

- app96 (96m)
  - DC tespiti: 18:00 asla; 19:36 Pazar HARİÇ DC olamaz; Cuma 16:24 asla DC değil.

---

## 🎯 Ofset Mantığı (Detay)

- Base mumu: 18:00 (tüm app’lerde ortak). `find_start_index` 18:00’e hizalar.
- `determine_offset_start`: base’den başlayarak yalnızca non‑DC mum sayar; hedef non‑DC muma ait `(idx, ts, status)` döner. `offset==0` → base.
- Hedef ts referansı: `base_ts + offset*TF` olarak hesaplanır; veri tam denk gelmezse `ts ≥ target_ts` ilk mum alınır ve `missing_steps` hesaplanır.
- “Non‑DC başlangıç” garantisi: Ofset başlangıç mumu DC değildir; devamındaki sayımda DC atlama ve “son adım DC kullanımı” kuralı korunur.

Sequence Allocation (özet algoritma)
- İlk değer: `start_idx` atanır.
- Sonraki değer: adım farkı kadar ilerle; DC’leri atla; son adım DC ise onu yerleştir (`used_dc=True`).
- `missing_steps>0` ise dizi `missing+1` ile başlar; `≤missing` değerler veri dışında kalır (tahmin tarafına düşer).

---

## 🔍 IOU (Inverse OC — Uniform sign)

Tanım ve Kurallar
- IOU: OC ve PrevOC limit üstü ve aynı işaret (++ veya --).
- 5 şart (sıra önemlidir):
  1) |OC| ≥ limit
  2) |PrevOC| ≥ limit
  3) |OC − limit| ≥ tolerance (limit çok yakın eleme)
  4) |PrevOC − limit| ≥ tolerance
  5) İşaretler aynı
- Tolerance varsayılanı: 0.005 (mutlaka limit kontrollerinden SONRA uygulanır).

App‑Bazlı IOU Saat İstisnaları
- app48: 18:00, 18:48, 19:36 IOU değil.
- app72: 18:00, 19:12, 20:24 IOU değil (2. Pazar HARİÇ); Cuma 16:48 asla IOU değil.
- app80: 18:00 asla; 19:20, 20:40 IOU değil (2. Pazar HARİÇ); Cuma 16:40 asla IOU değil.
- app90: 18:00 asla; 19:30 IOU değil (Pazar HARİÇ); Cuma 16:30 asla IOU değil.
- app96: 18:00 asla; 19:36 IOU değil (Pazar HARİÇ); Cuma 16:24 asla IOU değil.
- app120: 18:00 asla; 20:00 asla; Cuma 16:00 asla IOU değil.
- app321: 18:00, 19:00, 20:00 (dakika=00) IOU değil.

XYZ (Haber) Analizi (özet)
- IOU aralığı: [start, start+TF). `time_24h=null` olaylar için [start−1h, start+TF).
- “Holiday” olayları gösterilir ama XYZ elemede sayılmaz (non‑holiday filtre).
- Offset eleme: bir ofsette ≥1 habersiz IOU varsa ofset elenir; kalanı “XYZ kümesi”dir.

---

## 🧮 Tahmin (Prediction)

- 72/80/90/96/120: Haftasonu boşluğu kuralları uygulanır.
  - Cuma 16:00 sonrası → Pazar 18:00’a sıçrama (uygulamaya göre TF adımıyla ilerlerken bu kural gözetilir).
  - Cumartesi: Pazar 18:00’a atla.
  - Pazar 18:00’dan önce: 18:00’a hizala.
- 48/321: Haftasonu yönetimi yok; dakika ekleme ile ilerler.

Not: app90/app96/app120 IOU modüllerinde haber eşlemesi kullanılabilir; app120’de ayrıca IOV (zıt işaret) analizi vardır.

---

## 🌐 Web Arayüzü & Rotalar

Genel
- Tüm web’ler tek dosya HTML/CSS ve BaseHTTPRequestHandler üzerine kurulu, stateless.
- appsuite, backend linklerini prefix altında yaşatmak için `href/action` yollarını yeniden yazar.
- Favicon ve görseller: `/favicon/*`, `/photos/*` appsuite’ten statik servis edilir.

Rota Özeti
- app48: `/`, `/dc`, `/matrix`, `/convert`, `/iou`
- app72: `/`, `/dc`, `/matrix`, `/converter`, `/iou`
- app80: `/`, `/dc`, `/matrix`, `/converter`, `/iou`
- app90: `/`, `/dc`, `/matrix`, `/converter`, `/iou`
- app96: `/`, `/dc`, `/matrix`, `/converter`, `/iou`
- app120: `/`, `/dc`, `/matrix`, `/iov`, `/iou`, `/converter`
- app321: `/`, `/dc`, `/matrix`, `/iou`

Form Parametreleri (örnek)
- Counter/DC/Matrix: `csv` (file), `sequence` (S1/S2), `offset` (−3..+3), opsiyonel gösterim bayrakları.
- IOU (çoklu dosya): `files[]` (en fazla 25), `sequence`, `limit`, `tolerance`.

---

## 🔄 Converter’lar

Özet
- app48: 12→48 (Web: `/convert`). İlk gün hariç her gün 18:00 ve 18:48 sentetik mum ekler (hizalama/doğruluk için).
- app72: 12→72 (CLI)
- app80: 20→80 (CLI)
- app90: 30→90 (CLI + Web)
- app96: 12→96 (CLI + Web)
- app120: 60→120 (CLI + Web)

Genel Kurallar
- TZ normalize: Girdi UTC‑5 ise +1h kaydır (çıkış UTC‑4). Girdi UTC‑4 ise değişiklik yok.
- Blok hizası: Günlük 18:00 anchor’a göre; `block_index = floor((ts−anchor)/TF)`.
- Hafta sonu filtreleme: Cumartesi atla; Pazar 18:00 öncesi atla.
- OHLC birleştirme: open=ilk, close=son (sonra close’u bir sonraki blok open’ı ile düzelt). high/low gerekli ise close’a göre ayarlanır.
- Son mum: close≥high ise high=close; close≤low ise low=close (kapanış tutarlılığı).

app48 Sentetik Kuralları (kısa)
- Her gün (ilk gün hariç) 17:12–19:36 aralığında 18:00 ve 18:48 eksikse eklenir. Değerler lineer aralıkla (1/3, 2/3) tahmin edilir; `synthetic=True`.

—

## 📝 CSV Desteği

Başlıklar (case‑insensitive)
- Time: `time`, `date`, `datetime`, `timestamp`
- Open: `open`, `o`, `open (first)`
- High: `high`, `h`
- Low: `low`, `l`
- Close: `close`, `close (last)`, `last`, `c`, `close last`, `close(last)`

Tarih‑Saat
- ISO: `...Z`, `+00:00` gibi tz’li değerlerde tz düşürülür (local wall time kabul edilir).
- Yaygın formatlar desteklenir. Bazı converter’lar epoch saniye/ms tamsayılarını da kabul eder.

Ondalık & Dialect
- Ondalık: `"1,23456"` → `1.23456` (yalnız virgüllü hallerde).
- Delimiter: csv.Sniffer (`,` `;` `\t`), bulunamazsa `,` düşer.
- Sıralama: Yüklendikten sonra `candles.sort(key=lambda x: x.ts)`.

---

## ⚙️ CLI Hızlı Başlangıç

Suite (hepsi tek yerde)
- `python -m appsuite.web --host 0.0.0.0 --port 2000`

Tekil Web Uygulamaları
- `python -m app48.web  --host 127.0.0.1 --port 2020`
- `python -m app72.web  --host 127.0.0.1 --port 2172`
- `python -m app80.web  --host 127.0.0.1 --port 2180`
- `python -m app90.web  --host 127.0.0.1 --port 2190`
- `python -m app96.web  --host 127.0.0.1 --port 2196`
- `python -m app120.web --host 127.0.0.1 --port 2120`
- `python -m app321.web --host 127.0.0.1 --port 2019`
- `python -m landing.web --host 127.0.0.1 --port 2000`

Counter (örnekler)
- `python -m app48.main  --csv data.csv --sequence S2 --offset +1 --show-dc`
- `python -m app72.counter --csv data.csv --sequence S1 --offset 0`
- `python -m app80.counter --csv data.csv --sequence S2 --offset +2`
- `python -m app90.counter --csv data.csv --sequence S1 --offset 0`
- `python -m app96.counter --csv data.csv --sequence S1 --offset 0`
- `python -m app120.counter --csv data.csv --sequence S1 --offset 0 --predict-next`
- `python -m app321.main --csv data.csv --sequence S2 --offset 0 --show-dc`

Converter (örnekler)
- `python -m app72.main  --csv input12m.csv --input-tz UTC-5 --output out72m.csv`
- `python -m app80.main  --csv input20m.csv --input-tz UTC-5 --output out80m.csv`
- `python -m app90.main  --csv input30m.csv --input-tz UTC-5 --output out90m.csv`
- `python -m app96.main  --csv input12m.csv --input-tz UTC-5 --output out96m.csv`
- `python -m app120.main --csv input60m.csv --input-tz UTC-5 --output out120m.csv`

---

## 📌 Önemli Notlar & İpuçları

- IOU tolerance kuralı, limit kontrolü geçildikten sonra uygulanır; aksi halde yanlış eleme olur.
- “Holiday” olayları görüntüde tutulur fakat XYZ elemeyi ETKİLEMEZ (yalnız non‑holiday sayılır).
- Ofset başlangıcı non‑DC garanti edilse bile, dizi ilerlerken “son adım DC” kuralı geçerlidir.
- app80 UI’da ek “convert2” linki görünebilir; gerçek dönüşüm rotası `/converter`.
- Geniş CSV’lerde (≥10MB) işlem süresi artar; IOU çoklu yükleme limiti 25 dosyadır.

---

## 📚 Fonksiyon İmzaları (seçki)

- CSV: `load_candles(path) -> List[Candle]`
- DC: `compute_dc_flags(candles) -> List[Optional[bool]]`
- Ofset: `determine_offset_start(candles, base_idx, offset, minutes_per_step?, dc_flags?) -> (idx?, ts?, status)`
- Sayım: `compute_sequence_allocations(candles, dc_flags, start_idx, seq_values) -> List[SequenceAllocation]`
- Tahmin: `predict_time_after_n_steps(base_ts, n, minutes_per_step) -> datetime`
- IOU: `analyze_iou(candles, sequence, limit, tolerance=0.005) -> Dict[int, List[IOUResult]]`
- Haber: `load_news_data_from_directory(dir) -> Dict[str, List[Dict]]`, `find_news_in_timerange(...) -> List[Dict]`, `is_holiday_event(event) -> bool`
- Converter: `adjust_to_output_tz(...)`, `convert_12m_to_48m`, `convert_12m_to_72m`, `convert_20m_to_80m`, `convert_30m_to_90m`, `convert_12m_to_96m`, `convert_60m_to_120m`

—

Kapsamlı örnekler ve komutlar için WARP.md ve app modüllerine bakın.

agents.md — v3.3 — 2025-10-23
