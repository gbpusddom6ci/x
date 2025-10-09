# Railway/Fly.io için optimize edilmiş Dockerfile
FROM python:3.11-slim

# Çalışma dizini
WORKDIR /app

# Python optimizasyonları
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8080

# Sistem bağımlılıkları (gerekirse)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Python bağımlılıklarını kopyala ve yükle
COPY requirements.txt .
RUN pip install -r requirements.txt

# Uygulama kodunu kopyala
COPY . .

# Port açıklama (Railway/Fly.io bu portu kullanacak)
EXPOSE $PORT

# Uygulamayı başlat - Railway'in PORT değişkenini kullan
CMD python -m appsuite.web --host 0.0.0.0 --port $PORT
