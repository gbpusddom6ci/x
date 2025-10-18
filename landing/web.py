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
        background: #000;
        background-image: 
          radial-gradient(2px 2px at 20% 30%, white, transparent),
          radial-gradient(2px 2px at 60% 70%, white, transparent),
          radial-gradient(1px 1px at 50% 50%, white, transparent),
          radial-gradient(1px 1px at 80% 10%, white, transparent),
          radial-gradient(2px 2px at 90% 60%, white, transparent),
          radial-gradient(1px 1px at 33% 80%, white, transparent),
          radial-gradient(1px 1px at 15% 90%, white, transparent);
        background-size: 200px 200px, 300px 300px, 250px 250px, 350px 350px, 280px 280px, 220px 220px, 320px 320px;
        background-position: 0 0, 40px 60px, 130px 270px, 70px 100px, 200px 150px, 250px 300px, 100px 200px;
        min-height: 100vh;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        overflow-x: hidden;
      }}
      .space-container {{
        position: relative;
        width: 800px;
        height: 600px;
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
        width: 280px;
        height: auto;
        border-radius: 8px;
        box-shadow: 0 0 40px rgba(255, 255, 255, 0.3);
      }}
      .orbital {{
        position: absolute;
        top: 50%;
        left: 50%;
        width: 100%;
        height: 100%;
      }}
      .orbital a {{
        position: absolute;
        display: block;
        transition: transform 0.3s ease;
      }}
      .orbital a:hover {{
        transform: scale(1.15);
        filter: brightness(1.2);
      }}
      .orbital a img {{
        width: 100px;
        height: 100px;
        object-fit: cover;
        border-radius: 50%;
        border: 3px solid rgba(255, 255, 255, 0.5);
        box-shadow: 0 0 20px rgba(255, 255, 255, 0.4);
      }}
      /* Position each orbital item */
      .orbital a:nth-child(1) {{ top: -50px; left: 50%; transform: translateX(-50%); }}
      .orbital a:nth-child(2) {{ top: 80px; right: -20px; }}
      .orbital a:nth-child(3) {{ top: 50%; right: -60px; transform: translateY(-50%); }}
      .orbital a:nth-child(4) {{ bottom: 80px; right: -20px; }}
      .orbital a:nth-child(5) {{ bottom: -50px; left: 50%; transform: translateX(-50%); }}
      .orbital a:nth-child(6) {{ bottom: 80px; left: -20px; }}
      .orbital a:nth-child(7) {{ top: 50%; left: -60px; transform: translateY(-50%); }}
      .orbital a:nth-child(8) {{ top: 80px; left: -20px; }}
      footer {{
        position: fixed;
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%);
        text-align: center;
        font-family: Arial, sans-serif;
        font-size: 11px;
        color: #ff0000;
      }}
      footer a {{
        color: #ff0000;
        text-decoration: none;
        margin: 0 8px;
      }}
      footer a:hover {{
        text-decoration: underline;
      }}
      .copyright {{
        margin-top: 8px;
        color: #ff0000;
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
    <footer>
      <div>
        <a href='#'>Privacy Policy</a>
        <a href='#'>Terms</a>
        <a href='#'>Accessibility</a>
        <a href='#'>AdChoices</a>
      </div>
      <div class='copyright'>x1 Trading Platform. All rights reserved © 2025</div>
    </footer>
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
            elif self.path.startswith("/photos/"):
                filename = self.path.split("/")[-1].split("?")[0]
                photos_path = os.path.join(os.path.dirname(__file__), "..", "photos", filename)
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
