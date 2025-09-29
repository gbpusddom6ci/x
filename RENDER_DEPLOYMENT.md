# Render.com'a Deployment Rehberi

Bu proje Render.com'a deploy edilmeye hazır hale getirilmiştir. İşte adım adım deployment süreci:

## Ön Hazırlık

✅ `requirements.txt` - Python bağımlılıkları
✅ `render.yaml` - Render deployment yapılandırması
✅ `.python-version` - Python sürümü belirteci

## Deployment Yöntemleri

### Yöntem 1: render.yaml ile Otomatik Deployment (Önerilen)

1. **Render.com'a Giriş Yapın**
   - https://render.com adresine gidin
   - GitHub/GitLab hesabınızla giriş yapın

2. **GitHub/GitLab'a Projeyi Push Edin**
   ```bash
   git add .
   git commit -m "Add render deployment config"
   git push origin main
   ```

3. **Render Dashboard'dan "New +" Butonuna Tıklayın**
   - "Blueprint" seçeneğini seçin
   - Repository'nizi seçin
   - `render.yaml` dosyası otomatik algılanacak
   - "Apply" butonuna tıklayın

4. **Deployment Başlayacak**
   - Build süreci otomatik olarak başlar
   - Logs'u takip edebilirsiniz
   - Deploy tamamlandığında size bir URL verilecek (örn: `https://candles-trading-suite.onrender.com`)

### Yöntem 2: Manuel Web Service Oluşturma

1. **Render Dashboard'dan "New +" > "Web Service" Seçin**

2. **Repository'yi Bağlayın**
   - GitHub/GitLab repository'nizi seçin

3. **Ayarları Yapılandırın:**
   - **Name:** `candles-trading-suite`
   - **Region:** Frankfurt (veya size yakın olan)
   - **Branch:** `main` (veya kullandığınız branch)
   - **Root Directory:** (boş bırakın - repository kökü)
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python -m appsuite.web --host 0.0.0.0 --port $PORT`
   - **Plan:** Free (veya istediğiniz plan)

4. **Environment Variables (Opsiyonel):**
   - `PYTHON_VERSION`: `3.11.0`

5. **Health Check:**
   - **Health Check Path:** `/health`

6. **"Create Web Service" Butonuna Tıklayın**

## Deployment Sonrası

### Uygulamanıza Erişim

Deploy tamamlandıktan sonra size verilen URL'den uygulamanıza erişebilirsiniz:

- **Ana Landing Page:** `https://your-app.onrender.com/`
- **app48:** `https://your-app.onrender.com/app48/`
- **app321:** `https://your-app.onrender.com/app321/`
- **app120:** `https://your-app.onrender.com/app120/`
- **Health Check:** `https://your-app.onrender.com/health`

### Free Plan Önemli Notlar

⚠️ **Render.com Free Plan'de dikkat edilmesi gerekenler:**

1. **Auto-Sleep:** 15 dakika hareketsizlikten sonra servis uyku moduna geçer. İlk istek 1-2 dakika sürebilir.
2. **750 Saat/Ay Limit:** Aylık 750 saat çalışma süresi limiti vardır.
3. **Build Time:** Her deployment yaklaşık 5-10 dakika sürebilir.

### Logs ve Monitoring

- Render dashboard'dan "Logs" sekmesinden canlı logları görüntüleyebilirsiniz
- "Metrics" sekmesinden CPU, Memory kullanımını takip edebilirsiniz
- "Events" sekmesinden deployment geçmişini görebilirsiniz

## Alternatif Deployment Seçenekleri

### Sadece Landing Page Deploy Etmek

Eğer sadece landing page'i deploy etmek isterseniz, `render.yaml` dosyasındaki yorumdan çıkarılmış alternatifi kullanın veya start command'i şöyle değiştirin:

```bash
python -m landing.web --host 0.0.0.0 --port $PORT
```

### Tek Bir Uygulama Deploy Etmek

Sadece app48, app321 veya app120'den birini deploy etmek için start command:

```bash
# app48 için:
python -m app48.web --host 0.0.0.0 --port $PORT

# app321 için:
python -m app321.web --host 0.0.0.0 --port $PORT

# app120 için:
python -m app120.web --host 0.0.0.0 --port $PORT
```

## Troubleshooting

### Build Hatası
- `requirements.txt` dosyasının doğru olduğundan emin olun
- Python version'ın uyumlu olduğunu kontrol edin

### Runtime Hatası
- Logs'u kontrol edin: Dashboard > Services > Your Service > Logs
- Port'un `$PORT` environment variable'ından alındığından emin olun
- `--host 0.0.0.0` parametresinin kullanıldığından emin olun

### 502 Bad Gateway
- Health check path'in doğru olduğundan emin olun
- Uygulamanın başarıyla başladığını logs'tan kontrol edin

## Custom Domain (Opsiyonel)

Kendi domain'inizi bağlamak için:
1. Render Dashboard > Your Service > Settings > Custom Domain
2. Domain'inizi ekleyin ve DNS kayıtlarını yapılandırın

## Otomatik Deployment

Her `git push` sonrası otomatik deploy için:
1. Render Dashboard > Your Service > Settings
2. "Auto-Deploy" seçeneğinin açık olduğundan emin olun

---

**İletişim ve Destek:**
- Render Docs: https://render.com/docs
- Render Community: https://community.render.com/
