# app120_iov - IOV Candle Analysis

**IOV (Inverse OC Value)** mum analizi için özel 120m timeframe uygulaması.

## IOV Mum Nedir?

IOV mumu, aşağıdaki **3 kriteri birden** karşılayan özel mumlardır:

1. **|OC| ≥ Limit** - Mumun open-close farkı limit değerinin üstünde olmalı
2. **|PrevOC| ≥ Limit** - Önceki mumun open-close farkı limit değerinin üstünde olmalı
3. **Zıt İşaret** - OC ve PrevOC'nin işaretleri zıt olmalı (biri + biri -)

## 📋 Özellikler

- ✅ S1 ve S2 sequence desteği
- ✅ Filtrelenmiş sequence değerleri:
  - **S1:** 7, 13, 21, 31, 43, 57, 73, 91, 111, 133, 157 (1, 3 hariç)
  - **S2:** 9, 17, 25, 37, 49, 65, 81, 101, 121, 145, 169 (1, 5 hariç)
- ✅ Tüm offsetler taranır (-3 ile +3 arası)
- ✅ Özelleştirilebilir limit değeri
- ✅ 2 haftalık veri desteği (1. hafta Pazar → 2. hafta Cuma)

## 🚀 Kullanım

### CLI (Command Line):

```bash
python3 -m app120_iov.counter --csv data.csv --sequence S2 --limit 0.1
```

**Parametreler:**
- `--csv`: 2 haftalık 120m CSV dosyası
- `--sequence`: S1 veya S2 (varsayılan: S2)
- `--limit`: IOV limit değeri (varsayılan: 0.1)

### Web Arayüzü:

```bash
python3 -m app120_iov.web --port 2121
```

Tarayıcıda açın: http://localhost:2121

## 📊 Örnek Çıktı

```
Offset: 0
  Seq=31, Index=34, Time=2025-08-20 14:00:00
    OC: +0.15200, PrevOC: -0.16900

Offset: +1
  Seq=43, Index=50, Time=2025-08-21 20:00:00
    OC: -0.08200, PrevOC: +0.12500
```

## 📂 Veri Formatı

CSV dosyası şu başlıkları içermelidir:
```
Time, Open, High, Low, Close (Last)
```

**Örnek:**
```csv
Time,Open,High,Low,Close (Last)
2025-08-17 18:00:00,97.344,97.396,97.296,97.392
2025-08-17 20:00:00,97.392,97.402,97.382,97.398
...
```

## 🔍 Analiz Mantığı

1. Her offset için (-3..+3) ayrı analiz yapılır
2. Sadece filtrelenmiş sequence değerleri incelenir
3. Her sequence değerinde:
   - OC = candle.close - candle.open
   - PrevOC = prev_candle.close - prev_candle.open
4. Eğer |OC| < limit **VEYA** |PrevOC| < limit → **Etkisiz**
5. Eğer OC ve PrevOC aynı işaretteyse → **Etkisiz**
6. Aksi halde → **IOV Mum!** 🎯

## 💡 Örnek Senaryo

**Limit: 0.1**

| Seq | OC      | PrevOC  | Durum     | Sebep                            |
|-----|---------|---------|-----------|----------------------------------|
| 7   | +0.031  | +0.001  | Etkisiz   | İkisi de 0.1'den küçük          |
| 13  | +0.095  | -0.023  | Etkisiz   | İkisi de 0.1'den küçük          |
| 21  | +0.003  | +0.060  | Etkisiz   | İkisi de 0.1'den küçük          |
| 31  | +0.152  | -0.169  | **IOV**   | ✅ İkisi de limit üstü + zıt işaret |
| 43  | -0.030  | -0.014  | Etkisiz   | İkisi de 0.1'den küçük          |

## 🏗️ Proje Yapısı

```
app120_iov/
├── __init__.py       # Package init
├── counter.py        # IOV analiz mantığı (CLI)
├── web.py            # Web arayüzü
└── README.md         # Bu dosya
```

## 🔗 İlgili Uygulamalar

- **app120**: Standart 120m sayım uygulaması
- **app72**: 72m timeframe
- **app80**: 80m timeframe
- **app48**: 48m timeframe

## 📝 Notlar

- DC (Distorted Candle) hesaplaması mevcut sistemle aynı
- Hafta sonu boşluğu otomatik yönetilir (Cuma 16:00 → Pazar 18:00)
- Prediction desteği yok (sadece gerçek mumlar analiz edilir)
