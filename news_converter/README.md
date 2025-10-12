# News Converter

ForexFactory tarzı Markdown haber formatını JSON formatına dönüştürür.

## Özellikler

- ✅ **Çoklu dosya desteği**: 1-10 dosya tek seferde
- ✅ **Otomatik yıl tespiti**: Geçmiş ve gelecek tarihler otomatik algılanır
- ✅ **12→24 saat dönüşümü**: "2:30am" → "02:30"
- ✅ **Direkt indirme**: Tek dosya için .json, çoklu için .zip
- ✅ **Esnek parsing**: Farklı format varyasyonlarını destekler

## Kullanım

### Web Arayüzü

```bash
python3 -m news_converter.web
```

Tarayıcıda http://127.0.0.1:2199/ adresini açın.

### Komut Satırı (Python)

```python
from news_converter.parser import parse_markdown_to_json
import json

with open('3augto6sep.md', 'r') as f:
    md_content = f.read()

result = parse_markdown_to_json(md_content, '3augto6sep.md')

# JSON'a kaydet
with open('output.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=2, ensure_ascii=False)
```

## Girdi Formatı

Markdown dosyası ForexFactory tarzında olmalıdır:

```markdown
Sun
Aug 3
All Day
AUD		
Bank Holiday
Mon
Aug 4
2:30am
CHF		
CPI m/m
0.0%	-0.2%	0.2%	
```

## Çıktı Formatı

```json
{
  "meta": {
    "source": "markdown_import",
    "source_file": "3augto6sep.md",
    "assumptions": {
      "year": 2025,
      "time_zone": "UTC-4",
      "value_columns_order": ["actual", "forecast", "previous"]
    },
    "counts": {
      "days": 28,
      "events": 133
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
          "currency": "AUD",
          "title": "Bank Holiday",
          "time_label": "All Day",
          "time_24h": null,
          "values": {
            "actual": null,
            "forecast": null,
            "previous": null
          }
        }
      ]
    }
  ]
}
```

## Değer Parsing Kuralları

- **3 değer**: `actual`, `forecast`, `previous`
- **2 değer**: `actual`, `previous` (forecast `null`)
- **1 değer**: Yalnızca `actual`
- **0 değer**: Tüm değerler `null` (konuşmalar, açıklamalar)

## Port

- **Standalone**: 2199
- **appsuite içinde**: `/news` prefix ile

## Test

```bash
python3 test_news_converter.py
```

## Örnekler

Workspace'te mevcut örnek dosyalar:
- `3augto6sep.md` → geçmiş tarihler (Ağustos-Eylül)
- `2novto27dec.md` → gelecek tarihler (Kasım-Aralık)
