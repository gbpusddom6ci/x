# 📘 x1 — Teknik Rehber (AGENTS)

Son Güncelleme: 2025-10-30
Versiyon: 4.0
Amaç: Agent'lar için doğru, öz ve bakımı kolay referans.

Not: Detaylı örnekler ve uzun anlatımlar WARP.md ve app modüllerindedir. Bu belge; kurallar, sapmayan kararlar (invariants), app‑bazı farklar ve hızlı çalışma akışını içerir.

---

## 🚀 Hızlı Bakış

- **Uygulamalar (TF)**: app48(48m), app72(72m), app80(80m), app90(90m), app96(96m), app120(120m), app321(60m)
- **Suite (tek kapı)**: `python -m appsuite.web --host 0.0.0.0 --port 2000`
- **Portlar (standalone)**: app48:2020, app72:2172, app80:2180, app90:2190, app96:2196, app120:2120, app321:2019, landing:2000, news:2199
- **Portlar (appsuite internal)**: 9200(app48), 9201(app72), 9202(app80), 9207(app90), 9206(app96), 9203(app120), 9204(app321), 9205(news)
- **Zaman**: UTC‑4 (naive output). Girdi UTC‑5 ise converter/`--input-tz` ile +1h normalize edilir.
- **Anchor**: 18:00 (tüm app'lerde sabit). **Ofset**: −3..+3 (sadece non‑DC sayılır, 2025‑10‑07 güncellemesi).
- **Bağımlılıklar**: Pure Python stdlib (sadece gunicorn production için opsiyonel).
- **İlgili belgeler**: WARP.md (çalıştırma/komutlar), her app'in `counter.py`/`main.py`/`web.py`/`iou/`/`iov/` dosyaları.

---

## 📂 Klasör & Servis Özeti

**Ana Uygulamalar**
- **app48** (48m): 12m→48m converter + sentetik mum ekleme (18:00, 18:48) + IOU analizi + pattern analizi
- **app72** (72m): 12m→72m converter + IOU analizi + **XYZ pattern analizi** (joker sistemi ile)
- **app80** (80m): 20m↔80m iki yönlü converter + IOU analizi
- **app90** (90m): 30m→90m converter + IOU analizi + hafta sonu filtreleme
- **app96** (96m): 12m→96m converter + IOU analizi
- **app120** (120m): 60m→120m converter + IOU + **IOV** (zıt işaret) analizi
- **app321** (60m): Counter + IOU analizi (converter yok)

**Yardımcı Servisler**
- **appsuite**: Reverse proxy (tüm app'leri tek portta birleştirir, 0.0.0.0:2000)
- **landing**: DVD-screensaver tarzı görsel giriş sayfası
- **news_converter**: ForexFactory Markdown→JSON converter (çoklu dosya + ZIP desteği)
- **news_data/**: JSON haber verileri (IOU XYZ analizinde kullanılır)

**Port Haritası**
- **Dış (appsuite)**: 0.0.0.0:2000 → landing `/`, health `/health`, statik `/favicon/*`, `/photos/*`, `/stars.gif`
- **İç (appsuite)**: 127.0.0.1:9200–9207 → proxy altında `/app48`, `/app72`, `/app80`, `/app90`, `/app96`, `/app120`, `/app321`, `/news`
- **Standalone**: Her app kendi portunda çalışabilir (app48:2020, app72:2172, etc.)

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
- **Candle**: `ts, open, high, low, close` (UTC‑4). app48'de ek: `synthetic: bool`.
- **SequenceAllocation**: `idx, ts, used_dc` (sequence değeri dizi içindeki pozisyonu gösterir).
- **IOUResult**: `seq_value, index, timestamp, oc, prev_oc, prev_index, prev_timestamp` (IOU analiz sonucu).
- **IOVResult**: `seq_value, offset, index, timestamp, oc, prev_oc, prev_index, prev_timestamp` (sadece app120, zıt işaret).
- **PatternBranch**: `path, file_indices, current_state, expected_next, direction` (pattern analizi için).
- **PatternResult**: `pattern, file_sequence, is_complete, length, expected_next` (pattern sonuçları).

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

**Tanım ve Kurallar**
- **IOU**: OC ve PrevOC limit üstü ve **aynı işaret** (++ veya --). Trend devamı sinyali.
- **5 şart (sıra önemlidir)**:
  1) |OC| ≥ limit
  2) |PrevOC| ≥ limit
  3) |OC − limit| ≥ tolerance (limit çok yakın eleme)
  4) |PrevOC − limit| ≥ tolerance
  5) İşaretler aynı: `(OC>0 AND PrevOC>0) OR (OC<0 AND PrevOC<0)`
- **Tolerance**: varsayılan 0.005 (mutlaka limit kontrollerinden **SONRA** uygulanır).
- **Sequence filtre**: SEQUENCES_FILTERED kullanılır (S1: 1,3 hariç; S2: 1,5 hariç).

**App‑Bazlı IOU Saat İstisnaları** (bu saatlerdeki mumlar **ASLA** IOU olamaz)
- **app48**: 18:00, 18:48, 19:36 (her zaman)
- **app72**: 18:00 (her zaman); 19:12, 20:24 (Pazar HARİÇ, **ANCAK 2. Pazar'da bu kısıtlama kalkar**); Cuma 16:48 (her zaman)
- **app80**: 18:00 (her zaman); 19:20, 20:40 (Pazar HARİÇ, **ANCAK 2. Pazar'da bu kısıtlama kalkar**); Cuma 16:40 (her zaman)
- **app90**: 18:00 (her zaman); 19:30 (Pazar HARİÇ); Cuma 16:30 (her zaman)
- **app96**: 18:00 (her zaman); 19:36 (Pazar HARİÇ); Cuma 16:24 (her zaman)
- **app120**: 18:00, 20:00, Cuma 16:00 (hepsi her zaman)
- **app321**: 18:00, 19:00, 20:00 (dakika=00 olan tüm saatler, her zaman)

**XYZ (Haber) Analizi**
- **Amaç**: Habersiz IOU'ları filtreleyerek güvenilir offset kümesi bulmak.
- **Haber aralığı**: `[start, start+TF)`. Null-value events (speeches, statements) için `[start−1h, start+TF)`.
- **Haber kategorileri**:
  - **NORMAL**: actual/forecast/previous değerli (XYZ'yi etkiler)
  - **SPEECH**: time_24h var + null values (XYZ'yi etkiler, 1h öncesi dahil)
  - **HOLIDAY**: "holiday" başlıklı + All Day + null values (gösterilir ama XYZ'yi ETKİLEMEZ)
  - **ALLDAY**: All Day + null values (holiday değil, gösterilir ama XYZ'yi ETKİLEMEZ)
- **Offset eleme**: Bir offsette ≥1 habersiz IOU varsa o offset elenir. Kalan offsetler **XYZ kümesi**'ni oluşturur.
- **Veri kaynağı**: `news_data/*.json` (otomatik merge, candle year ile eşleme).
- **Web UI**: Çoklu dosya upload (max 50 dosya), joker seçimi (max 25 seçilebilir), pattern analizi (sadece app72'de aktif).
- **2. Pazar İstisnası** (app72/app80): 2 haftalık veride 2. Pazar tespit edilir; o gün 19:12/20:24 (app72) veya 19:20/20:40 (app80) IOU olabilir.

## 🔄 IOV (Inverse OC Value — Opposite sign) [Sadece app120]

**Tanım ve Kurallar**
- **IOV**: OC ve PrevOC limit üstü ve **zıt işaret** (+- veya -+). Trend dönüşü sinyali.
- **Şartlar** (3 adım, IOU'dan daha basit):
  1) |OC| ≥ limit
  2) |PrevOC| ≥ limit
  3) İşaretler zıt: `(OC>0 AND PrevOC<0) OR (OC<0 AND PrevOC>0)`
- **Özel**: Tolerance kontrolü **YOK** (IOU'dan farklı).
- **Sequence filtre**: IOU ile aynı (SEQUENCES_FILTERED).
- **DC Kuralları**: app120 matrix/counter ile aynı (18:00, 20:00 (Pazar HARİÇ), Cuma 16:00).
- **Saat kısıtlaması**: IOV için IOU gibi saat bazlı eleme **YOK** (tüm saatler IOV olabilir).
- **Modül**: `app120/iov/counter.py`, `app120/iov/web.py`
- **Web UI**: `/iov` route'u (app120'de mevcut), form ve tablo gösterimi.

---

## 🧩 Pattern Analizi (app72 İçin Uygulanmıştır)

Genel Bakış
- Amaç: Birden fazla haftalık veriyi analiz edip geçerli offset pattern'lerini bulmak.
- Giriş: XYZ kümeleri (habersiz IOU'lar) + opsiyonel joker dosyalar.
- Çıkış: Geçerli pattern'ler, görselleştirme, devam ihtimalleri.

Pattern Kuralları
1. **0 = Reset noktası**: Her cycle sonrası 0 gelir (zorunlu değil ama tamamlanma kriteri).
2. **Triplet yapısı**: `-1→-2→-3→0` veya `-3→-2→-1→0` (aynı şey + için).
3. **Yön sabitleme**: Triplet başladıktan sonra yön değişmez (ascending/descending).
4. **Ardışıklık**: Atlama yok (`-1→-3` geçersiz, `-1→-2→-3` gerekli).
5. **İlk dosya özel**: Herhangi bir offset ile başlayabilir (öncesi bilinmiyor).
   - `-2` ile başlarsa → 2 dal açılır (ascending: bekler -3, descending: bekler -1).
   - `+2` ile başlarsa → 2 dal açılır (ascending: bekler +3, descending: bekler +1).
6. **Son dosya serbest**: Herhangi bir yerde bitebilir.
   - `0` ile biterse → ✅ Tamamlandı
   - Diğer offsetle biterse → ⚠️ Devam ediyor (next: X, Y, Z)

Dallanma Algoritması
- Her dosyada birden fazla geçerli offset varsa → her ihtimal için ayrı dal açılır.
- Max dal limiti: 1000 (kombinatoryal patlamayı önler).
- Dallar dosyalar arası ilerler; geçersiz dallar elenir.

İki Aşamalı İşlem (Web)
1. **Stage 1** (`/iou` POST): Dosya yükle → XYZ hesapla → Joker seçim tablosu göster.
2. **Stage 2** (`/iou_analyze` POST): Joker seçimleri al → Pattern analizi yap → Sonuç göster.

Joker Sistemi
- Problem: Bazı dosyalarda IOU yok/az, XYZ boş.
- Çözüm: Joker yaparak tüm offsetlere (`-3..+3`) izin ver.
- Kullanım: Joker seçim tablosunda checkbox ile işaretle.
- Etki: Joker dosyalar her pattern dalında wildcard olarak kullanılabilir.

Görselleştirme
- **Renklendirme**: Aynı (dosya+offset) grubu → aynı pastel renk (24 renk paleti, cycling).
- **Blok yapısı**: `[🟦 -1 → -2 → -3 🟦] → 0 → [🟨 +1 → +2 → +3 🟨]`
  - **Triplet** (3 ardışık offset): `-1→-2→-3` veya `+1→+2→+3` tek renk bloğu.
  - **Doublet** (2 ardışık offset): Son dosyada biterse 2'li grup da desteklenir.
  - 0'lar renksiz (reset noktası).
- **Tooltip**: Her offset üzerine hover → dosya adı gösterilir (`.rsplit('.', 1)[0]`).
- **Son offsetler özeti**: Tüm pattern'lerin son değerleri (benzersiz) listelenir.
- **Tamamlanma durumu**: ✅ (0 ile biter) veya ⚠️ (devam ediyor, next offsetler gösterilir).

Veri Yapıları
- `PatternBranch`: `path, file_indices, current_state, expected_next, direction`
- `PatternResult`: `pattern, file_sequence, is_complete, length, expected_next`

Dosya Konumu
- Modül: `app72/pattern.py`
- Web entegrasyonu: `app72/web.py` (satır ~580-800)
- Fonksiyonlar: `find_valid_patterns(xyz_data, max_branches=1000)`, `format_pattern_results(results)`

**Pattern Analizi Taşıma Rehberi** (şu an sadece app72'de)
- `pattern.py` kopyala → hedef app klasörüne.
- `web.py` entegrasyonu: `/iou` ve `/iou_analyze` route'larını ekle.
- `MINUTES_PER_STEP` değiştir (app80→80, app90→90, vb.).
- IOU XYZ analizi zaten tüm app'lerde var; pattern logic eklenmesi yeterli.
- Joker selection UI ve format_pattern_results fonksiyonunu kullan.

---

## 🧮 Tahmin (Prediction)

**Haftasonu Jump Logic** (app72, app80, app90, app96, app120)
- **Cuma kapanış kontrolü**: Her app'in son Cuma mumu farklı:
  - app72: 16:48 → Pazar 18:00
  - app80: 16:40 → Pazar 18:00
  - app90: 16:30 → Pazar 18:00 (alternatif: 14:24'ten 16:00'a)
  - app96: 16:24 → Pazar 18:00 (alternatif: 14:24'ten 16:00'a)
  - app120: 16:00 → Pazar 18:00 (alternatif: 14:00'den 16:00'a)
- **Cumartesi**: Herhangi bir saat → Pazar 18:00'a atla.
- **Pazar 18:00 öncesi**: 18:00'a hizala.
- **Algoritma**: `predict_next_candle_time(current_ts, minutes_per_step)` fonksiyonu:
  1. `next_ts = current_ts + timedelta(minutes=TF)`
  2. Hafta sonu kontrolü yap (Cuma kapanış, Cumartesi, Pazar sabahı)
  3. Gerekirse Pazar 18:00'a ayarla
  4. Döngü ile `predict_time_after_n_steps(base_ts, n_steps)` çağrılır

**Basit Prediction** (app48, app321)
- Haftasonu yönetimi **YOK**
- Doğrudan `base_ts + timedelta(minutes=TF * n_steps)` hesaplama
- 48m ve 60m sistemlerde hafta sonu boşluğu ignore edilir

**IOU/IOV Modül Dağılımı**
- **IOU**: app48, app72, app80, app90, app96, app120, app321 (7 app)
- **IOV**: Sadece app120 (zıt işaret analizi)
- **Pattern**: Sadece app72 (XYZ pattern analizi aktif)

---

## 🌐 Web Arayüzü & Rotalar

**Genel Mimari**
- **Tek dosya**: Tüm web UI'lar HTML/CSS inline, `BaseHTTPRequestHandler` üzerine kurulu, **stateless**.
- **Path rewriting**: appsuite, backend linklerini prefix altında yaşatmak için `href/action` yollarını otomatik düzenler.
- **Statik servis**: `/favicon/*`, `/photos/*`, `/stars.gif` appsuite'ten servis edilir.
- **Upload limiti**: 50 MB (tek veya çoklu dosya toplamı).

**Rota Özeti (GET/POST)**
- **app48**: `/` (counter), `/dc` (DC listesi), `/matrix`, `/convert` (12→48 çoklu dosya), `/iou` (XYZ+pattern)
- **app72**: `/` (counter), `/dc`, `/matrix`, `/converter` (12→72 çoklu dosya), `/iou` (XYZ+pattern stage 1), `/iou_analyze` (pattern stage 2)
- **app80**: `/` (counter), `/dc`, `/matrix`, `/converter` (20↔80 iki yönlü, çoklu dosya), `/iou`
- **app90**: `/` (counter), `/dc`, `/matrix`, `/converter` (30→90 çoklu dosya), `/iou`
- **app96**: `/` (counter), `/dc`, `/matrix`, `/converter` (12→96 çoklu dosya), `/iou`
- **app120**: `/` (counter), `/dc`, `/matrix`, `/converter` (60→120 çoklu dosya), `/iou`, `/iov` (IOV analizi)
- **app321**: `/` (counter), `/dc`, `/matrix`, `/iou` (converter yok, sadece counter/IOU)
- **news_converter**: `/` (upload form), `/convert` (MD→JSON, çoklu dosya + ZIP)
- **landing**: `/` (DVD-screensaver wormhole UI), `/health`, statik `/favicon/*`, `/photos/*`, `/stars.gif`
- **appsuite**: `/` (landing proxy), `/health`, `/app48/*`, `/app72/*`, `/app80/*`, `/app90/*`, `/app96/*`, `/app120/*`, `/app321/*`, `/news/*` (reverse proxy)

**Form Parametreleri**
- **Counter/DC/Matrix**: `csv` (file), `sequence` (S1/S2), `offset` (−3..+3), `input_tz` (UTC-4/UTC-5), `show_dc` (checkbox).
- **IOU**: `csv` veya `files[]` (çoklu, max 50), `sequence`, `limit` (float), `tolerance` (float, default 0.005), `xyz_analysis` (checkbox), `xyz_summary_table` (checkbox), `pattern_analysis` (checkbox, sadece app72).
- **Pattern (app72)**: `/iou_analyze` POST ile joker seçimleri (`joker_N` checkbox array, max 25 seçilebilir) gönderilir.
- **IOV (app120)**: `csv`, `sequence`, `limit` (float, tolerance YOK).
- **Converter**: `csv` veya çoklu dosya (max 50 tüm app'ler), `input_tz` (UTC-5 varsayılan, UTC-4 mevcut).
- **News Converter**: `files[]` (max 10 MD dosyası), tek dosya→JSON, çoklu→ZIP.

---

## 🔄 Converter'lar

**Özet (Timeframe Dönüşümleri)**
- **app48**: 12m→48m (Web: `/convert`, CLI: `main.py`). **Sentetik mum ekleme**: İlk gün hariç 18:00 ve 18:48.
- **app72**: 12m→72m (Web: `/converter`, CLI: `main.py`)
- **app80**: 20m↔80m **iki yönlü** (Web: `/converter`, CLI: `main.py`)
- **app90**: 30m→90m (Web: `/converter`, CLI: `main.py`)
- **app96**: 12m→96m (Web: `/converter`, CLI: `main.py`)
- **app120**: 60m→120m (Web: `/converter`, CLI: `main.py`)
- **app321**: **Converter YOK** (sadece 60m counter/IOU)

**Genel Converter Kuralları**
- **TZ normalize**: Girdi UTC‑5 ise +1h kaydır (çıkış UTC‑4). Girdi UTC‑4 ise değişiklik yok. **Tüm işlemler naive datetime** (tzinfo yok).
- **Blok hizası**: Günlük 18:00 anchor'a göre; `block_index = floor((ts−anchor)/TF)`.
- **Hafta sonu filtreleme**: Cumartesi atla; Pazar 18:00 öncesi atla.
- **OHLC birleştirme**:
  - `open = block[0].open` (blok içindeki ilk mum)
  - `close = block[-1].close` (blok içindeki son mum)
  - `high = max(candle.high for candle in block)`
  - `low = min(candle.low for candle in block)`
  - **Close adjustment**: `candles[i].close = candles[i+1].open` (next-open ile düzelt)
  - **Son mum**: `if close >= high: high = close` / `if close <= low: low = close`
- **Çoklu dosya desteği (Web)**: Max 50 dosya (tüm converter'lar). Tek dosya→CSV indir, çoklu→ZIP arşivi indir.
- **Dosya adlandırma**: Tek dosya `original_48m.csv`, ZIP `converted_48m.zip` (app numarası eklenir).

**app48 Sentetik Mum Kuralları**
- **Amaç**: 18:00 ve 18:48 mumlarının eksik olduğu günlerde ekleme yaparak hizalama sağlamak.
- **Kapsam**: İlk gün (Pazar) HARİÇ her gün.
- **Koşul**: 17:12 ve 19:36 mumları mevcut olmalı.
- **Hesaplama**:
  - **18:00 mumu**: `close = c[17:12] + (c[19:36] - c[17:12]) / 3` (lineer interpolasyon 1/3)
  - **18:48 mumu**: `close = c[17:12] + 2 * (c[19:36] - c[17:12]) / 3` (lineer interpolasyon 2/3)
  - `open = prev_candle.close`, `high = max(open, close)`, `low = min(open, close)`
- **İşaretleme**: `synthetic=True` (DC kontrollerinde kullanılabilir).

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

**Kritik Kurallar**
- **IOU tolerance**: Mutlaka limit kontrolünden **SONRA** uygulanır; sırayı değiştirmek yanlış elemeye yol açar.
- **Holiday olayları**: Gösterilir ama XYZ elemeyi **ETKİLEMEZ** (sadece NORMAL ve SPEECH kategorisi etkiler).
- **Ofset başlangıcı**: Non-DC garanti edilir, ama dizi ilerlerken "son adım DC" kuralı hala geçerlidir.
- **News matching**: Candle **year** kullanılır, JSON year'ı ignore edilir (yıllara göre aynı tarihler eşlenir).
- **IOV vs IOU**: IOV tolerance kontrolü **yapmaz**, sadece zıt işaret kontrolü yapar.

**Web UI**
- **Upload limiti**: 50 MB toplam (tek veya çoklu dosya).
- **IOU çoklu dosya**: Max 50 dosya upload, max 25 joker seçimi (pattern analizi için).
- **Pattern analizi**: Şu an sadece app72'de aktif; `/iou` (stage 1: XYZ hesaplama) ve `/iou_analyze` (stage 2: pattern analizi) iki aşamalı flow.
- **Joker sistemi**: Boş veya az IOU'lu XYZ dosyalarını wildcard (-3..+3 tüm offsetler) yaparak pattern devamını sağlar.
- **ZIP indirme**: Çoklu dosya converter/IOU'da otomatik ZIP oluşturulur (in-memory, zipfile.ZipFile).

**Performance**
- **Geniş CSV**: ≥10 MB dosyalarda işlem süresi artar (pure Python stdlib, optimizasyon yok).
- **Stateless**: Her request bağımsız, session/cache yok.
- **Concurrent**: appsuite tüm backend'leri paralel başlatır (threading.Thread daemon=True).

**Deployment**
- **Railway/Render/Fly.io**: `railway.toml`, `render.yaml`, `Dockerfile` hazır.
- **Health check**: `/health` endpoint (appsuite ve tüm app'ler).
- **Port binding**: Railway/Render otomatik `$PORT` inject eder.

---

## 📚 Fonksiyon İmzaları (Özet)

**CSV & Veri**
- `load_candles(path: str) -> List[Candle]` — CSV yükle, parse et, sırala
- `load_candles_from_text(text: str) -> List[Candle]` — String CSV (web upload için)
- `estimate_timeframe_minutes(candles) -> Optional[float]` — TF otomatik tespit (median)

**DC & Counting**
- `compute_dc_flags(candles: List[Candle]) -> List[Optional[bool]]` — DC bayrakları hesapla
- `find_start_index(candles, start_tod) -> (int, str)` — 18:00 base bulma
- `determine_offset_start(candles, base_idx, offset, minutes_per_step?, dc_flags?) -> (idx?, ts?, status)` — Non-DC offset hesaplama
- `compute_sequence_allocations(candles, dc_flags, start_idx, seq_values) -> List[SequenceAllocation]` — Sequence allocation
- `compute_offset_alignment(candles, dc_flags, base_idx, seq_values, offset) -> OffsetComputation` — Tüm offset hesaplama wrapper

**Prediction (Weekend Jump)**
- `predict_next_candle_time(current_ts, minutes_per_step) -> datetime` — Haftasonu jump ile bir sonraki mum
- `predict_time_after_n_steps(base_ts, n_steps, minutes_per_step) -> datetime` — n adım sonrası (72/80/90/96/120)

**IOU/IOV Analysis**
- `analyze_iou(candles, sequence, limit, tolerance=0.005) -> Dict[int, List[IOUResult]]` — Tüm offsetler için IOU
- `analyze_iov(candles, sequence, limit) -> Dict[int, List[IOVResult]]` — IOV (sadece app120)

**News Integration**
- `load_news_data_from_directory(dir_path) -> Dict[str, List[Dict]]` — news_data/ JSON merge
- `find_news_in_timerange(events_by_date, start_ts, duration_minutes) -> List[Dict]` — Zaman aralığında haber bul
- `categorize_news_event(event) -> str` — HOLIDAY/SPEECH/ALLDAY/NORMAL kategorize
- `format_news_events(events) -> str` — HTML için haber formatla

**Pattern Analysis (app72)**
- `find_valid_patterns(xyz_data, max_branches=1000) -> List[PatternResult]` — Geçerli pattern'ler bul
- `format_pattern_results(results) -> str` — HTML renklendirme ile pattern göster

**Converters**
- `adjust_to_output_tz(candles, input_tz) -> (List[Candle], str)` — UTC-5→UTC-4 shift
- `convert_12m_to_48m(candles) -> List[Candle]` — app48
- `convert_12m_to_72m(candles) -> List[Candle]` — app72
- `convert_20m_to_80m(candles) -> List[Candle]` — app80
- `convert_30m_to_90m(candles) -> List[Candle]` — app90
- `convert_12m_to_96m(candles) -> List[Candle]` — app96
- `convert_60m_to_120m(candles) -> List[Candle]` — app120
- `insert_synthetic_48m(candles, start_day) -> (List[Candle], int)` — app48 sentetik mum

**Web Utilities**
- `page(title, body, active_tab?) -> bytes` — HTML page wrapper
- `format_price(value: float) -> str` — Fiyat formatı (6 decimal, trailing zero trim)
- `fmt_ts(dt: Optional[datetime]) -> str` — Timestamp format
- `fmt_pip(delta: Optional[float]) -> str` — OC/PrevOC format (+/- işaretli)

—

Kapsamlı örnekler ve komutlar için WARP.md ve app modüllerine bakın.

---

## 🔧 Deployment & Configuration

**Docker**
```bash
docker build -t x1 .
docker run --rm -e PORT=2000 -p 2000:2000 x1
```

**Railway**
- Config: `railway.toml`
- Build: NIXPACKS (auto-detect)
- Start: `python -m appsuite.web --host 0.0.0.0 --port $PORT`

**Render**
- Config: `render.yaml`
- Region: frankfurt (veya oregon, singapore)
- Health: `/health`
- Free plan: 1 service, auto-sleep

**Environment Variables**
- `PORT`: Web server port (Railway/Render inject eder)
- `PYTHON_VERSION`: 3.11+ (requirements.txt belirtir)

**Requirements**
- Python: 3.11+
- Dependencies: Sadece `gunicorn` (production için opsiyonel)
- Stdlib: csv, http.server, datetime, dataclasses, argparse, json, io, zipfile

---

agents.md — v4.0 — 2025-10-30 — Comprehensive technical reference for x1 trading analysis suite
