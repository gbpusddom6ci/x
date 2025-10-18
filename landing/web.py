from __future__ import annotations

from http.server import HTTPServer, BaseHTTPRequestHandler
import argparse
import html
from typing import Dict


def build_html(app_links: Dict[str, Dict[str, str]]) -> bytes:
    import os, base64, math

    def b64_image(filename: str) -> str:
        photos_dir = os.path.join(os.path.dirname(__file__), "..", "photos")
        path = os.path.join(photos_dir, filename)
        try:
            with open(path, "rb") as f:
                data = f.read()
            ext = filename.lower().rsplit(".", 1)[-1]
            mime = "jpeg" if ext in {"jpg", "jpeg"} else "png"
            return f"data:image/{mime};base64," + base64.b64encode(data).decode("ascii")
        except Exception:
            return ""

    central_name = "lobotomy.jpg"
    central_src = b64_image(central_name)

    # Collect satellite images (any image except central)
    photos_dir = os.path.join(os.path.dirname(__file__), "..", "photos")
    candidates = []
    try:
        for fn in os.listdir(photos_dir):
            ext = fn.lower().rsplit(".", 1)[-1]
            if ext in {"jpg", "jpeg", "png"} and fn != central_name:
                candidates.append(fn)
    except Exception:
        pass
    candidates.sort()

    app_items = list(app_links.items())
    sat_files = candidates[: len(app_items)]

    star_css = """
      body{margin:0;background:#000;color:#fff;height:100vh;overflow:hidden;font-family: system-ui;}
      .sky{position:fixed;inset:0;background:
          radial-gradient(2px 2px at 20% 30%, #fff, rgba(255,255,255,0) 60%),
          radial-gradient(1.5px 1.5px at 70% 80%, #fff, rgba(255,255,255,0) 60%),
          radial-gradient(1.5px 1.5px at 40% 60%, #fff, rgba(255,255,255,0) 60%),
          radial-gradient(1px 1px at 85% 20%, #fff, rgba(255,255,255,0) 60%),
          radial-gradient(1px 1px at 10% 80%, #fff, rgba(255,255,255,0) 60%),
          radial-gradient(1px 1px at 50% 10%, #fff, rgba(255,255,255,0) 60%);
          background-color:#000;}
      .universe{position:relative;width:100%;height:100%;display:flex;align-items:center;justify-content:center;}
      .planet{position:absolute;width:180px;height:180px;border-radius:50%;box-shadow:0 0 12px rgba(255,255,255,.25);} 
      .sat{position:absolute;width:90px;height:90px;border-radius:50%;box-shadow:0 0 10px rgba(255,255,255,.2);}
      .sat:hover{transform:scale(1.06);} 
      a{display:block;width:100%;height:100%;}
      img{width:100%;height:100%;object-fit:cover;border-radius:50%;}
    """

    # Arrange satellites around a circle
    r = 220
    pos_styles = []
    n = len(sat_files) if len(sat_files) > 0 else 1
    for i in range(n):
        angle = (2 * math.pi * i) / n
        x = int(r * math.cos(angle))
        y = int(r * math.sin(angle))
        pos_styles.append(f"style='transform: translate({x}px,{y}px);'")

    sats_html = []
    for (name, meta), fn, style in zip(app_items, sat_files, pos_styles):
        url = meta.get("url", "#")
        src = b64_image(fn)
        sats_html.append(
            f"<div class='sat' {style}><a href='{html.escape(url)}' target='_blank' rel='noopener'><img src='{src}' alt=''/></a></div>"
        )

    page = f"""<!doctype html>
<html lang='tr'>
  <head>
    <meta charset='utf-8'>
    <meta name='viewport' content='width=device-width, initial-scale=1'>
    <title>Landing</title>
    <link rel='icon' type='image/png' sizes='32x32' href='/favicon/favicon-32x32.png?v=2'>
    <link rel='icon' type='image/png' sizes='16x16' href='/favicon/favicon-16x16.png?v=2'>
    <link rel='shortcut icon' href='/favicon/favicon.ico?v=2'>
    <style>{star_css}</style>
  </head>
  <body>
    <div class='sky'></div>
    <div class='universe'>
      <div class='planet' style='transform: translate(0px,0px);'>
        <img src='{central_src}' alt='logo'/>
      </div>
      {''.join(sats_html)}
    </div>
  </body>
</html>"""
    return page.encode("utf-8")


def make_handler(html_bytes: bytes):
    class LandingHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path in {"/", "/index", "/index.html"}:
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(html_bytes)
            elif self.path == "/health":
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"ok")
            elif self.path.startswith("/favicon/"):
                import os
                filename = self.path.split("/")[-1].split("?")[0]  # Remove query params
                favicon_path = os.path.join(os.path.dirname(__file__), "..", "favicon", filename)
                try:
                    with open(favicon_path, "rb") as f:
                        content = f.read()
                    if filename.endswith(".ico"):
                        content_type = "image/x-icon"
                    elif filename.endswith(".png"):
                        content_type = "image/png"
                    else:
                        content_type = "application/octet-stream"
                    self.send_response(200)
                    self.send_header("Content-Type", content_type)
                    self.send_header("Content-Length", str(len(content)))
                    self.send_header("Cache-Control", "public, max-age=86400")
                    self.end_headers()
                    self.wfile.write(content)
                except FileNotFoundError:
                    self.send_error(404, "Favicon not found")
            else:
                self.send_error(404, "Not Found")

        def log_message(self, format, *args):  # noqa: A003
            pass

    return LandingHandler


def run(host: str, port: int, app_links: Dict[str, Dict[str, str]]) -> None:
    html_bytes = build_html(app_links)
    handler_cls = make_handler(html_bytes)
    server = HTTPServer((host, port), handler_cls)
    print(f"landing page: http://{host}:{port}/")
    server.serve_forever()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="landing.web", description="Basit landing page")
    parser.add_argument("--host", default="127.0.0.1", help="Sunucu adresi (vars: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=2000, help="Port (vars: 2000)")
    parser.add_argument(
        "--app48-url",
        default="http://127.0.0.1:2020/",
        help="app48 web arayüzü için URL",
    )
    parser.add_argument(
        "--app321-url",
        default="http://127.0.0.1:2019/",
        help="app321 web arayüzü için URL",
    )
    parser.add_argument(
        "--app72-url",
        default="http://127.0.0.1:2172/",
        help="app72 web arayüzü için URL",
    )
    parser.add_argument(
        "--app80-url",
        default="http://127.0.0.1:2180/",
        help="app80 web arayüzü için URL",
    )
    parser.add_argument(
        "--app120-url",
        default="http://127.0.0.1:2120/",
        help="app120 web arayüzü için URL",
    )
    parser.add_argument(
        "--news-converter-url",
        default="http://127.0.0.1:2199/",
        help="news_converter web arayüzü için URL",
    )
    args = parser.parse_args(argv)

    app_links = {
        "app48": {
            "title": "app48",
            "url": args.app48_url,
            "description": "48 dakikalık mumlarla sayım, DC listesi ve 12→48 dönüştürücü.",
        },
        "app72": {
            "title": "app72",
            "url": args.app72_url,
            "description": "72 dakikalık sayım, DC analizi ve 12→72 dönüştürücü (7x12m).",
        },
        "app80": {
            "title": "app80",
            "url": args.app80_url,
            "description": "80 dakikalık sayım, DC analizi ve 20→80 dönüştürücü (4x20m).",
        },
        "app120": {
            "title": "app120",
            "url": args.app120_url,
            "description": "120 dakikalık sayım, DC analizi, IOV/IOU analizi ve 60→120 dönüştürücü.",
        },
        "app321": {
            "title": "app321",
            "url": args.app321_url,
            "description": "60 dakikalık sayım araçları, DC listesi ve offset matrisi.",
        },
        "news_converter": {
            "title": "News Converter",
            "url": args.news_converter_url,
            "description": "📰 ForexFactory MD formatını JSON'a dönüştürür (çoklu dosya, direkt indirme).",
        },
    }

    run(args.host, args.port, app_links)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
