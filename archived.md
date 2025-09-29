--eski agents.md

/--/ 
## Proje tanımı ve terimler
bir sayı dizisi var, bir parite var(dxy), bir timeframe var, bir başlangıç noktası var, belirli sayı dizisi baz alınarak yapılan bir sayım var, sayım boyunca bazı istisnai kurallar var, mumlar var, sisteme yüklenecek bir CSV dosyası var, CSV' deki her bir satır bir mum temsil ediyor, her mum o alt projenin zaman dilimini temsil eder(48m, 60m, 120m vsvs.), Distorted Candle' lar var, sayımın başlangıcının ayarlanabileceği bir offset mantığı var, iki tame zaman dilimimiz var utc-4 ve utc-5,
#### CSV formatı:
"Time" "Open" "High" "Low" "Close (Last)"

#### DC tanımı: 

Distorted Candle' lar sayımda atlanır ve sayılmaz. Eğer özel sayı dizisindeki bir mum DC' ye denk gelirse o mumun saati alakalı muma yazılır. Örnek: 17. mum xx:xx saatindeki muma denk geliyor ve xx:xx saati mumu DC, bu durumda 17. mum xx:xx saatindeki DC mumuna yazılır.

"
bir önceki mumun high' ını asla aşmayacak, eşit olabilir.

bir önceki mumun low' undan aşağı asla düşmeyecek, eşit olabilir.

close(last) değeri bir önceki mumun open ve close değerlerinin arasında olacak, yani bir önceki mumun open ve close değerleri arasında kapanacak.

"

#### Offset mantığı

Sayımın varsayılan başlangıç noktasından -3 ve +3 aralığında ayarlanabilir başlangıç noktası seçme mantığıdır. "-3 -2 -1 0 +1 +2 +3 " 

örnek: varsayılan başlangıç noktası 18:00 ise, -2 seçildiğinde 16:00, +2 seçildiğinde 20:00 başlangıç noktası olur.

#### Belirlenmiş sayı dizileri: 
S1: "1, 3, 7, 13, 21, 31, 43, 57, 73, 91, 111, 133, 157" 
S2: "1, 5, 9, 17, 25, 37, 49, 65, 81, 101, 121, 145, 169"


#### Zaman dilimleri

UTC-4 ve UTC-5 zaman dilimleri var.
Sana yüklenen veriler çoğunlukla utc-5 olacak ama bazen utc-4 de olabilir o yüzden bir seçenek ekranı olmalı.
Sana utc-5 veri verildiği zaman bana utc-4' e çevirip vereceksin çıktıyı. 
utc-4 yüklendiğinde ise çıktının zaman dilimi ile oynama.

#### DC istisnası

Distorted Candle' lar 13:00 ve 20:00 saatleri arasında sayılır ve normal mum gibi davranılırlar. app321 için kurallar net ama app48 için bir açıklama yapayım; app48 için bu saatler 13:12 - 19:36 arasındadır. 

#### örnek app: app321
bu app yüklenen verideki en erken tarihteki 18:00 mumundan başlayarak 60 dakikalık zaman diliminde sayım yapıyor. 18:00 dan başlayarak 1(18:00), 2(19:00), 3(20:00) ... şeklinde sayıyor. S2 ile sayım yapıldığını varsayalım; 1. değer(1) 18:00, 2. değer(5) 22:00, 3. değer(9) 02:00, 4. değer(17) 10:00 şeklinde.

#### app48
DC mantığı aynı, Zaman Dilimi konusu aynı, diziler aynı, offset mantığı aynı, CSV Formatı aynı, başlangıç noktası 18:00 sabittir.
Bu app' in farkı 48m için olması, UTC-4 18:00' dan başlayacak ve 18:00, 18:48, 19:36 şeklinde sırayla sayacak app321 gibi. Bu app' deki ana fark, dayımın başladığı ilk gün hariç diğer günlerde piyasanın kapalı olduğu 18:00 - 19:36 arasına suni mum eklemenmesi. Piyasa kapanmadan önceki son mum 17:12 mum ile piyasanın açıldığı 19:36 mumu arasına suni mum eklenmesi buradaki olay. Yani 18:00 ve 18:48 mumları, 2 mum eklenecek araya.

#### app48 Distorted Candle List

app48' deki Distorted Candle' ları listele.


#### app321 Distorted Candle List

app321' deki Distorted Candle' ları listele.

#### app321 için prediction mantığı

app321' e tamamlanmamış bir veri yüklendiği senaryoda (örneğin yüklenen veride halihazırda sadece 25. mum verisi var ve 37. mum için veri yok) dizideki alakalı mumun o şartlara göre saat kaçta geleceğini gösteren bir ek yap. Bunu ayrı bir sekme olarak değil, direkt ana sekmenin içinde yetersiz veriye sahip mumlar için yap. Örneğin yüklenen veride 40 mumluk veri var ise 49. mumun saat kaça geleceğini gösteren bir ek yap tabloya.

#### app48 için prediction mantığı

app321' ün prediction mantığına göre tamamen aynı mantık.


#### istisnai bir kapsayıcı kural 

eğer sayım sırasında sayı dizisindeki bir sayı Distorted Candle' a denk gelirse bu sayıya Distorted Candle' ın saati yazılır.

#### app321 için matrix ekranı

bütün offsetlerin (-3, -2, -1, 0, +1, +2, +3) saatlerini ve predictionlarını görebileceğim bir app yapacaksın app321' e sekme olarak, adı "matrix" olacak. 


#### app48 için matrix ekranı

app48' e matrix ekranı yap. app321' deki gibi. 