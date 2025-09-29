# Landing Page

Basit landing page, app48, app321 ve app120 web arayüzlerini tek ekranda listeler.

## Çalıştırma

```bash
python3 -m landing.web --host 0.0.0.0 --port 2000
```

Varsayılan linkler sırasıyla `http://127.0.0.1:2020/`, `http://127.0.0.1:2019/` ve `http://127.0.0.1:2120/` adreslerine yönlenir. Uygulamaları farklı portlarda çalıştırıyorsanız CLI parametreleriyle güncelleyebilirsiniz:

```bash
python3 -m landing.web \
  --app48-url "http://localhost:9000/" \
  --app321-url "http://localhost:9001/" \
  --app120-url "http://localhost:9002/"
```

Landing page yalnızca ilgili sayfaları bağlar; analizin çalışması için `python3 -m app48.web`, `python3 -m app321.web` ve `python3 -m app120.web` servislerinin açık olması gerekir.
