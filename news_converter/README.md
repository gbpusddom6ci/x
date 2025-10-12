# 📰 News Converter

Markdown formatından JSON formatına haber verisi dönüştürücü.

## 🚀 Kullanım

```bash
python3 -m news_converter.web --port 3000
```

Web arayüzü: http://127.0.0.1:3000/

## 📋 Özellikler

- **Markdown Parse**: ornek.md formatını otomatik parse eder
- **JSON Export**: Standart news_data/ formatında JSON üretir
- **Direkt Kayıt**: `news_data/` klasörüne tek tıkla kayıt
- **Download**: JSON dosyasını indir
- **Kopyala**: JSON'u clipboard'a kopyala
- **Batch İşlem**: Tek seferde tüm haberleri işle

## 📝 Markdown Formatı

```
Sun
Mar 30
9:30pm
CNY
Manufacturing PMI
50.5	50.4	50.2
CNY
Non-Manufacturing PMI
50.8	50.5	50.4
Mon
Mar 31
All Day
EUR
German Prelim CPI m/m
0.3%	0.3%	0.4%
8:30pm
AUD
Retail Sales m/m
0.2%	0.3%	0.3%
```

## 📊 JSON Çıktısı

```json
{
  "meta": {
    "source": "markdown_converter",
    "year": 2025,
    "total_days": 29,
    "total_events": 168,
    "date_range": "2025-03-30 -> 2025-05-03"
  },
  "days": [
    {
      "date": "2025-03-30",
      "weekday": "Sun",
      "events": [
        {
          "date": "2025-03-30",
          "weekday": "Sun",
          "time_label": null,
          "time_24h": "21:30",
          "currency": "CNY",
          "title": "Manufacturing PMI",
          "values": {
            "actual": "50.5",
            "forecast": "50.4",
            "previous": "50.2"
          }
        }
      ]
    }
  ]
}
```

## 🎯 Kullanım Senaryoları

1. **Yeni Haber Verisi Ekleme**:
   - Markdown formatını kopyala
   - Web arayüzüne yapıştır
   - "Convert to JSON" tıkla
   - "Save to news_data/" ile kaydet

2. **Toplu Güncelleme**:
   - Birden fazla dosya içeriğini birleştir
   - Tek seferde parse et
   - İndir ve manuel kontrol et

3. **Format Dönüştürme**:
   - Farklı kaynaklardan gelen verileri standart formata çevir
   - Otomatik validasyon

## ⚙️ Landing Page Entegrasyonu

Landing page'e otomatik eklendi:
```bash
python3 -m landing.web --port 2000 --news-converter-url http://127.0.0.1:3000/
```
