# Proje Rehberi

Bu doküman app321, app48, app72, app80, app120 ve app120_iov uygulamalarının ortak kavramlarını ve uygulamaya özel kurallarını açıklar. Tüm açıklamalar Türkçe'dir ve en güncel davranışları yansıtır.

## Temel Kavramlar
- **Sayı dizileri:** Sayım işlemleri belirlenmiş sabit dizilere göre ilerler. Şu an desteklenen diziler:
  - **S1:** `1, 3, 7, 13, 21, 31, 43, 57, 73, 91, 111, 133, 157`
  - **S2:** `1, 5, 9, 17, 25, 37, 49, 65, 81, 101, 121, 145, 169`
- **Mum verisi:** Sayım için giriş olarak CSV dosyaları kullanılır. Her satır bir mumdur.
- **Timeframe:** app321 için 60 dakikalık, app48 için 48 dakikalık, app72 için 72 dakikalık, app80 için 80 dakikalık, app120 için 120 dakikalık mumlar işlenir.
- **Varsayılan başlangıç saati:** Tüm uygulamalar varsayılan olarak 18:00 mumundan saymaya başlar.

## CSV Formatı
Aşağıdaki başlıklar zorunludur (eş anlamlılar desteklenir):
```
Time, Open, High, Low, Close (Last)
```
Saat değerleri ISO veya yaygın tarih-saat formatlarında olabilir. CSV dosyaları yüklenmeden önce sıralanır.

## Distorted Candle (DC) Tanımı
Bir mumun Distorted Candle (DC) sayılması için üç şart bir önceki muma göre aynı anda sağlanmalıdır:
1. `High` değeri bir önceki mumun `High` değerini aşmamalı (eşit olabilir).
2. `Low` değeri bir önceki mumun `Low` değerinin altına düşmemeli (eşit olabilir).
3. `Close (Last)` değeri bir önceki mumun `Open` ve `Close` değerleri aralığında kapanmalıdır.

DC mumları normal sayımda atlanır. Ek olarak global kurallar:
- 18:00 (varsayılan başlangıç mumu) hiçbir koşulda DC sayılmaz.
- Ardışık iki DC oluşamaz; önceki mum DC ise sıradaki mum otomatik olarak normal mum kabul edilir.
- Sayım tablolarında her gerçek mum için iki değer raporlanır:
  - **OC:** İlgili mumun `Close - Open` farkı.
  - **PrevOC:** Bir önceki mumun `Close - Open` farkı (mümkün değilse `-`).
  Tahmini satırlarda OC/PrevOC değerleri `-` olarak gösterilir.

### İstisnai Kapsayıcı Kural
Sayım sırasında diziye ait bir adım bir DC mumuna denk gelirse, o adımın zamanı ilgili DC mumunun saati olarak kaydedilir. Bu eşleme yalnızca DC kuralı nedeniyle atlanması gereken mum tam olarak ilgili dizin adımını tamamlayacağı anda yapılır.

## Offset Mantığı
- Offset, varsayılan 18:00 başlangıç mumuna göre -3 ile +3 arasında seçilebilir (`-3, -2, -1, 0, +1, +2, +3`).
- Offset uygulanırken hedef zaman, **tabanda yakalanan 18:00 mumunun gerçek zamanından** dakikalık adımlar eklenerek hesaplanır. Bu yaklaşım, dizinin gün içinde kaymasını engeller.
- Hedef zaman aralık dışındaysa veya mumu eksikse:
  - Veri içinde hedefi karşılayan gerçek bir mum bulunursa sayım o mumdan başlatılır ve eksik adımların saatleri tahmini olarak `pred` etiketiyle gösterilir.
  - Veride hedef saatten önce mum yoksa, tüm değerler tahmini zamanlarla (`pred`) listelenir.
- Tahminler, ofset hedef zamanını temel alır; gerçek mum bulunduysa gerçek mumun normalleştirilmiş saati kullanılır.

## Zaman Dilimleri
- Kullanıcı girişinde iki seçenek vardır: `UTC-5` ve `UTC-4`.
- **Giriş UTC-5 ise**, çıktılar UTC-4'e kaydırılır (tüm mumlar +1 saat).
- **Giriş UTC-4 ise** herhangi bir zaman kaydırması yapılmaz.

## DC İstisna Saatleri
- **app321 (60m):** 13:00–20:00 aralığındaki DC mumları normal mum gibi sayılır.
- **app48 (48m):** 13:12–19:36 aralığındaki DC mumları normal mum gibi sayılır.
- **app72 (72m):** 
  - **18:00 mumu ASLA DC olamaz** (Pazar günü dahil - 2 haftalık veri için 2. hafta başlangıcı)
  - **Cuma 16:48 mumu ASLA DC olamaz** (2 haftalık veri için 1. hafta bitimindeki son mum)
  - **Pazar hariç, 19:12 ve 20:24 mumları DC olamaz** (günlük cycle noktaları)
  - **Hafta kapanış mumu (Cuma 16:00) DC olamaz**
- **app80 (80m):**
  - **Pazar hariç, 18:00, 19:20 ve 20:40 mumları DC olamaz** (günlük cycle noktaları: 18:00, 18:00+80dk, 18:00+160dk)
  - **Hafta kapanış mumu (Cuma 16:00) DC olamaz**
- **app120 (120m):** DC istisnası yoktur; tüm DC mumlar saatten bağımsız şekilde atlanır (kapsayıcı kural geçerli). Hafta kapanışı sayılan 16:00 mumları (ardından >120 dakikalık boşluk başlayanlar) DC kabul edilmez.

İstisna dışında kalan DC mumları sayımda atlanır ancak kapsayıcı kural gereği ilgili adımın zamanı olarak yazılabilir.

## Uygulama Ayrıntıları

### app321
- Başlangıç noktası: Verideki ilk 18:00 mumu (UTC-4 referansı). Offset seçimi hedef zamanı bu mumdan itibaren kaydırır.
- Sayım adımları seçilen diziye göre ilerler (varsayılan S2).
- Her ofset için gerçek mumlar gösterilir; eksik adımlar `pred` etiketiyle tahmin edilir.
- **DC Listesi:** Yüklenen veri için tespit edilen tüm DC mumları listelenebilir. Saatler giriş verisinin ilgili zaman diliminde gösterilir (UTC-5 girişi gelirse liste UTC-4'e kaydırılır).
- **Tahmin:** Veride bulunmayan adımlar için tahmini saat her zaman ana tabloda gösterilir; ek sekmeye gerek yoktur.
- **Matrix Sekmesi:** Tüm offset değerleri (-3..+3) için aynı tabloda saatler ve tahminler sunulur. DC'den kaynaklanan eşleşmeler tabloda `(DC)` etiketiyle belirtilir.

### app48
- 48 dakikalık mumlar kullanılır ve varsayılan başlangıç yine 18:00'dir.
- İlk sayım gününden sonraki her gün, piyasanın kapalı olduğu 18:00–19:36 aralığı için 18:00 ve 18:48 saatlerine yapay mumlar eklenir. Bu sayede sayım zinciri kesintiye uğramaz.
- DC kuralları ve offset davranışı app321 ile aynıdır; tek fark DC istisna saatlerinin 13:12–19:36 olmasıdır.
- Tahminler ve `pred` etiketi app321 ile aynı şekilde çalışır.
- **DC ve Matrix Listeleri:** app48 için de DC listesi ve matrix görünümü aynı mantıkla sunulur (48 dakikalık adımlar dikkate alınarak).
- **12m → 48m Converter:** app48 arayüzündeki yeni "12-48" sekmesi, UTC-5 12 dakikalık mumları UTC-4 48 dakikalık mumlara dönüştürür. Yüklenen veri önce +1 saat kaydırılır, ardından her gün 18:00'e hizalanan 48 dakikalık bloklar oluşturulur (18:00, 18:48, 19:36 ...). Her bloktaki close değeri bir sonraki bloğun open değerine eşitlenir; eğer bu değer bloktaki high/low sınırlarını aşıyorsa ilgili sınır close ile güncellenir. CSV çıktısında gereksiz sondaki sıfırlar kaldırılır.

### app72
- 72 dakikalık mumlar kullanılır; 18:00 başlangıç saati standart.
- **Sayım Mantığı:**
  - S1 ve S2 dizileri desteklenir (varsayılan S2).
  - Offset sistemi: -3 ile +3 arası (her adım 72 dakika).
  - **Özel DC Kuralları (2 Haftalık Veri İçin):**
    - **18:00 mumu ASLA DC olamaz** → Pazar günü dahil (ikinci hafta başlangıcı için kritik)
    - **Cuma 16:48 mumu ASLA DC olamaz** → Birinci hafta bitimindeki son mum (16:00 kapanıştan 12 dk önce)
    - **Pazar hariç 19:12 ve 20:24 DC olamaz** → Günlük cycle noktaları (18:00 + 72dk, 18:00 + 144dk)
    - **Cuma 16:00 (hafta kapanış) DC olamaz**
- **12m → 72m Converter (CLI: `python3 -m app72.main`):**
  - 12 dakikalık UTC-5 mumları alır, UTC-4 72 dakikalık mumlara dönüştürür.
  - Her 72 dakikalık mum 7 tane 12 dakikalık mumdan oluşur (7 × 12 = 84 ama offset mantığıyla 72 dakikaya düşer).
  - Hafta sonu boşluğu: Cumartesi mumları atlanır, Pazar 18:00'dan önce mumlar göz ardı edilir.
- **Web Arayüzü (`python3 -m app72.web`, port: 2172):**
  1. **Analiz:** 72m sayım, sequence/offset seçimi, OC/PrevOC, DC gösterimi.
  2. **DC List:** Tüm DC mumlarının listesi (2 haftalık veri kurallarına göre).
  3. **Matrix:** Tüm offset'ler (-3..+3) için tek ekranda özet tablo.
  4. **12→72 Converter:** 12m CSV yükle, 72m CSV indir.

### app80
- 80 dakikalık mumlar kullanılır; 18:00 başlangıç saati standart.
- **Sayım Mantığı:**
  - S1 ve S2 dizileri desteklenir (varsayılan S2).
  - Offset sistemi: -3 ile +3 arası (her adım 80 dakika).
  - **DC Kuralları:**
    - **Pazar hariç, 18:00, 19:20 ve 20:40 mumları DC olamaz** → Günlük cycle noktaları (18:00, 18:00+80dk, 18:00+160dk)
    - **Hafta kapanış mumu (Cuma 16:00) DC olamaz**
- **20m → 80m Converter (CLI: `python3 -m app80.main`):**
  - 20 dakikalık UTC-5 mumları alır, UTC-4 80 dakikalık mumlara dönüştürür.
  - Her 80 dakikalık mum 4 tane 20 dakikalık mumdan oluşur (4 × 20 = 80).
  - Hafta sonu boşluğu: Cumartesi mumları atlanır, Pazar 18:00'dan önce mumlar göz ardı edilir.
  - Dönüştürme sırasında: Open = ilk mumun open, Close = son mumun close, High = max(high), Low = min(low).
- **Web Arayüzü (`python3 -m app80.web`, port: 2180):**
  1. **Analiz:** 80m sayım, sequence/offset seçimi, OC/PrevOC, DC gösterimi.
  2. **DC List:** Tüm DC mumlarının listesi.
  3. **Matrix:** Tüm offset'ler (-3..+3) için tek ekranda özet tablo.
  4. **20→80 Converter:** 20m CSV yükle, 80m CSV indir.

### app120
- app321/app48 mantığındaki 120m sayımı ve 60→120 dönüştürücüyü tek pakette birleşik sunar.
- **Sayım (CLI: `python3 -m app120.counter`):**
  - 120 dakikalık mumları 18:00 başlangıcına göre sayar; DC istisnası yoktur.
  - OC/PrevOC bilgilerini aynı formatta raporlar; tahmin satırları `OC=- PrevOC=-` şeklinde etiketlenir.
- **Dönüştürücü (CLI: `python3 -m app120`):** 60m UTC-5 verisini UTC-4 120m mumlarına çevirir; gereksiz trailing sıfırları temizler. Cumartesi mumları ile Pazar 18:00 öncesi mumlar yok sayılır; Cuma 16:00 kapanışından sonra doğrudan Pazar 18:00 açılış mumuna geçilir.
- **Web Arayüzü (`python3 -m app120.web`, port: 2120):** Dört sekme içerir:
  1. **Analiz:** 120m sayım, OC/PrevOC, DC bilgileri.
  2. **DC List:** Tüm DC mumlarının listesi (UTC dönüşümü kullanılarak).
  3. **Matrix:** Tüm offset'ler için tek tabloda zaman/OC/PrevOC özetleri.
  4. **60→120 Converter:** 60m CSV yükleyip dönüştürülmüş 120m CSV indirme.

### app120_iov
- 🎯 **IOV (Inverse OC Value)** mum analizi için özel 120m timeframe uygulaması.
- **Amaç:** 2 haftalık 120m veride, OC ve PrevOC değerlerinin belirli bir limit değerinin üstünde ve zıt işaretli olduğu özel mumları tespit etmek.
- **IOV Mum Tanımı:** Aşağıdaki 3 kriteri **birden** karşılayan mumlardır:
  1. **|OC| ≥ Limit** → Mumun open-close farkı (mutlak değer) limit değerinin üstünde
  2. **|PrevOC| ≥ Limit** → Önceki mumun open-close farkı (mutlak değer) limit değerinin üstünde
  3. **Zıt İşaret** → OC ve PrevOC'den birinin pozitif (+), diğerinin negatif (-) olması
- **Filtrelenmiş Sequence Değerleri:**
  - **S1 için:** `7, 13, 21, 31, 43, 57, 73, 91, 111, 133, 157` (1 ve 3 analiz edilmez)
  - **S2 için:** `9, 17, 25, 37, 49, 65, 81, 101, 121, 145, 169` (1 ve 5 analiz edilmez)
- **Etkisiz Mum:** OC veya PrevOC'den herhangi biri limit değerinin altındaysa, o mum IOV analizi için etkisiz sayılır.
- **Analiz Kapsamı:**
  - Tüm offsetler taranır: -3, -2, -1, 0, +1, +2, +3 (toplam 7 offset)
  - Her offset için ayrı IOV mumları listelenir
  - 2 haftalık veri desteği: 1. hafta Pazar 18:00 → 2. hafta Cuma 16:00
- **CLI Kullanımı (`python3 -m app120_iov.counter`):**
  ```bash
  python3 -m app120_iov.counter --csv data.csv --sequence S2 --limit 0.1
  ```
  - `--csv`: 2 haftalık 120m CSV dosyası
  - `--sequence`: S1 veya S2 (varsayılan: S2)
  - `--limit`: IOV limit değeri (varsayılan: 0.1)
- **Web Arayüzü (`python3 -m app120_iov.web`, port: 2121):**
  - CSV dosyası yükleme (2 haftalık 120m data)
  - Sequence seçimi (S1/S2)
  - Limit değeri girişi
  - Tüm offsetler için IOV mum listesi
  - Her IOV mum için: Seq değeri, Index, Timestamp, OC, PrevOC
- **Örnek Çıktı:**
  ```
  Offset: 0
    Seq=31, Index=34, Time=2025-08-20 14:00:00
      OC: +0.15200, PrevOC: -0.16900
  ```
- **DC Hesaplama:** DC (Distorted Candle) hesaplaması mevcut app120 mantığı ile aynıdır; ancak IOV analizinde sadece sequence allocation için kullanılır, IOV kriterleri sadece OC/PrevOC değerlerine bakar.

## Özet
- Giriş CSV’si düzgün formatlanmış olmalı ve zorunlu kolonları içermelidir.
- Varsayılan başlangıç 18:00 mumu olup offset bu zaman üzerinden uygulanır.
- **DC Kuralları Özeti:**
  - **app321:** 13:00–20:00 DC istisna saatleri
  - **app48:** 13:12–19:36 DC istisna saatleri
  - **app72:** 18:00 (Pazar dahil) ve Cuma 16:48 ASLA DC olamaz; Pazar hariç 19:12 ve 20:24 DC olamaz
  - **app80:** Pazar hariç 18:00, 19:20, 20:40 DC olamaz
  - **app120:** DC istisnası yok, tüm DC'ler atılır
  - **app120_iov:** DC sadece sequence allocation için kullanılır, IOV kriterleri DC'den bağımsızdır
- 18:00 mumu genelde DC olamaz (app72'de Pazar dahil) ve ardışık iki DC bulunmaz.
- Her gerçek adım, mumun OC ve PrevOC değerleri ile birlikte raporlanır; tahmini satırlarda değerler `-` olarak gösterilir.
- Eksik veriler tahmini zamanlarla (`pred`) gösterilir.
- Tüm uygulamalar UTC-4/UTC-5 girişlerine uygun şekilde çıktı üretir.
- **Converter Özeti:**
  - **app48:** 12m → 48m (4 × 12m = 48m)
  - **app72:** 12m → 72m (7 × 12m ≈ 72m)
  - **app80:** 20m → 80m (4 × 20m = 80m)
  - **app120:** 60m → 120m (2 × 60m = 120m)
- **IOV Analizi (app120_iov):**
  - Filtrelenmiş sequence değerleri: S1 (1,3 hariç), S2 (1,5 hariç)
  - IOV kriteri: |OC| ≥ limit AND |PrevOC| ≥ limit AND zıt işaret
  - Tüm offsetler (-3..+3) taranır
  - 2 haftalık 120m veri desteği

Bu rehber, uygulamaların geliştirme ve kullanımında referans kabul edilmelidir.
