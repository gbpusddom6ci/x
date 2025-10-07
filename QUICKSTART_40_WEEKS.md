# ⚡ 40 Haftalık ForexFactory Verisi - Hızlı Başlangıç

## 🎯 Problem
40 haftalık IOU analizi için ForexFactory haberlerini manuel girmek çok uzun.

## ✅ Çözüm
**Tek komutla 40 haftayı otomatik indir!**

---

## 📦 Adım 1: Kurulum (İlk kez)

```bash
# Selenium yükle
pip install selenium

# ChromeDriver yükle (Mac)
brew install chromedriver

# ChromeDriver'ı güvenilir yap (Mac)
xattr -d com.apple.quarantine /opt/homebrew/bin/chromedriver 2>/dev/null || true
```

**Linux:**
```bash
sudo apt-get install chromium-chromedriver
```

**Windows:**
[ChromeDriver indirin](https://chromedriver.chromium.org/downloads) ve PATH'e ekleyin.

---

## 🚀 Adım 2: 40 Haftalık Veriyi İndir

```bash
cd /Users/malware/x1

# 40 haftalık veriyi çek (5-10 dakika sürer, sadece bir kez)
python3 -m forexfactory.cli --weeks 40
```

**Ne olacak:**
- ✅ ForexFactory'den 40 haftalık Mid/High impact haberler çekilir
- ✅ `forexfactory/cache/` klasörüne kaydedilir
- ✅ Her hafta ayrı dosya (tekrar indirmeyi önler)
- ✅ 7 gün boyunca geçerli

---

## 📊 Adım 3: IOU Analizlerini Çalıştır

Artık **her IOU dosyası otomatik olarak** cache'den haberleri bulur:

```bash
# Tek dosya
python3 -m app72_iou.cli ornek.csv output.csv

# Birden fazla dosya
python3 -m app72_iou.cli iou_week1.csv output_week1.csv
python3 -m app72_iou.cli iou_week2.csv output_week2.csv
# ... 40 hafta boyunca

# Veya toplu:
for f in iou_*.csv; do
    python3 -m app72_iou.cli "$f" "${f%.csv}_with_news.csv"
done
```

**Hız:**
- İlk çalıştırma: 5-10 dakika (veri indirme)
- Sonraki çalıştırmalar: ~2-3 saniye (cache kullanır)

---

## 🌐 Adım 4: Web Arayüzü (Opsiyonel)

```bash
python3 -m app72_iou.web
# Tarayıcıda: http://localhost:2172
```

CSV yükle → Otomatik haber kontrolü → İndir

---

## 🔄 Güncelleme (Haftalık)

Yeni haftalar için:

```bash
# Her hafta yeni haftayı ekle
python3 -m forexfactory.cli --weeks 1
```

Veya otomatik güncelleme (cron):

```bash
# crontab -e
# Her Pazartesi sabah 8'de
0 8 * * 1 cd /Users/malware/x1 && python3 -m forexfactory.cli --weeks 1
```

---

## 📁 Cache Yapısı

```
forexfactory/cache/
├── ff_2024-12-01_2024-12-07.json  # Hafta 1
├── ff_2024-12-08_2024-12-14.json  # Hafta 2
├── ff_2024-12-15_2024-12-21.json  # Hafta 3
└── ... (40 hafta)
```

Her dosya o haftanın haberlerini içerir. 7 günden eski cache otomatik yenilenir.

---

## 🎯 Özet

| Adım | Komut | Süre | Sıklık |
|------|-------|------|--------|
| 1. Kurulum | `brew install chromedriver && pip install selenium` | 2 dk | Bir kez |
| 2. Veri İndir | `python3 -m forexfactory.cli --weeks 40` | 5-10 dk | Bir kez |
| 3. IOU Analiz | `python3 -m app72_iou.cli input.csv output.csv` | 2-3 sn | Her dosya |
| 4. Güncelleme | `python3 -m forexfactory.cli --weeks 1` | 20 sn | Haftalık |

---

## 💡 Pro Tips

### 1. Hız Testi

```bash
# Önce 1 hafta ile test et
python3 -m forexfactory.cli --weeks 1

# Çalışıyorsa 40 haftaya geç
python3 -m forexfactory.cli --weeks 40
```

### 2. Belirli Tarihten Başla

```bash
# 2025 başından itibaren 20 hafta
python3 -m forexfactory.cli --weeks 20 --from 2025-01-01
```

### 3. Cache'i Temizle

```bash
# Yeni baştan indir
rm -rf forexfactory/cache/
python3 -m forexfactory.cli --weeks 40
```

### 4. Sessiz Mod

```bash
# Log çıktısı azaltılmış
python3 -m forexfactory.cli --weeks 40 > /dev/null 2>&1
```

---

## 🐛 Sorun mu var?

### ChromeDriver bulunamadı
```bash
# Yüklü mü kontrol et
which chromedriver

# Yoksa:
brew install chromedriver  # Mac
```

### Permission denied (Mac)
```bash
xattr -d com.apple.quarantine /opt/homebrew/bin/chromedriver
```

### Selenium yok
```bash
pip install selenium
```

### Çok yavaş
- İnternet hızınızı kontrol edin
- Önce 10 hafta ile test edin
- Cache sistem çalışıyor mu: `ls -la forexfactory/cache/`

---

## ✅ Checklist

- [ ] Selenium yüklü (`pip list | grep selenium`)
- [ ] ChromeDriver yüklü (`which chromedriver`)
- [ ] İnternet bağlantısı var
- [ ] 40 hafta indirdim (`python3 -m forexfactory.cli --weeks 40`)
- [ ] Cache oluştu (`ls forexfactory/cache/`)
- [ ] IOU analizi çalışıyor (`python3 -m app72_iou.cli ornek.csv test.csv`)

---

## 🎉 Tamamdır!

Artık **40 haftalık** analiz için:
- ❌ Manuel veri girişi YOK
- ❌ Her seferinde indirme YOK
- ✅ Tek komut, tek seferlik indirme
- ✅ Sonrası otomatik ve hızlı

```bash
# Tek yapmanız gereken:
python3 -m forexfactory.cli --weeks 40

# Artık tüm IOU dosyalarınızı işleyebilirsiniz!
```

🚀 **Haydi başlayın!** Detaylar için: `SELENIUM_SETUP.md`
