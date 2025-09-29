# Proje Rehberi

Bu doküman app321 ve app48 uygulamalarının ortak kavramlarını ve uygulamaya özel kurallarını açıklar. Tüm açıklamalar Türkçe'dir ve en güncel davranışları yansıtır.

## Temel Kavramlar
- **Sayı dizileri:** Sayım işlemleri belirlenmiş sabit dizilere göre ilerler. Şu an desteklenen diziler:
  - **S1:** `1, 3, 7, 13, 21, 31, 43, 57, 73, 91, 111, 133, 157`
  - **S2:** `1, 5, 9, 17, 25, 37, 49, 65, 81, 101, 121, 145, 169`
- **Mum verisi:** Sayım için giriş olarak CSV dosyaları kullanılır. Her satır bir mumdur.
- **Timeframe:** app321 için 60 dakikalık, app48 için 48 dakikalık mumlar işlenir.
- **Varsayılan başlangıç saati:** Her iki uygulama da varsayılan olarak 18:00 mumundan saymaya başlar.

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

### app120
- app321/app48 mantığındaki 120m sayımı ve 60→120 dönüştürücüyü tek pakette birleşik sunar.
- **Sayım (CLI: `python3 -m app120.counter`):**
  - 120 dakikalık mumları 18:00 başlangıcına göre sayar; DC istisnası yoktur.
  - OC/PrevOC bilgilerini aynı formatta raporlar; tahmin satırları `OC=- PrevOC=-` şeklinde etiketlenir.
- **Dönüştürücü (CLI: `python3 -m app120`):** 60m UTC-5 verisini UTC-4 120m mumlarına çevirir; gereksiz trailing sıfırları temizler. Cumartesi mumları ile Pazar 18:00 öncesi mumlar yok sayılır; Cuma 16:00 kapanışından sonra doğrudan Pazar 18:00 açılış mumuna geçilir.
- **Web Arayüzü (`python3 -m app120.web`):** Dört sekme içerir:
  1. **Analiz:** 120m sayım, OC/PrevOC, DC bilgileri.
  2. **DC List:** Tüm DC mumlarının listesi (UTC dönüşümü kullanılarak).
  3. **Matrix:** Tüm offset’ler için tek tabloda zaman/OC/PrevOC özetleri.
  4. **60→120 Converter:** 60m CSV yükleyip dönüştürülmüş 120m CSV indirme.

## Özet
- Giriş CSV’si düzgün formatlanmış olmalı ve zorunlu kolonları içermelidir.
- Varsayılan başlangıç 18:00 mumu olup offset bu zaman üzerinden uygulanır.
- DC’ler normalde atlanır (app321/app48 için belirtilen saat istisnaları geçerli, app120’de istisna yok). 18:00 hiçbir zaman DC olamaz ve ardışık iki DC bulunmaz.
- Her gerçek adım, mumun OC ve PrevOC değerleri ile birlikte raporlanır; tahmini satırlarda değerler `-` olarak gösterilir.
- Eksik veriler tahmini zamanlarla (`pred`) gösterilir.
- Tüm uygulamalar UTC-4/UTC-5 girişlerine uygun şekilde çıktı üretir.

Bu rehber, uygulamaların geliştirme ve kullanımında referans kabul edilmelidir.
