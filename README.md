# x1 — Candle-based market analysis toolkit

x1, özel timeframe’lerle (48m, 72m, 80m, 120m ve referans 60m) fiyat davranışını incelemek için yazılmış, pratik ve modüler bir araç setidir. Amaç; standart 1h/4h gibi periyotlarda görünmeyen düzenleri görmek, sequence tabanlı sayım ve DC/IOU taramalarıyla net çalışma hipotezleri oluşturmaktır.

Bu repo; yalnızca standart kütüphane ile çalışan, küçük ayak izli HTTP servisleri (http.server) ve CLI araçları içerir. Veri girişi CSV’dir; çıktı HTML/CSV ve terminal yazımıdır.

---

## İçindekiler

- Genel mimari ve teknoloji
- Uygulamalar (48m, 72m, 80m, 120m, 60m), landing ve news converter
- Veri formatı (CSV), parsing ve zaman yönetimi
- DC (Distortion Condition) kuralları ve offset (-3..+3)
- Sequence (S1/S2) sayımı ve tahmin
- IOU taraması ve haber entegrasyonu (XYZ filtresi)
- Çalıştırma (Web ve CLI), port haritası
- Geliştirme notları ve ipuçları

---

## Teknoloji ve yaklaşım

- Pure Python 3 (http.server, csv, email.parser, dataclasses)
- Harici bağımlılık yok; opsiyonel olarak production’da process manager olarak gunicorn kullanılabilir (requirements.txt’te öneri olarak durur)
- Her uygulama kendi mini HTTP sunucusuyla gelir; ayrıca tümünü tek adreste birleştiren küçük bir reverse proxy (appsuite) de vardır

Neden “non-standard” timeframe? Bazı döngüler 48/72/80/120 dakikada daha okunaklı hale geliyor. x1, sabit bir anchor (18:00) ve offset mantığıyla bu periyotlarda sequence (S1/S2) sayımı, DC ve IOU analizlerini sistematikleştirir.

---

## Proje yapısı (özet)

```
app48/   → 48m analiz + 12→48 converter (web)
app72/   → 72m analiz + 12→72 converter (CLI+web)
app80/   → 80m analiz + 20→80 converter (CLI+web)
app120/  → 120m analiz + 60→120 converter (CLI+web) + IOV/IOU modülleri
app321/  → 60m (referans) analiz + IOU
landing/ → merkezi giriş sayfası
appsuite/→ tüm uygulamalar için basit reverse proxy
news_converter/ → ForexFactory tarzı MD→JSON dönüştürücü (haber datası)
news_data/ → örnek/çalışma JSON haber dosyaları
```

Portlar (varsayılan):
- landing: 2000
- app321 (60m): 2019
- app48 (48m): 2020
- app72 (72m): 2172
- app80 (80m): 2180
- app120 (120m): 2120
- news_converter: 2199
- appsuite (reverse proxy): 2000 (iç servisler 9200-9205)

---

## Veri formatı ve parsing

- Girdi: CSV, zorunlu alanlar Time, Open, High, Low, Close (eş anlamlı başlıklar desteklenir; ör. `last`, `close (last)`, `o/h/l` vb.)
- Delimiter: otomatik tespit (`,` `;` `\t`), bulunamazsa `,`
- Ondalık: `1,23456` gibi varyasyonlar normalize edilir
- Timestamp: ISO (tz atılır), “YYYY-MM-DD HH:MM[:SS]”, “DD.MM.YYYY …”, “MM/DD/YYYY …”; okunabilen ilk format kullanılır
- Sıralama: yükleme sonrası zaman artan (ascending) olarak sıralanır
- Zaman kabulü: timezone-naive ve UTC-4 görünüm (gerekliyse giriş UTC-5 → +1h kaydırılır)

---

## Çekirdek kavramlar

### Candle
```
ts, open, high, low, close  (UTC-4 görünüm)
```
app48’te sentetik hizalama için `synthetic: bool` alanı da kullanılabilir.

### Sequence (S1/S2)
- S1: 1, 3, 7, 13, 21, 31, 43, 57, 73, 91, 111, 133, 157
- S2: 1, 5, 9, 17, 25, 37, 49, 65, 81, 101, 121, 145, 169
- IOU analizinde “erken değerler” hariç tutulan filtreli versiyonlar kullanılır (ör. S1’te 1 ve 3 kalkar)

### DC (Distortion Condition)
- Temel kural: cur.high ≤ prev.high, cur.low ≥ prev.low, cur.close ∈ [min(prev.open, prev.close), max(prev.open, prev.close)]
- Ardışık DC yasak: önceki mum DC ise yenisi DC sayılmaz
- Uygulama bazlı istisnalar (özet):
  - 60m (app321): Pazar hariç 20:00 DC olamaz
  - 48m (app48): İlk gün hariç 18:00, 18:48, 19:36 DC olamaz; ayrıca her gün için 18:00 ve 18:48 sentetik 48m mum eklenebilir
  - 72m (app72): 18:00 asla DC değil; Pazar hariç 19:12 ve 20:24 DC değil; Cuma 16:48 ve hafta kapanışı (16:00, yeterli gap varsa) DC değil
  - 80m (app80): 18:00 asla DC değil; Pazar hariç 19:20 ve 20:40 DC değil; Cuma 16:40 ve hafta kapanışı (16:40, yeterli gap varsa) DC değil
  - 120m (app120): 18:00 asla DC değil; 20:00 Pazarlar hariç DC değil; Cuma 16:00 hafta kapanışı (yeterli gap varsa) DC değil

### Offset (−3..+3)
- Anchor her zaman 18:00’dır; offset, 18:00’a göre DC olmayan mum sayısı üzerinden konumlanır
- Hedef muma tam oturmuyorsa, ilk ≥ hedef zamanındaki muma kayar ve “missing steps” hesaplanır; sayım buna göre başlatılır
- DC’ler sayımda atlanır; son adım DC’ye denk gelirse “used_dc=True” ile o DC yerleştirilebilir

### IOU (Inverse OC — Uniform sign)
- Tanım: OC (open-close) ve prev OC aynı işaretli (++ veya --) ve her ikisinin mutlak değeri limitin üstünde; limit’e çok yakın değerler `tolerance` ile elenir
- IOU taraması tüm offsetler için yapılır; app’e göre 48/60/72/80/120 dakikalık dilim süresi kullanılır
- Haber entegrasyonu: `news_data/*.json` içindeki günlere karşılık gelen event’ler taranır; All Day/speech/holiday ayrımları yapılır
- XYZ filtresi: Bir offset içinde en az bir “news-free IOU” varsa o offset elenir; hiç yoksa offset “XYZ kümesi”ne girer

---

## Uygulamalar ve kullanım

Aşağıdaki web servisleri http.server ile gelir. Hepsi tek başına veya appsuite altında prefix’lerle kullanılabilir.

### app48 (48m)
- Web: `python -m app48.web --host 127.0.0.1 --port 2020`
  - Tabs: Counter, IOU, 12→48 Converter, DC List, Matrix
  - Converter (web): 12m (UTC-5) → 48m (UTC-4); çıktı indirilebilir CSV
- CLI (counter): `python -m app48.main --csv data.csv --input-tz UTC-5 --sequence S2 --offset 0 --show-dc`

### app72 (72m)
- Web: `python -m app72.web --host 127.0.0.1 --port 2172`
- CLI (counter): `python -m app72.counter --csv data.csv --sequence S1 --offset +1`
- CLI (converter): `python -m app72.main --csv input12m.csv --input-tz UTC-5 --output out72m.csv`

### app80 (80m)
- Web: `python -m app80.web --host 127.0.0.1 --port 2180`
- CLI (counter): `python -m app80.counter --csv data.csv --sequence S2 --offset +2`
- CLI (converter): `python -m app80.main --csv input20m.csv --input-tz UTC-5 --output out80m.csv`

### app120 (120m)
- Web: `python -m app120.web --host 127.0.0.1 --port 2120`
- CLI (counter): `python -m app120.counter --csv data.csv --sequence S1 --offset 0 --predict-next`
- CLI (converter): `python -m app120.main --csv input60m.csv --input-tz UTC-5 --output out120m.csv`

### app321 (60m)
- Web: `python -m app321.web --host 127.0.0.1 --port 2019`
- CLI (counter): `python -m app321.main --csv data.csv --sequence S2 --offset 0 --show-dc`

### landing
- `python -m landing.web --host 127.0.0.1 --port 2000`
- App link’leri tek sayfada sunar (favicon ve görsel servisleri dahil)

### appsuite (reverse proxy)
- `python -m appsuite.web --host 0.0.0.0 --port 2000`
- İçeride her app’i 9200-9205 aralığında çalıştırır ve `/app48`, `/app72`, `/app80`, `/app120`, `/app321`, `/news` prefix’leriyle sunar

### news_converter (MD→JSON)
- Web: `python -m news_converter.web --host 127.0.0.1 --port 2199`
- Markdown’dan JSON’a dönüştürür; tek dosyada JSON, çoklu dosyada ZIP indirir

---

## DC ve IOU nüansları (pratik notlar)

- DC hesaplaması her app’te aynı temel kurala dayanır; istisnalar saat/gün kurallarıyla uygulanır ve ardışık DC’ye izin verilmez
- Offset belirlenirken DC olmayan mumlar sayılır; veri boşluklarında hedef sonraki mevcut muma kaydırılır
- IOU’da `limit` ve `tolerance` birlikteliği “limit’e çok yakın” değerleri eleyerek yalancı sinyalleri azaltır
- Haberler taranırken “HOLIDAY / SPEECH / ALLDAY / NORMAL” kategorileri ayrıştırılır; XYZ filtresi “market-impact” içerenleri dikkate alır

---

## Geliştirme

- Python 3.11+ önerilir
- Sanal ortam (opsiyonel):
  - `python -m venv .venv && source .venv/bin/activate`
  - `pip install -r requirements.txt` (gerekirse; default akış standart kütüphaneyle çalışır)
- Büyük CSV’lerde (MB’larca) taramalar uzayabilir; web arayüzleri tek iş parçacıklı ve state-less’tir

---

## Lisans

Bu depo özeldir. Ticari kullanım veya iş birliği talepleri için iletişime geçin.
