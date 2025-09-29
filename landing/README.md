# Landing Page

Basit landing page, app48, app72, app120 ve app321 web arayüzlerini tek ekranda listeler.

## Çalıştırma

```bash
python3 -m landing.web --host 0.0.0.0 --port 2000
```

Varsayılan linkler sırasıyla `http://127.0.0.1:2020/`, `http://127.0.0.1:2172/`, `http://127.0.0.1:2120/` ve `http://127.0.0.1:2019/` adreslerine yönlenir. Uygulamaları farklı portlarda çalıştırıyorsanız CLI parametreleriyle güncelleyebilirsiniz:

```bash
python3 -m landing.web \
  --app48-url "http://localhost:9000/" \
  --app72-url "http://localhost:9001/" \
  --app120-url "http://localhost:9002/" \
  --app321-url "http://localhost:9003/"
```

Landing page yalnızca ilgili sayfaları bağlar; analizin çalışması için `python3 -m app48.web`, `python3 -m app72.web`, `python3 -m app120.web` ve `python3 -m app321.web` servislerinin açık olması gerekir.
