from __future__ import annotations

from http.server import HTTPServer, BaseHTTPRequestHandler
import argparse
import os
from typing import Dict


def build_html(app_links: Dict[str, Dict[str, str]]) -> bytes:
    # App to photo mapping
    app_photos = {
        "app48": "kan.jpeg",
        "app72": "kits.jpg",
        "app80": "penguins.jpg",
        "app120": "romantizma.png",
        "app321": "silkroad.jpg",
        "news_converter": "suicide.png",
    }

    # Build orbital items
    orbital_items = []
    for key, meta in app_links.items():
        url = meta.get("url", "#")
        photo = app_photos.get(key, "")
        orbital_items.append(
            f"<a href='{url}' target='_blank' rel='noopener'><img src='/photos/{photo}' alt='{key}'></a>"
        )

    page = f"""<!doctype html>
<html>
  <head>
    <meta charset='utf-8'>
    <meta name='viewport' content='width=device-width, initial-scale=1'>
    <title>x1 Trading Platform</title>
    <link rel="icon" type="image/png" sizes="32x32" href="/favicon/favicon-32x32.png">
    <link rel="icon" type="image/png" sizes="16x16" href="/favicon/favicon-16x16.png">
    <link rel="shortcut icon" href="/favicon/favicon.ico">
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      body {{
        background: #000 url('/stars.gif') repeat;
        min-height: 100vh;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        overflow-x: hidden;
      }}
      .space-container {{
        position: relative;
        width: 1200px;
        height: 900px;
        display: flex;
        align-items: center;
        justify-content: center;
      }}
      .center-logo {{
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        z-index: 10;
      }}
      .center-logo img {{
        width: 180px;
        height: auto;
        display: block;
      }}
      .orbital {{
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
      }}
      .orbital a {{
        position: absolute;
        display: block;
      }}
      .orbital a img {{
        width: auto;
        height: 96px;
        max-width: 144px;
        display: block;
      }}
      /* Position each orbital item - balanced asymmetric layout around center (6 items) */
      .orbital a:nth-child(1) {{ top: 150px; left: 50%; transform: translateX(-50%); }}
      .orbital a:nth-child(2) {{ top: 250px; right: 250px; }}
      .orbital a:nth-child(3) {{ top: 35%; right: 180px; transform: translateY(-50%); }}
      .orbital a:nth-child(4) {{ top: 60%; left: 220px; }}
      .orbital a:nth-child(5) {{ bottom: 180px; left: 480px; }}
      .orbital a:nth-child(6) {{ bottom: 150px; right: 400px; }}
      footer {{
        position: fixed;
        bottom: 40px;
        left: 50%;
        transform: translateX(-50%);
        text-align: center;
        font-family: sans-serif;
        font-size: 10px;
        font-weight: normal;
        color: #DC143C;
      }}
    </style>
  </head>
  <body>
    <div class='space-container'>
      <div class='center-logo'>
        <img src='/photos/lobotomy.jpg' alt='x1'>
      </div>
      <div class='orbital'>
        {''.join(orbital_items)}
      </div>
    </div>
    <footer>marketmalware</footer>
  </body>
</html>"""
    return page.encode("utf-8")


def make_handler(html_bytes: bytes):
    # Resolve paths at module level, not inside handler
    base_dir = os.path.dirname(os.path.abspath(__file__))
    photos_dir = os.path.join(base_dir, "..", "photos")
    favicon_dir = os.path.join(base_dir, "..", "favicon")
    
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
            elif self.path == "/stars.gif":
                stars_path = os.path.join(base_dir, "..", "stars.gif")
                try:
                    with open(stars_path, "rb") as f:
                        content = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "image/gif")
                    self.send_header("Content-Length", str(len(content)))
                    self.send_header("Cache-Control", "public, max-age=86400")
                    self.end_headers()
                    self.wfile.write(content)
                except FileNotFoundError:
                    self.send_error(404, "Stars.gif not found")
            elif self.path.startswith("/photos/"):
                filename = self.path.split("/")[-1].split("?")[0]
                photos_path = os.path.join(photos_dir, filename)
                try:
                    with open(photos_path, "rb") as f:
                        content = f.read()
                    if filename.endswith(".jpg") or filename.endswith(".jpeg"):
                        content_type = "image/jpeg"
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
                    self.send_error(404, "Photo not found")
            elif self.path.startswith("/favicon/"):
                filename = self.path.split("/")[-1].split("?")[0]
                favicon_path = os.path.join(favicon_dir, filename)
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
        default="http://127.0.0.1:3000/",
        help="News Converter web arayüzü için URL",
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
            "title": "📰 News Converter",
            "url": args.news_converter_url,
            "description": "Markdown formatından JSON'a haber verisi dönüştürücü. news_data/ klasörüne kayıt.",
        },
    }

    run(args.host, args.port, app_links)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
