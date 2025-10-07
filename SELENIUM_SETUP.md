# 🚀 Selenium Setup - ForexFactory Otomatik Scraping

## 40 Haftalık Veriyi Tek Komutla İndirin!

### 1️⃣ Kurulum

```bash
# Selenium yükle
pip install selenium

# ChromeDriver yükle (Mac)
brew install chromedriver

# Linux için:
# sudo apt-get install chromium-chromedriver

# Windows için:
# https://chromedriver.chromium.org/downloads adresinden indirin
```

### 2️⃣ Toplu Veri İndirme

```bash
# 40 haftalık veriyi indir (cache'lenir, tekrar indirmez)
python3 -m forexfactory.cli --weeks 40

# Özel dosya adı ile
python3 -m forexfactory.cli --weeks 40 --output my_forex_data.json

# Belirli tarihten başla
python3 -m forexfactory.cli --weeks 20 --from 2025-01-01

# Sadece 1 hafta test için
python3 -m forexfactory.cli --weeks 1
```

### 3️⃣ Otomatik Kullanım

IOU news checker artık **otomatik olarak** Selenium kullanır:

```bash
# Artık hiçbir şey yapmanıza gerek yok!
python3 -m app72_iou.cli ornek.csv output.csv

# Web arayüzü de otomatik kullanır
python3 -m app72_iou.web
```

## ⚙️ Nasıl Çalışır?

### Cache Sistemi

1. **İlk çalıştırma:** ForexFactory'den çeker, `forexfactory/cache/` klasörüne kaydeder
2. **Sonraki çalıştırmalar:** Cache'den okur (7 gün geçerli)
3. **Güncelleme:** 7 gün sonra otomatik yeniden çeker

### Örnek İş Akışı

```bash
# 1. 40 haftalık veriyi bir kere çek (5-10 dakika sürer)
python3 -m forexfactory.cli --weeks 40

# 2. IOU analizlerini çalıştır (saniyeler sürer, cache kullanır)
python3 -m app72_iou.cli iou_week1.csv output1.csv
python3 -m app72_iou.cli iou_week2.csv output2.csv
python3 -m app72_iou.cli iou_week3.csv output3.csv
# ... 40 hafta boyunca
```

## 🎯 Avantajlar

✅ **Hızlı:** 40 hafta bir kez indirilir, sonrası cache  
✅ **Güvenilir:** Gerçek browser kullandığı için anti-bot bypass  
✅ **Otomatik:** Manuel veri girişine gerek yok  
✅ **Esnek:** İstediğiniz tarih aralığını seçin  

## 🐛 Sorun Giderme

### "chromedriver not found"

```bash
# Mac
brew install chromedriver

# Veya manuel indirin:
# https://chromedriver.chromium.org/downloads
# Chrome sürümünüzle eşleşen versiyonu indirin
```

### "Permission denied" (Mac)

```bash
# ChromeDriver'ı güvenilir yap
xattr -d com.apple.quarantine /usr/local/bin/chromedriver
```

### Selenium çalışmıyor

```bash
# Safari driver kullan (Mac'te built-in)
# Kod otomatik Safari'ye geçer
```

### Çok yavaş

```bash
# Daha az hafta ile başla
python3 -m forexfactory.cli --weeks 10

# Veya headless mode devre dışı (görmek için)
# selenium_scraper.py içinde headless=False yapın
```

### Cache'i temizle

```bash
# Cache klasörünü sil
rm -rf forexfactory/cache/

# Veya sadece eski dosyaları
find forexfactory/cache/ -mtime +7 -delete
```

## 📊 Veri Formatı

İndirilen JSON dosyası:

```json
[
  {
    "date": "Jun09",
    "time": "8:30am",
    "datetime": "2025-06-09T08:30:00",
    "currency": "USD",
    "impact": "High",
    "event": "Non-Farm Employment Change",
    "actual": "",
    "forecast": "190K",
    "previous": "177K"
  }
]
```

## 🔄 Güncelleme

Haftalık yeni veriler için:

```bash
# Her hafta başı yeni haftayı ekle
python3 -m forexfactory.cli --weeks 1 --from 2025-10-13
```

## 💡 Pro Tip

Cron job ile otomatik haftalık güncelleme:

```bash
# crontab -e
# Her Pazartesi sabah 8'de yeni haftayı çek
0 8 * * 1 cd /Users/malware/x1 && python3 -m forexfactory.cli --weeks 1
```

## 🎉 Sonuç

Artık **40 haftalık** veriyi:
- ✅ Tek komutla indirebilirsiniz
- ✅ Manuel giriş yok
- ✅ Her IOU analizi otomatik haberleri bulur
- ✅ Cache sayesinde hızlı

```bash
# Tek yapmanız gereken:
python3 -m forexfactory.cli --weeks 40

# Sonra normal kullanım:
python3 -m app72_iou.cli iou_files/*.csv
```

🚀 **Haydi başlayın!**
