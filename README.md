# X1 Trading Platform

Forex piyasalarında çoklu zaman dilimi (multi-timeframe) analizi için geliştirilmiş kapsamlı bir trading araç seti. Proje, standart olmayan zaman dilimlerinde mum analizi yaparak piyasa davranışlarını farklı açılardan inceleme imkanı sunuyor.

## Proje Hakkında

Çoğu trading platformu standart zaman dilimlerini (5m, 15m, 1H, 4H vs.) kullanırken, X1 farklı bir yaklaşım benimsiyor. 48, 72, 80 ve 120 dakikalık özel zaman dilimlerinde analiz yaparak, klasik göstergelerin yakalayamadığı pattern'leri ortaya çıkarıyor. 

Bu yaklaşımın temelinde, piyasa maker'ların ve büyük oyuncuların standart dışı zaman dilimlerinde hareket ettiği hipotezi yatıyor. Özellikle Doji mum formasyonlarının (DC - Doji Candle) bu zaman dilimlerindeki dağılımı, potansiyel dönüş noktalarını işaret edebiliyor.

## Kurulum ve Çalıştırma

### Gereksinimler

- Python 3.8+
- Flask web framework
- CSV işleme kütüphaneleri

### Hızlı Kurulum

```bash
# Bağımlılıkları yükle
pip install -r requirements.txt

# Ana sayfayı başlat
python3 -m landing.web
```

Tarayıcınızda `http://localhost:2000` adresine giderek tüm araçlara erişebilirsiniz.

## Uygulama Detayları

### app48 - 48 Dakikalık Analiz
**Port:** 2020

48 dakikalık zaman dilimi, 1 saatlik (60m) mumların %80'ine denk geliyor. Bu oran, piyasadaki 5-dalga Elliott yapısının 4. dalgasına karşılık geliyor. Uygulama, 12 dakikalık veriyi 48 dakikalık mumlara dönüştürüyor (4x12=48). 

Özellikle EURUSD ve GBPUSD gibi majör paritlerde, 48 dakikalık DC (Doji Candle) oluşumları önemli destek/direnç seviyelerini gösteriyor. S1 ve S2 sequence'larında sayım yaparak, Fibonacci benzeri bir yaklaşımla gelecek muhtemel dönüş noktalarını tahmin ediyor.

### app72 - 72 Dakikalık Analiz  
**Port:** 2172

72 dakika, günün tam 20'de birine denk geliyor (1440/72=20). Bu matematiksel uyum, gün içi döngülerin yakalanmasını sağlıyor. Sistem, 12 dakikalık veriden 6'lı gruplar halinde 72 dakikalık mumlar oluşturuyor.

DC analizi ve offset matrisi sayesinde, -3'ten +3'e kadar olan zaman kaymalarında pattern arayışı yapıyor. Her offset'te farklı bir piyasa döngüsü ortaya çıkıyor. Özellikle Asya-Londra-New York session geçişlerinde bu offsetler kritik öneme sahip.

### app80 - 80 Dakikalık Analiz
**Port:** 2180

80 dakika = 1 saat 20 dakika. Bu zaman dilimi, Fibonacci sayılarından 8 ve 10'un çarpımı. 20 dakikalık verilerden 4'lü gruplar halinde dönüştürme yapıyor. 

Bu zaman dilimi özellikle commodity para birimlerinde (AUD, NZD, CAD) daha anlamlı sonuçlar veriyor. Çünkü bu paritelerde emtia piyasaları ve Asya seansının etkisi 80 dakikalık döngülerde kendini gösteriyor.

### app120 - 2 Saatlik Analiz
**Port:** 2120

Klasik 2 saatlik (120 dakika) analiz ama farklı bir bakış açısıyla. DC istisnası sistemi, standart Doji tanımının dışına çıkan ama davranışsal olarak Doji karakteri gösteren mumları yakalıyor. 

60 dakikalık veriden 2'li gruplar oluşturuyor. Offset sistemi sayesinde, major ekonomik veri açıklamalarının etkisini farklı zaman dilimlerinde gözlemleyebiliyorsunuz.

### app120_iov - IOV Mum Analizi
**Port:** 2121

IOV (Inverse OC Value) analizi, bu projenin en özgün özelliklerinden biri. Bir mumun açılış-kapanış farkının (OC), bir önceki mumun OC değeriyle ters yönde ve belirli bir limitin üzerinde olması durumunu arıyor.

Örneğin:
- Önceki mum: Açılış 1.1000, Kapanış 1.1020 (OC = +20 pip)
- Mevcut mum: Açılış 1.1020, Kapanış 1.0990 (OC = -30 pip)

Eğer limit 25 pip ise, bu bir IOV mumu oluyor. Bu formasyonlar genelde güçlü momentum değişimlerini işaret ediyor. 2 haftalık veri üzerinde çalışarak, kısa-orta vadeli trade fırsatlarını yakalıyor.

### app321 - 60 Dakikalık Klasik Analiz
**Port:** 2019

Standart 1 saatlik analiz ama X1'in özel sayım algoritmasıyla. DC listesi ve offset matrisi, klasik timeframe'de bile farklı pattern'ler ortaya çıkarıyor. Diğer özel timeframe'lerle karşılaştırma yapabilmek için eklendi.

### news_converter - Haber Verisi Dönüştürücü
**Port:** 2199

ForexFactory'den alınan ekonomik takvim verilerini (Markdown formatında) JSON'a dönüştürüyor. Birden fazla dosyayı aynı anda işleyebiliyor ve zip olarak indirme imkanı sunuyor.

Özellikleri:
- Otomatik yıl tespiti (geçmiş/gelecek tarihler)
- Çoklu dosya desteği (1-10 dosya)
- Temiz JSON çıktısı
- Timezone dönüşümleri

Bu veriyi diğer uygulamalarla entegre ederek, haber bazlı trading stratejileri geliştirilebiliyor.

### landing - Ana Kontrol Paneli
**Port:** 2000

Tüm uygulamalara tek noktadan erişim sağlayan ana sayfa. Uzay temalı, interaktif bir arayüzle tüm araçları listiyor. Her uygulamanın kendi görsel teması var (penguenler, kediler, manzaralar vs.) - biraz eğlenceli bir dokunuş.

## Teknik Detaylar

### Sequence Sistemi

Projede iki temel sequence kullanılıyor:

**S1:** 1, 3, 7, 13, 21, 31, 43, 57, 73, 91, 111, 133, 157  
**S2:** 1, 5, 9, 17, 25, 37, 49, 65, 81, 101, 121, 145, 169

Bu sayılar rastgele değil - her biri belirli bir matematiksel pattern'i takip ediyor. S1 genelde trend devamı, S2 ise dönüş noktaları için kullanılıyor.

### Offset Sistemi

-3'ten +3'e kadar olan offset değerleri, zaman kaydırması anlamına geliyor. Örneğin:
- Offset 0: Normal sayım
- Offset +1: Bir mum ileri kaydırılmış sayım  
- Offset -2: İki mum geri kaydırılmış sayım

Bu sistem, farklı timezone'lardaki trader'ların davranışlarını yakalamaya yarıyor.

### DC (Doji Candle) Tanımı

Bir mumun Doji sayılması için:
- |Open - Close| < (High - Low) * 0.1
- Yani gövde, toplam mum boyutunun %10'undan küçük olmalı

Bu mumlar kararsızlığı ve potansiyel dönüş noktalarını gösteriyor.

### CSV Format Esnekliği

Sistem, farklı broker'lardan gelen CSV formatlarını otomatik olarak tanıyor:
- Time, Timestamp, Date, DateTime
- Open, O, Open (First)
- High, H
- Low, L
- Close, C, Close (Last), Last

Virgül, noktalı virgül veya tab ile ayrılmış dosyaları okuyabiliyor.

## Deployment

Proje Railway, Render ve Docker üzerinde çalışacak şekilde yapılandırılmış:

- **Dockerfile:** Multi-stage build ile optimize edilmiş container
- **railway.toml:** Railway.app deployment config
- **render.yaml:** Render.com deployment config  
- **Procfile:** Heroku-style deployment

Landing page otomatik olarak diğer servislere yönlendirme yapıyor.

## Veri Kaynakları

- **CSV Verileri:** MetaTrader, TradingView veya diğer platformlardan export edilmiş OHLC verisi
- **Haber Verileri:** ForexFactory ekonomik takvimi (MD formatında)
- Örnek veri dosyaları: `apr13.csv`, `ornek80.csv`

## Geliştirme Notları

Bu proje, klasik teknik analiz yaklaşımlarının ötesinde, piyasa mikroyapısını anlamaya odaklanıyor. Standart olmayan zaman dilimleri kullanarak, kurumsal oyuncuların gözden kaçırdığı veya kasıtlı olarak gizlediği pattern'leri ortaya çıkarmayı hedefliyor.

Her uygulama modüler yapıda - kendi web sunucusu, veri işleme ve analiz katmanları var. Bu sayede bağımsız olarak geliştirilebilir ve ölçeklenebilirler.

Gelecek planlar:
- Makine öğrenmesi entegrasyonu (pattern recognition)
- Gerçek zamanlı veri akışı
- Otomatik trading sinyalleri
- Backtesting modülü

## Lisans ve İletişim

Proje şu anda private repository'de geliştiriliyor. Ticari kullanım için iletişime geçin.

---

*"Piyasalar kaotik görünür ama kendi içinde bir düzeni vardır. O düzeni standart araçlarla bulamazsınız."*