# News Data Directory

Bu klasör IOU analizi için haber verilerini içerir.

## Kullanım

1. **news_converter** ile MD dosyalarını JSON'a çevir
2. Çıkan JSON dosyalarını bu klasöre koy
3. IOU analizi otomatik olarak bu klasördeki tüm JSON dosyalarını okur

## Dosya Formatı

JSON dosyaları şu formatta olmalıdır:

```json
{
  "meta": {
    "source": "markdown_import",
    "assumptions": {
      "year": 2025,
      "time_zone": "UTC-4"
    }
  },
  "days": [
    {
      "date": "2025-08-03",
      "weekday": "Sun",
      "events": [
        {
          "date": "2025-08-03",
          "weekday": "Sun",
          "currency": "USD",
          "title": "Event Title",
          "time_label": "10:00am",
          "time_24h": "10:00",
          "values": {
            "actual": "50.1",
            "forecast": "51.5",
            "previous": "50.8"
          }
        }
      ]
    }
  ]
}
```

## Destekleyen Uygulamalar

Aşağıdaki uygulamalar bu klasördeki haber verilerini IOU analizi için kullanır:

- ✅ **app48** - IOU sekmesi
- ✅ **app72** - IOU sekmesi
- ✅ **app80** - IOU sekmesi
- ✅ **app120** - IOU sekmesi
- ✅ **app321** - IOU sekmesi

## Otomatik Algılama

Tüm `.json` uzantılı dosyalar otomatik olarak yüklenir ve birleştirilir. Dosya isimleri önemli değil, içerik otomatik olarak tarih bazında organize edilir.

## Örnek Dosya İsimleri

```
news_data/
├── 3augto6sep.json          # Ağustos-Eylül haberleri
├── 2novto27dec.json         # Kasım-Aralık haberleri
├── jan2025.json             # Ocak haberleri
└── README.md                # Bu dosya
```

## Yenileme

Yeni haber verisi eklemek için:

1. news_converter'dan yeni JSON dosyası al
2. Bu klasöre kopyala
3. Uygulamayı yenile (otomatik algılar)

## Notlar

- Dosyalar otomatik birleştirilir, çakışma olmaz
- Aynı gün için birden fazla event olabilir
- Timezone varsayılanı UTC-4
- All Day eventler için time_24h null olabilir
