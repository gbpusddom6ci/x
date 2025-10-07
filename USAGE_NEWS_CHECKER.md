# ForexFactory News Checker - Kullanım Kılavuzu

## 🎯 Ne İşe Yarar?

IOU analiz çıktılarınızdaki her offset için:
- 72 dakikalık mum aralığını hesaplar
- O zaman aralığında ForexFactory'de Mid/High impact haber var mı kontrol eder
- Varsa yanına not ekler
- Yeni CSV dosyası oluşturur

## 🚀 Hızlı Başlangıç

### 1. Web Arayüzü (Tavsiye Edilen)

```bash
python3 -m app72_iou.web
```

Tarayıcıda: `http://localhost:2172`

**Adımlar:**
1. IOU CSV dosyanızı sürükle-bırak veya seç
2. Candle duration ayarla (varsayılan: 72 dakika)
3. "Check ForexFactory News" butonuna tıkla
4. Sonuçları görüntüle ve CSV indir

### 2. CLI Kullanımı

```bash
# Basit kullanım
python3 -m app72_iou.cli ornek.csv

# Output dosyası belirt
python3 -m app72_iou.cli ornek.csv ornek_with_news.csv

# Farklı candle duration
python3 -m app72_iou.cli input.csv output.csv 60
```

## 📊 Örnek

### Input (ornek.csv):
```
Ofs	Seq	Idx	Timestamp	OC	PrevOC	PIdx
-1	13	12	06-09 08:24	+0.07000	+0.10500	11
+0	21	23	06-09 21:36	+0.12400	+0.16700	22
```

### Output (ornek_with_news.csv):
```
Ofs,Seq,Idx,Timestamp,OC,PrevOC,PIdx,News
-1,13,12,06-09 08:24,+0.07000,+0.10500,11,[HIG] USD Non-Farm Employment Change @ 8:30am | [HIG] USD Unemployment Rate @ 8:30am
+0,21,23,06-09 21:36,+0.12400,+0.16700,22,-
```

## ⚙️ Nasıl Çalışır?

1. **Timestamp Parse:** `06-09 08:24` → DateTime (2025-06-09 08:24)
2. **Candle Range:** `08:24` + 72 dakika = `09:36`
3. **News Check:** 08:24 - 09:36 arasında haber var mı?
4. **Match:** NFP @ 8:30am → ✅ Aralıkta!
5. **Output:** News kolonu ekle

## 📝 Veri Kaynağı

### Manuel Mod (Şu an aktif)

ForexFactory anti-bot koruması nedeniyle manuel veri kullanıyoruz.

**Haberleri güncellemek için:**

1. `forexfactory/manual_data.py` dosyasını aç
2. `get_manual_events()` fonksiyonundaki event listesini güncelle
3. ForexFactory.com'dan haberleri manuel gir

**Örnek event:**
```python
{
    'date': 'Jun09',
    'time': '8:30am',
    'datetime': datetime(2025, 6, 9, 8, 30),
    'currency': 'USD',
    'impact': 'High',
    'event': 'Non-Farm Employment Change',
    'actual': '',
    'forecast': '190K',
    'previous': '177K'
}
```

### Auto Scraping Modu (Deneysel)

```python
from app72_iou.news_checker import check_iou_news

# Manuel data yerine scraping dene
results = check_iou_news('input.csv', use_manual_data=False)
```

⚠️ **Uyarı:** ForexFactory 403 hatası verebilir. Manuel mod daha güvenilir.

## 🔧 Özelleştirme

### Farklı Candle Duration

```bash
# 60 dakika için
python3 -m app72_iou.cli input.csv output.csv 60

# 48 dakika için
python3 -m app72_iou.cli input.csv output.csv 48
```

### Farklı Yıl

```python
from app72_iou.news_checker import check_iou_news

results = check_iou_news('input.csv', year=2024)
```

### Sadece Belirli Para Birimleri

`forexfactory/manual_data.py` içinde filtreleme:

```python
events = [e for e in all_events if e['currency'] in ['USD', 'EUR']]
```

## 🐛 Troubleshooting

### "No data found in CSV"
- CSV dosyası boş veya format hatalı
- Tab-delimited olduğundan emin olun
- İlk satırda başlık olmalı

### "Error parsing timestamp"
- Timestamp formatı: `MM-DD HH:MM` olmalı (örn: `06-09 08:24`)
- Yıl parametresini kontrol edin

### "403 Forbidden" (Scraping modu)
- ForexFactory anti-bot koruması
- Manuel mod kullanın: `use_manual_data=True`
- `forexfactory/manual_data.py` güncelle

### Haberler çıkmıyor
- `manual_data.py` dosyasını kontrol edin
- Tarih ve saat doğru mu?
- Timezone UTC-4 olmalı

## 📁 Dosya Yapısı

```
forexfactory/
  __init__.py
  scraper.py          # Auto scraping (deneysel)
  timezone_utils.py   # UTC-4 dönüşüm
  manual_data.py      # Manuel haber girişi ← BU DOSYAYI GÜNCELLEYİN

app72_iou/
  __init__.py
  news_checker.py     # Ana mantık
  cli.py              # Komut satırı aracı
  web.py              # Web arayüzü
  README.md
```

## 🎓 İleri Kullanım

### Python Script

```python
from app72_iou.news_checker import check_iou_news

# Temel kullanım
results = check_iou_news(
    iou_csv_path='input.csv',
    output_csv_path='output.csv',
    candle_minutes=72,
    year=2025,
    use_manual_data=True
)

# Sonuçları işle
for row in results:
    print(f"Offset {row['Ofs']}: {row['News']}")
```

### Toplu İşlem

```bash
# Tüm CSV dosyalarını işle
for file in *.csv; do
    python3 -m app72_iou.cli "$file" "${file%.csv}_with_news.csv"
done
```

## 📞 Destek

Sorularınız için:
1. `app72_iou/README.md` oku
2. `forexfactory/manual_data.py` örnek eventlere bak
3. Log çıktılarını kontrol et

## ✅ Checklist

- [ ] Kütüphaneler yüklü mü? (`pip install -r requirements.txt`)
- [ ] `manual_data.py` güncel mi?
- [ ] Input CSV formatı doğru mu?
- [ ] Timezone UTC-4 mü?
- [ ] Candle duration doğru mu? (72 dk)

Hazırsınız! 🚀
