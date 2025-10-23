# 📘 x1 — Kısa Teknik Rehber (AGENTS)

Son Güncelleme: 2025-10-23
Versiyon: 3.0
Amaç: Agent’lar için öz, doğru ve bakımı kolay referans.

Not: Derin anlatımlar, örnekler ve komutlar için WARP.md ve ilgili app modüllerine bakın. Bu belge; kurallar, değişmezler (invariants) ve hızlı kullanım akışına odaklanır.

---

## 🚀 Hızlı Bakış

- Uygulamalar (TF): app48(48m), app72(72m), app80(80m), app90(90m), app96(96m), app120(120m), app321(60m)
- Tek kapı (appsuite): `python -m appsuite.web --host 0.0.0.0 --port 2000`
- Portlar (varsayılan): app48 2020, app72 2172, app80 2180, app90 2190, app96 2196, app120 2120, app321 2019
- Zaman: UTC‑4 (naive). Girdi UTC‑5 ise converter/`--input-tz` ile +1h normalize edilir.
- Anchor: 18:00. Ofset: −3..+3, yalnızca non‑DC mum sayılır (2025‑10‑07).

---

## 📂 Klasör Özeti

- app48/app72/app80/app90/app96/app120/app321: CLI + http.server web UI
- app90, app96, app120: iou/ (IOU); app120 ayrıca iov/
- landing: giriş sayfası; appsuite: reverse proxy (tüm app’ler tek kapıda)
- news_converter: ForexFactory benzeri Markdown→JSON; IOU UIs `news_data/` okur

---

## 🧭 Değişmezler (Invariants)

- Sequence’ler: S1=[1,3,7,13,21,31,43,57,73,91,111,133,157], S2=[1,5,9,17,25,37,49,65,81,101,121,145,169]
- IOU için filtre: S1 erken [1,3], S2 erken [1,5] hariç tutulur.
- DC baz kuralı: high≤prev.high, low≥prev.low, close∈[prev.open, prev.close]; ardışık DC yasak.
- Ofset: base=18:00’dan sadece non‑DC mumları sayarak bulunur (−: geri, +: ileri). `offset==0` → base.
- Sayım: DC’ler atlanır; son adım DC ise o DC kullanılır (`used_dc=True`).
- Missing steps: `target_ts` yoksa `ts ≥ target_ts` ilk mum seçilir; `missing = ⌊Δ/TF⌋`; dizi `missing+1` ile başlatılır.
- Tahmin: 72/80/90/96/120 haftasonu atlar (Cuma 16:00 → Pazar 18:00); 48/321 doğrudan dakika ekler.

---

## 🕐 DC İstisnaları (Uygulama Bazlı)

- app321: Pazar HARİÇ 20:00 DC değil; sayımda 13:00–20:00 DC istisnası (Pazar hariç).
- app48: İlk gün HARİÇ 18:00, 18:48, 19:36 DC değil; sayımda 13:12–19:36 (Pazar hariç) DC sayılmaz.
- app72: 18:00 asla; Pazar HARİÇ 19:12, 20:24 değil; Cuma 16:48 asla; 16:00 (gap>72) haftasonu kapanışı değil.
- app80: 18:00 asla; Pazar HARİÇ 19:20, 20:40 değil; Cuma 16:40 (gap>80) değil.
- app120: 18:00 asla; 20:00 Pazar HARİÇ değil; Cuma 16:00 (gap>120) değil.
- app90: 18:00 asla; 19:30 Pazar HARİÇ değil; Cuma 16:30 asla.
- app96: 18:00 asla; 19:36 Pazar HARİÇ değil; Cuma 16:24 asla.

---

## 🔍 IOU (Inverse OC — Uniform sign)

- Tanım: OC ve PrevOC limit üstü ve aynı işaret (++/--).
- 5 Şart (sıralı): 1) |OC|≥limit 2) |PrevOC|≥limit 3) |OC−limit|≥tolerance 4) |PrevOC−limit|≥tolerance 5) işaretler aynı.
- Tolerance: 0.005 (limit kontrollerinden sonra).

IOU Zaman İstisnaları
- app48: 18:00, 18:48, 19:36 IOU değil.
- app72: 18:00, 19:12, 20:24 IOU değil (2. Pazar HARİÇ); Cuma 16:48 asla IOU değil.
- app80: 18:00 asla; 19:20, 20:40 IOU değil (2. Pazar HARİÇ); Cuma 16:40 asla IOU değil.
- app90: 18:00 asla; 19:30 IOU değil (Pazar HARİÇ); Cuma 16:30 asla IOU değil.
- app96: 18:00 asla; 19:36 IOU değil (Pazar HARİÇ); Cuma 16:24 asla IOU değil.
- app120: 18:00 asla; 20:00 IOU değil (Pazar HARİÇ); Cuma 16:00 asla IOU değil.
- app321: 18:00, 19:00, 20:00 (dakika=00) IOU değil.

XYZ (Haber) Özeti
- IOU aralığı: [start, start+TF). Null time_24h olayları için [start−1h, start+TF).
- Sadece non‑holiday olaylar sayılır. En az 1 habersiz IOU içeren ofset ELENİR → kalanlar XYZ kümesi.

---

## 🌐 Web & Proxy

- Rotalar özet:
  - app48: `/`, `/dc`, `/matrix`, `/convert`, `/iou`
  - app72/app80/app90/app96: `/`, `/dc`, `/matrix`, `/converter`, `/iou`
  - app120: `/`, `/dc`, `/matrix`, `/iov`, `/iou`, `/converter`
  - app321: `/`, `/dc`, `/matrix`, `/iou`
- appsuite: `/` landing, `/health`, `/favicon/*`, `/photos/*`; tüm app yollarını prefix altında proxy eder ve `href`/`action`’ları yeniden yazar.

---

## 🔄 Converter’lar (Özet)

- app48: 12→48 (Web: `/convert`) — her gün (ilk gün hariç) 18:00 ve 18:48 sentetik mum ekler.
- app72: 12→72 (CLI)
- app80: 20→80 (CLI)
- app90: 30→90 (CLI + Web)
- app96: 12→96 (CLI + Web)
- app120: 60→120 (CLI + Web)

Genel: Girdi UTC‑5 ise +1h; 18:00 anchor ile blok hizası; Cumartesi ve Pazar 18:00 öncesi atla; “close” bir sonraki blok “open” ile düzeltilir.

---

## 📝 CSV Desteği (Özet)

- Başlıklar (case‑insensitive): Time/Date/Datetime/Timestamp, Open (o), High (h), Low (l), Close/Close (Last)/Last (c)
- Tarih‑saat: ISO (tz düşürülür), yaygın formatlar; bazı converter’larda epoch saniye/ms kabul edilir.
- Dialect: csv.Sniffer (`,` `;` `\t`), bulunamazsa `,`. Yükledikten sonra `ts` artan sıralanır.
- Ondalık: “1,23456” → “1.23456”.

---

## 📌 Önemli Notlar

- IOU tolerance kontrolü her zaman limit kontrolünden sonra.
- Holiday olayları görüntülenir fakat XYZ elemeyi etkilemez (non‑holiday sayılır).
- Haftasonu tahmin: 72/80/90/96/120 atlar; 48/321 doğrudan dakika ekler.
- app80 UI’da ek “convert2” linki görünebilir; işlem rotası `/converter`.

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

Kapsamlı örnekler ve komutlar: WARP.md ve app modülleri.

agents.md — v3.0 — 2025-10-23

