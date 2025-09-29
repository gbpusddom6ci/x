# Fly.io Deployment Rehberi 🚀

## 🎯 Neden Fly.io?

- ✅ **Sleep yok** - 24/7 aktif kalır
- ✅ **3 VM ücretsiz** - Küçük projeler için ideal
- ✅ **Çok hızlı** - Global edge network
- ✅ **Amsterdam datacenter** - Türkiye'ye yakın
- ✅ **Otomatik SSL** - HTTPS dahil

---

## 📋 Ön Hazırlık

Oluşturulan dosyalar:
- ✅ `fly.toml` - Fly.io yapılandırması
- ✅ `Dockerfile` - Container image
- ✅ `.dockerignore` - Gereksiz dosyaları hariç tut
- ✅ `requirements.txt` - Python bağımlılıkları

---

## 🔧 Adım 1: Fly.io CLI Kurulumu

### macOS (Homebrew ile - Önerilen):

```bash
brew install flyctl
```

### Alternatif (curl ile):

```bash
curl -L https://fly.io/install.sh | sh
```

Kurulum sonrası terminal'i yeniden başlatın veya:

```bash
# Shell'inize göre:
source ~/.zshrc  # zsh kullanıyorsanız
source ~/.bashrc # bash kullanıyorsanız
```

### Kurulumu kontrol edin:

```bash
flyctl version
```

---

## 🔑 Adım 2: Fly.io Hesabı Oluşturma ve Giriş

### Yeni hesap oluşturun:

```bash
fly auth signup
```

Bu komut tarayıcınızı açacak ve kayıt formunu gösterecek.

### Veya mevcut hesabınıza giriş yapın:

```bash
fly auth login
```

**ÖNEMLİ:** Fly.io ücretsiz plan için **kredi kartı gerektirir** (doğrulama amaçlı).
Ancak ücretsiz limitlerin içinde kalırsanız **hiçbir ücret alınmaz**.

---

## 🚀 Adım 3: Uygulamayı Deploy Etme

### Proje dizinine gidin:

```bash
cd /Users/malware/candles
```

### İlk deployment (otomatik setup):

```bash
fly launch
```

Bu komut:
1. Mevcut `fly.toml` dosyasını algılayacak
2. Size birkaç soru soracak:

**Sorular ve Cevaplar:**

```
? Choose an app name: (candles-trading-suite veya boş bırakın - otomatik isim)
> candles-trading-suite

? Choose a region for deployment: 
> Amsterdam, Netherlands (ams) - Türkiye'ye en yakın

? Would you like to set up a Postgresql database?
> No (CSV dosyaları kullanıyorsunuz)

? Would you like to set up an Upstash Redis database?
> No

? Would you like to deploy now?
> Yes
```

### Deploy başlayacak! 🎉

Build süreci 2-5 dakika sürebilir. İlerlemeyi terminal'de görebilirsiniz.

---

## ✅ Adım 4: Deployment Sonrası

### Uygulamanızın durumunu kontrol edin:

```bash
fly status
```

### Canlı logları görüntüleyin:

```bash
fly logs
```

### Uygulamanızı açın:

```bash
fly open
```

Bu komut tarayıcınızda uygulamanızı açar:
- URL format: `https://candles-trading-suite.fly.dev`

---

## 🌐 Erişim URL'leri

Deploy sonrası uygulamanıza şu adreslerden erişebilirsiniz:

- **Ana Landing Page:** `https://your-app.fly.dev/`
- **app48:** `https://your-app.fly.dev/app48/`
- **app321:** `https://your-app.fly.dev/app321/`
- **app120:** `https://your-app.fly.dev/app120/`
- **Health Check:** `https://your-app.fly.dev/health`

---

## 🔄 Güncelleme ve Yeniden Deploy

Kod değişikliği yaptıktan sonra:

```bash
git add .
git commit -m "Update application"

# Fly.io'ya deploy
fly deploy
```

**Not:** Git push'a gerek yok, doğrudan `fly deploy` komutu yeterli!

---

## 📊 Yararlı Komutlar

```bash
# Dashboard'u aç (web arayüzü)
fly dashboard

# SSH ile makineye bağlan
fly ssh console

# Secrets/Environment variables ekle
fly secrets set SECRET_KEY=your-secret-value

# VM'leri listele
fly machines list

# Uygulamayı durdur
fly apps destroy candles-trading-suite

# Metrics ve monitoring
fly status
```

---

## 💰 Ücretsiz Limit Bilgileri

**Fly.io Free Tier:**

- ✅ **3 shared-cpu-1x VM** (256 MB RAM)
- ✅ **160 GB outbound transfer/ay**
- ✅ **3 GB persistent volumes** (opsiyonel)
- ✅ Sınırsız SSL sertifikası

**Sizin kullanımınız:**
- 1 VM kullanıyorsunuz (256 MB)
- Auto-stop kapalı, auto-start açık
- Tamamen ücretsiz limit içinde! 🎉

---

## 🔧 Troubleshooting

### Build hatası alırsanız:

```bash
# Logs'u kontrol edin
fly logs

# Local'de Docker build test edin
docker build -t candles-test .
docker run -p 8080:8080 candles-test
```

### Port sorunu:

`fly.toml` dosyasında `internal_port = 8080` olduğundan emin olun.

### Memory sorunu:

Eğer 256 MB yetmezse, `fly.toml` dosyasında:

```toml
[[vm]]
  memory_mb = 512  # 256'dan 512'ye çıkarın
```

**Not:** 512 MB hala ücretsiz limitte!

### CSV dosyaları erişilemiyor:

CSV dosyaları image'a dahil ediliyor. Eğer sorun varsa:
- `.dockerignore` dosyasını kontrol edin
- CSV dosyalarının exclude edilmediğinden emin olun

---

## 🌍 Custom Domain (Opsiyonel)

Kendi domain'inizi bağlamak için:

```bash
# Domain ekle
fly certs add yourdomain.com

# DNS kayıtlarını göster
fly certs show yourdomain.com
```

DNS ayarlarınıza:
```
A     @     <Fly.io IP adresi>
AAAA  @     <Fly.io IPv6 adresi>
```

---

## 🔐 Güvenlik İpuçları

1. **Secrets için fly secrets kullanın:**
   ```bash
   fly secrets set API_KEY=your-key
   ```

2. **Environment variables:**
   - `fly.toml` dosyasında `[env]` bölümüne ekleyin
   - Veya `fly secrets set` kullanın (hassas veriler için)

3. **HTTPS otomatik aktif** - Ekstra ayar gerekmez

---

## 📝 Sonraki Adımlar

1. **Git'e commit edin:**
   ```bash
   git add fly.toml Dockerfile .dockerignore FLY_DEPLOYMENT.md
   git commit -m "Add Fly.io deployment configuration"
   ```

2. **Deploy edin:**
   ```bash
   fly launch
   ```

3. **Tadını çıkarın!** 🎉

---

## 📚 Ek Kaynaklar

- **Fly.io Docs:** https://fly.io/docs/
- **Pricing:** https://fly.io/docs/about/pricing/
- **Status Page:** https://status.flyio.net/

---

## 🆘 Yardım

Sorun yaşarsanız:
1. `fly logs` ile logları kontrol edin
2. `fly doctor` ile sistem kontrolü yapın
3. Fly.io Community: https://community.fly.io/

Başarılar! 🚀
