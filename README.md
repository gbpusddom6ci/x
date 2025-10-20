# X1 Trading Platform

Bu proje, forex piyasalarında multi-timeframe analizi için tasarlanmış kapsamlı bir araç seti. Standart trading platformlarının ötesine geçerek, alışılmadık zaman dilimlerini kullanarak piyasa davranışlarını derinlemesine inceliyoruz. Özellikle 48, 72, 80 ve 120 dakikalık mumlar üzerinden yapılan analizler, büyük oyuncuların ve market maker'ların standart dışı pattern'lerini yakalamayı hedefliyor.

## Projenin Amacı ve Yaklaşımı

Geleneksel trading araçları genellikle 5 dakika, 15 dakika, 1 saat gibi standart timefram'lara odaklanır. Ancak X1, bu yaklaşımdan farklı olarak, piyasa dinamiklerini daha ince bir şekilde yakalamak için özel timefram'lar geliştiriyor. Temel hipotez, kurumsal yatırımcıların ve büyük sermayeli oyuncuların, standart timefram'ların dışında, matematiksel olarak anlamlı olan özel periyotlarda hareket ettiği yönünde.

Örneğin, Doji Candle (DC) formasyonları bu timefram'larda incelendiğinde, klasik analizlerde gözden kaçan dönüş noktaları ve destek/direnç seviyeleri ortaya çıkıyor. Proje, Elliott Wave teorisi, Fibonacci oranları ve custom sequence'ler gibi unsurları entegre ederek, hem manuel hem de otomatik analiz imkanı sağlıyor.

Bu araçlar, özellikle EURUSD, GBPUSD gibi major pair'lerde ve commodity currencies (AUD, NZD, CAD) için optimize edilmiş. Amacımız, trader'lara piyasa mikroyapısını anlamaları ve daha isabetli kararlar almaları için güçlü bir temel sunmak.

## Kurulum ve Başlangıç

### Sistem Gereksinimleri
- Python 3.8 veya üstü
- Flask (web framework için)
- Pandas ve NumPy (veri işleme için)
- Diğer bağımlılıklar requirements.txt'te listelenmiş

### Adım Adım Kurulum
1. Projeyi klonlayın veya indirin.
2. Sanal ortam oluşturun: `python -m venv venv`
3. Aktifleştirin: `source venv/bin/activate` (macOS/Linux) veya `venv\Scripts\activate` (Windows)
4. Bağımlılıkları yükleyin: `pip install -r requirements.txt`
5. Ana landing page'i başlatın: `python -m landing.web`

Tarayıcınızda `http://localhost:2000` adresine giderek tüm modüllere erişebilirsiniz. Her modül kendi port'unda çalışır ve landing page üzerinden linklenir.

## Modüllerin Detaylı Açıklaması

Proje, modüler bir yapıya sahip. Her modül, belirli bir timefram'a odaklanıyor ve bağımsız olarak çalıştırılabilir. Veri girişi olarak CSV formatında OHLC (Open, High, Low, Close) verileri kullanılıyor – MetaTrader, TradingView veya benzeri platformlardan export edilebilir.

### app48: 48 Dakikalık Analiz (Port: 2020)
48 dakika, 1 saatlik mumların %80'ine denk gelen bir periyot. Bu, 5-dalga Elliott pattern'inde 4. dalgayı temsil ediyor gibi düşünülebilir. Sistem, 12 dakikalık ham veriyi 4'lü gruplar halinde birleştirerek 48 dakikalık mumlar oluşturur.

Ana özellikler:
- Doji Candle tespiti: Gövde boyutu, toplam mum range'inin %10'undan küçükse DC olarak işaretlenir.
- S1 ve S2 sequence sayımı: Custom diziler (S1: 1,3,7,13,...; S2: 1,5,9,17,...) kullanılarak potansiyel reversal noktaları hesaplanır.
- Offset matrisi: -3'ten +3'e kadar zaman kaydırmalarıyla pattern analizi. Bu, farklı session geçişlerindeki (Asya-Londra-NY) davranışları yakalar.

EURUSD ve GBPUSD için ideal; DC kümelenmeleri güçlü destek seviyelerini gösterir.

### app72: 72 Dakikalık Analiz (Port: 2172)
72 dakika, günün (1440 dakika) tam 20'de biri. Matematiksel simetri sağladığı için intraday cycles'ı yakalamada etkili. 12 dakikalık veriden 6'lı gruplar oluşturur.

Özellikler:
- Offset tabanlı DC tarama: Her offset'te farklı piyasa döngüleri belirir.
- Session-aware analiz: Londra açılışı gibi kritik zamanlarda pattern'ler ön plana çıkar.
- Görselleştirme: Matris tabanlı heatmap'ler ile DC dağılımı gösterilir.

Bu timefram, trend continuation'ları doğrulamak için birebir.

### app80: 80 Dakikalık Analiz (Port: 2180)
80 dakika (1 saat 20 dakika), Fibonacci sayılarının (8x10) bir türevi. 20 dakikalık verilerden 4'lü gruplar halinde mumlar üretilir.

Uygulama alanı:
- Commodity pair'ler (AUDUSD, NZDUSD, USDCAD) için optimize.
- Emtia piyasalarının Asya session etkisini yakalar.
- DC istisnaları: Standart Doji kriterlerini aşan ama benzer davranış gösteren mumlar dahil edilir.

80 dakikalık döngüler, volatility spike'larını öngörmede yardımcı olur.

### app120: 120 Dakikalık (2 Saatlik) Analiz (Port: 2120)
Standart 2 saatlik timefram ama X1'in gelişmiş algoritmalarıyla zenginleştirilmiş. 60 dakikalık veriden 2'li gruplar oluşturur.

Ana yenilikler:
- Gelişmiş DC tanımı: Davranışsal Doji'ler (body < 0.1 * range).
- Offset sistemi: Economic news etkilerini farklı kaymalarda analiz eder.
- Sequence entegrasyonu: S1/S2 ile future projection'lar.

Kısa-orta vadeli swing trade'ler için mükemmel.

### app120_iov: IOV (Inverse OC Value) Analizi (Port: 2121)
Projenin en yenilikçi modülü. Inverse OC Value, bir mumun OC farkının (Open-Close), önceki mumun OC'sinin tersi yönde ve belirli bir threshold'un (örneğin 25 pip) üzerinde olması durumunu tanımlar.

Örnek:
- Önceki mum: OC = +20 pip (bullish)
- Mevcut mum: OC = -30 pip (bearish, threshold >25)

Bu formasyonlar, momentum reversal'larını işaret eder. 2 haftalık veri setleri üzerinde çalışır ve trade fırsatlarını listeler.

### app321: 60 Dakikalık Klasik Analiz (Port: 2019)
Standart 1 saatlik timefram için referans modül. X1 sequence'leri ve offset matrisiyle entegre, diğer timefram'larla karşılaştırma sağlar.

### news_converter: Haber Verisi Dönüştürücü (Port: 2199)
ForexFactory'den Markdown formatındaki economic calendar verilerini JSON'a dönüştürür.

Özellikler:
- Multi-file upload (1-10 dosya).
- Otomatik tarih/year detection ve timezone conversion.
- Zip export için hazır JSON output.
- Haber bazlı filtering: High-impact events için.

Bu modül, news trading stratejilerini destekler; diğer app'lerle entegre edilebilir.

### landing: Ana Dashboard (Port: 2000)
Tüm modüllere erişim sağlayan central hub. Tema: Uzay ve eğlenceli grafikler (penguenler, kediler). Her app'in status'unu gösterir ve direct link'ler sağlar.

## Teknik Mimari

### Veri İşleme
- CSV parsing: Farklı formatlar (comma, semicolon, tab) ve column varyasyonları (Time/Date, O/H/L/C) otomatik detect edilir.
- Mum aggregation: Ham tick/lower timeframe verilerinden custom mumlar oluşturulur.
- Sequence Sistemi: S1 (trend continuation: 1,3,7,13,21,31,43,57,73,91,111,133,157) ve S2 (reversal: 1,5,9,17,25,37,49,65,81,101,121,145,169). Bu diziler, Fibonacci-inspired pattern'lerden türetilmiş.
- Offset Mekanizması: Zaman kaydırmalarıyla alternatif senaryolar test edilir; trader timezone'larını simüle eder.

### DC (Doji Candle) Kriterleri
- |Open - Close| < (High - Low) * 0.1
- Bu, indecision mumlarını tanımlar ve reversal potansiyelini gösterir.

### Web Framework
Flask tabanlı, her app lightweight server olarak çalışır. Templates: Jinja2 ile dynamic charts (Matplotlib/Plotly entegrasyonu).

## Deployment ve Ölçekleme
- Docker: Multi-stage build ile production-ready image.
- Railway/Render/Heroku: Config dosyaları hazır (railway.toml, render.yaml, Procfile).
- Veri kaynakları: Local CSV'ler veya external feeds (gelecekte websocket support).

Örnek veriler: `apr13.csv`, `ornek80.csv` – test için kullanın.

## Geliştirme ve Gelecek Planlar
Proje, piyasa microstructure'ını anlamaya odaklanıyor. Modüller arası entegrasyonla, comprehensive backtesting mümkün.

Yakın gelecek:
- ML-based pattern recognition (LSTM/ clustering ile DC prediction).
- Real-time data feeds (WebSocket via broker APIs).
- Automated signal generation ve alert sistemi.
- Advanced backtesting suite ile strategy validation.

Bu araçlar, disiplinli trading'i teşvik eder – her zaman risk management'ı unutmayın.

## Lisans ve Katkı
Private repo, ticari kullanım için iletişime geçin. Açık kaynak katkılarını değerlendirebiliriz.

*"Piyasalar karmaşık, ama doğru araçlarla desenler belirginleşir."*