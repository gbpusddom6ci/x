# App72 IOU News Checker 📊

ForexFactory economic calendar integration for IOU offset analysis.

## Özellikler

- ✅ IOU CSV dosyalarını okur
- ✅ Her offset için 72 dakikalık mum aralığını hesaplar
- ✅ ForexFactory'den real-time haber çeker
- ✅ Mid ve High impact haberleri filtreler
- ✅ UTC-4 timezone dönüşümü
- ✅ Web arayüzü + CLI desteği
- ✅ CSV download ile sonuç çıktısı

## Kullanım

### Web Arayüzü (Önerilen)

```bash
python3 -m app72_iou.web
```

Tarayıcıda: `http://localhost:2172`

1. IOU CSV dosyanızı yükleyin
2. Candle duration (varsayılan 72 dk) ayarlayın
3. "Check ForexFactory News" butonuna tıklayın
4. Sonuçları görüntüleyin ve CSV olarak indirin

### CLI Kullanımı

```bash
# Basit kullanım
python3 -m app72_iou.cli ornek.csv

# Output dosyası belirterek
python3 -m app72_iou.cli ornek.csv ornek_with_news.csv

# Farklı candle duration ile
python3 -m app72_iou.cli ornek.csv output.csv 60
```

### Python Modülü Olarak

```python
from app72_iou.news_checker import process_iou_csv

results = process_iou_csv('ornek.csv', 'output.csv', candle_minutes=72)
```

## Input Format

CSV dosyası şu kolonları içermelidir:

```
Ofs,Seq,Idx,Timestamp,OC,PrevOC,PIdx
-1,13,12,06-09 08:24,+0.07000,+0.10500,11
+0,21,23,06-09 21:36,+0.12400,+0.16700,22
```

## Output Format

Aynı kolonlar + **News** kolonu eklenir:

```
Ofs,Seq,Idx,Timestamp,OC,PrevOC,PIdx,News
-1,13,12,06-09 08:24,+0.07000,+0.10500,11,[HIG] USD NFP @ 8:30am | [MED] EUR CPI @ 9:00am
+0,21,23,06-09 21:36,+0.12400,+0.16700,22,-
```

## Nasıl Çalışır?

1. **Timestamp Parse:** `06-09 08:24` → DateTime object
2. **Candle Range:** `08:24` + 72 dakika = `09:36`
3. **ForexFactory Fetch:** O tarih aralığında haberleri çek
4. **Filter:** Sadece Mid/High impact haberleri al
5. **Match:** Haber saati candle aralığına düşüyorsa ekle
6. **Output:** News kolonu ile CSV oluştur

## Timezone

- **Input:** UTC-4 (IOU CSV)
- **ForexFactory:** EST/EDT → UTC-4'e çevrilir
- **Output:** UTC-4

## Dependencies

```
requests>=2.31.0
beautifulsoup4>=4.12.0
lxml>=4.9.0
pytz>=2023.3
pandas>=2.0.0
```

## Port

Varsayılan: **2172** (app72 ile aynı seri)

## Notlar

⚠️ **Manuel Mod Aktif:** ForexFactory anti-bot koruması nedeniyle manuel veri kullanılıyor  
⚠️ **Veri Güncelleme:** `forexfactory/manual_data.py` dosyasını güncelleyin  
⚠️ **Auto Scraping:** Deneysel - 403 hatası alabilir  
📖 **Detaylı Kılavuz:** `USAGE_NEWS_CHECKER.md` dosyasına bakın

## Örnekler

### Örnek 1: ornek.csv

```bash
python3 -m app72_iou.cli ornek.csv
```

Output:
```
Ofs=-1 | 06-09 08:24 -> 09:36 | [HIG] USD Non-Farm Payrolls @ 8:30am
Ofs=+0 | 06-09 21:36 -> 22:48 | -
Ofs=+1 | 06-19 14:24 -> 15:36 | [MED] EUR Consumer Price Index @ 15:00
```

### Örnek 2: Web ile toplu işlem

1. Web arayüzünü başlat
2. Birden fazla CSV yükle
3. Hepsini işle
4. Sonuçları tek tek indir
