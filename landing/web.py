from __future__ import annotations

from http.server import HTTPServer, BaseHTTPRequestHandler
import argparse
import os
from typing import Dict


def build_html(app_links: Dict[str, Dict[str, str]]) -> bytes:
    # Deliberately strange, surreal gateway UI built with pure HTML/CSS/JS.
    # No external assets beyond photos/, favicon/, stars.gif.
    import math

    # App to photo mapping (kept from previous design)
    app_photos = {
        "app48": "kan.jpeg",
        "app72": "kits.jpg",
        "app80": "penguins.jpg",
        "app90": "pussy.png",
        "app96": "chud.jpeg",
        "app120": "romantizma.png",
        "app321": "silkroad.jpg",
        "news_converter": "suicide.png",
    }

    # Build orbital items around a "wormhole" with individual speeds/offsets
    n = max(1, len(app_links))
    orbital_items: list[str] = []
    for i, (key, meta) in enumerate(app_links.items()):
        url = meta.get("url", "#")
        title = meta.get("title", key)
        desc = meta.get("description", "")
        photo = app_photos.get(key, "")
        # Spread angles evenly; vary radius and speed in a pseudo-organic way
        angle = (360.0 * i) / n
        radius = 280 + 80 * math.sin((i + 1) * 1.7)
        speed_s = 28 + (i % 5) * 6  # seconds
        delay_s = - (angle / 360.0) * speed_s
        hue = (i * 53) % 360
        # Aurora Void accent color per item
        aurora_colors = ["#00E5FF", "#38BDF8", "#A78BFA", "#06B6D4"]
        color = aurora_colors[i % len(aurora_colors)]
        item = (
            f"<div class='orb' style=\"--radius:{radius:.0f}px; --speed:{speed_s}s; animation-delay:{delay_s:.3f}s; --c:{color};\">"
            f"<div class='arm'>"
            f"<a href='{url}' title='{title} — {desc}' target='_blank' rel='noopener'>"
            f"<img src='/photos/{photo}' alt='{key}'>"
            f"</a>"
            f"</div>"
            f"</div>"
        )
        orbital_items.append(item)

    # Pre-render orbit HTML safely (avoid join type issues)
    orbits_html = "".join(str(x) for x in orbital_items)

    # Build floating DVD-style app items (anchors with images)
    dvd_items: list[str] = []
    for key, meta in app_links.items():
        url = meta.get("url", "#")
        title = meta.get("title", key)
        desc = meta.get("description", "")
        photo = app_photos.get(key, "")
        dvd_items.append(
            f"<a class='dvd' href='{url}' title='{title} — {desc}' target='_blank' rel='noopener'>"
            f"<img src='/photos/{photo}' alt='{key}'>"
            f"</a>"
        )
    dvds_html = "".join(dvd_items)

    page = f"""<!doctype html>
<html>
  <head>
    <meta charset='utf-8'>
    <meta name='viewport' content='width=device-width, initial-scale=1'>
    <title>malw.beer</title>
    <link rel="icon" type="image/png" sizes="32x32" href="/favicon/favicon-32x32.png">
    <link rel="icon" type="image/png" sizes="16x16" href="/favicon/favicon-16x16.png">
    <link rel="shortcut icon" href="/favicon/favicon.ico">
    <style>
      :root {{
        --mx: 0; /* mouse -0.5..+0.5 */
        --my: 0;
        --twist: 18deg;
        --glow: 0.6;
        --portal-size: min(60vmin, 540px);
        --portal-thick: 10vmin;
      }}
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ height: 100%; }}
      body {{
        font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, "Apple Color Emoji", "Segoe UI Emoji";
        background: #000 url('/stars.gif') repeat;
        background-size: auto;
        color: #eee;
        overflow: hidden;
      }}



      /* DVD screensaver stage */
      .stage {{ position: fixed; inset: 0; overflow: hidden; z-index: 2; }}
      .dvd {{ position: absolute; display: block; will-change: transform; }}
      .dvd img {{ height: 96px; width: auto; display: block; transform-origin: 50% 50%; will-change: transform; animation: spin 8s linear infinite; }}
      @keyframes spin {{ to {{ transform: rotate(360deg); }} }}

      .scene {{ position: relative; z-index: 2; height: 100%; display: grid; place-items: stretch; }}

      /* Central wormhole */
      .portal {{
        position: relative; width: var(--portal-size); height: var(--portal-size);
        border-radius: 50%;
        background:
          radial-gradient(closest-side, rgba(255,255,255,0.12), rgba(0,0,0,0.0) 60%),
          conic-gradient(from 0deg, color-mix(in srgb, var(--a1) 60%, transparent), color-mix(in srgb, var(--a2) 50%, transparent), color-mix(in srgb, var(--a3) 60%, transparent), color-mix(in srgb, var(--a4) 50%, transparent));
        box-shadow:
          0 0 60px 20px rgba(255,0,153,0.07) inset,
          0 0 140px rgba(0,255,255,0.10);
        filter: url(#wobble) blur(0.2px) contrast(1.1);
        transform: perspective(900px) rotateX(calc(var(--my) * var(--twist))) rotateY(calc(var(--mx) * -1 * var(--twist)));
        animation: swirl 30s linear infinite;
      }}
      @keyframes swirl {{ from {{ transform: perspective(900px) rotateX(calc(var(--my) * var(--twist))) rotateY(calc(var(--mx) * -1 * var(--twist))) rotate(0deg); }} to {{ transform: perspective(900px) rotateX(calc(var(--my) * var(--twist))) rotateY(calc(var(--mx) * -1 * var(--twist))) rotate(360deg); }} }}

      .halo {{
        position: absolute; inset: calc(var(--portal-thick) * -0.15);
        border-radius: 50%;
        background: conic-gradient(from 90deg, rgba(255,255,255,0.22), rgba(0,0,0,0));
        filter: blur(16px) opacity(.8);
        mix-blend-mode: screen;
        pointer-events: none;
      }}

      /* Static luminous rings (4 layers) */
      .rings {{ position: absolute; inset: 6%; pointer-events: none; z-index: 0; }}
      .ring {{ position: absolute; inset: 0; border-radius: 50%; opacity: .9; mix-blend-mode: screen; }}
      .ring::before {{ content: ""; position: absolute; inset: 0; border-radius: 50%; border: 1px solid rgba(255,255,255,0.08); box-shadow: 0 0 24px rgba(255,255,255,0.06) inset; }}
      .r1 {{ transform: scale(.58); filter: drop-shadow(0 0 10px var(--a1)); }}
      .r2 {{ transform: scale(.90); filter: drop-shadow(0 0 12px var(--a2)); }}
      .r3 {{ transform: scale(1.22); filter: drop-shadow(0 0 14px var(--a3)); }}
      .r4 {{ transform: scale(1.48); filter: drop-shadow(0 0 16px var(--a4)); }}

      .glitch {{
        position: absolute; inset: 0; display: grid; place-items: center; text-transform: uppercase;
        font-size: clamp(28px, 7vmin, 92px); letter-spacing: .12em; font-weight: 800; color: #e7e7e7;
        mix-blend-mode: difference; text-shadow: 0 0 10px rgba(255,255,255,0.2);
      }}
      .glitch span {{ position: absolute; }}
      .glitch span:nth-child(1) {{ transform: translate(-2px,-1px); color: var(--a4); filter: blur(.2px); }}
      .glitch span:nth-child(2) {{ transform: translate(2px,1px); color: var(--a3); filter: blur(.2px); }}
      .glitch span:nth-child(3) {{ position: relative; color: #fafafa; }}
      .glitch span:nth-child(4) {{ transform: translate(-3px,2px); color: var(--a1); filter: blur(.2px); mix-blend-mode: screen; }}

      /* Galaxy of orbits */
      .galaxy {{ position: absolute; inset: -2%; }}
      .orb {{
        position: absolute; top: 50%; left: 50%;
        transform: translate(-50%,-50%) rotate(0deg);
        animation: revolve var(--speed) linear infinite;
        will-change: transform;
      }}
      .arm {{
        transform: translateX(var(--radius));
        filter: url(#wobble) saturate(1.05);
      }}
      .orb a {{ display: inline-block; transform: rotate(0deg); }}
      .orb img {{
        height: clamp(72px, 10vmin, 140px);
        width: auto; display: block; border-radius: 12px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.45), 0 0 0 1px rgba(255,255,255,0.06) inset;
        filter: drop-shadow(0 0 18px var(--c)) drop-shadow(0 0 6px rgba(255,255,255,0.06));
        mix-blend-mode: screen;
        animation: bob 4s ease-in-out infinite alternate;
      }}
      @keyframes revolve {{ to {{ transform: translate(-50%,-50%) rotate(360deg); }} }}
      @keyframes bob {{
        0% {{ filter: drop-shadow(0 0 0 rgba(255,0,200,0.0)); transform: translateY(-4px) rotate(-1deg); }}
        100% {{ filter: drop-shadow(0 0 16px rgba(0,255,240,0.16)); transform: translateY(4px) rotate(1deg); }}
      }}
    </style>
  </head>
  <body>
    <div class='scene'>
      <!-- DVD-style floating apps -->
      <div id='stage' class='stage'>
        {dvds_html}
      </div>
      <!-- Center logo -->
      <div style='position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); z-index: 999;'>
        <img src='/photos/lobotomy.jpg' alt='logo' style='max-width: min(60vw, 540px); max-height: min(60vh, 540px); width: auto; height: auto; border-radius: 24px; box-shadow: 0 20px 60px rgba(0,0,0,0.6), 0 0 80px rgba(255,255,255,0.15); filter: drop-shadow(0 0 30px rgba(255,255,255,0.2));'>
      </div>
      <!-- Hide old portal content entirely -->
      <div class='portal' style='display:none'></div>
    </div>

    <!-- SVG filters for wobble/distortion (no external deps) -->
    <svg width="0" height="0" style="position:absolute">
      <filter id="wobble">
        <feTurbulence type="fractalNoise" baseFrequency="0.98" numOctaves="1" seed="7" result="turb"/>
        <feDisplacementMap in="SourceGraphic" in2="turb" scale="2" xChannelSelector="R" yChannelSelector="G">
          <animate attributeName="scale" values="1;4;1" dur="8s" repeatCount="indefinite"/>
        </feDisplacementMap>
      </filter>
    </svg>

    <script>
      // Subtle mouse parallax (keeps the stars reactive)
      (function() {{
        const r = document.documentElement;
        window.addEventListener('mousemove', (e) => {{
          const x = (e.clientX / window.innerWidth) - 0.5;
          const y = (e.clientY / window.innerHeight) - 0.5;
          r.style.setProperty('--mx', x.toFixed(3));
          r.style.setProperty('--my', y.toFixed(3));
        }});
      }})();

      // DVD screensaver-like bouncing for app icons
      (function() {{
        const stage = document.getElementById('stage');
        if (!stage) return;
        const nodes = Array.from(stage.querySelectorAll('.dvd'));
        // Ensure predictable size for measurement
        function sizeOf(el) {{ return {{ w: el.offsetWidth || 100, h: el.offsetHeight || 80 }}; }}
        let W = stage.clientWidth, H = stage.clientHeight;
        const items = nodes.map((el, i) => {{
          const s = sizeOf(el);
          const ang = Math.random() * Math.PI * 2;
          const speed = 90 + Math.random() * 110; // px/s
          return {{ el, x: Math.random() * Math.max(1, W - s.w), y: Math.random() * Math.max(1, H - s.h), w: s.w, h: s.h, vx: Math.cos(ang) * speed, vy: Math.sin(ang) * speed }};
        }});

        function layout() {{
          W = stage.clientWidth; H = stage.clientHeight;
          // If any item has zero size (images not loaded yet), update sizes
          items.forEach(it => {{
            const s = sizeOf(it.el);
            if (s.w && s.h) {{ it.w = s.w; it.h = s.h; }}
            it.x = Math.max(0, Math.min(it.x, Math.max(0, W - it.w)));
            it.y = Math.max(0, Math.min(it.y, Math.max(0, H - it.h)));
          }});
        }}
        window.addEventListener('resize', layout);
        layout();

        let last = performance.now();
        function tick(now) {{
          const dt = Math.min(0.05, (now - last) / 1000); // clamp 50ms
          last = now;
          for (const it of items) {{
            it.x += it.vx * dt; it.y += it.vy * dt;
            // Bounce X
            if (it.x <= 0 && it.vx < 0) {{ it.x = 0; it.vx = -it.vx; }}
            if (it.x + it.w >= W && it.vx > 0) {{ it.x = W - it.w; it.vx = -it.vx; }}
            // Bounce Y
            if (it.y <= 0 && it.vy < 0) {{ it.y = 0; it.vy = -it.vy; }}
            if (it.y + it.h >= H && it.vy > 0) {{ it.y = H - it.h; it.vy = -it.vy; }}
            it.el.style.transform = `translate3d(${{it.x}}px, ${{it.y}}px, 0)`;
          }}
          requestAnimationFrame(tick);
        }}
        requestAnimationFrame(tick);
      }})();
    </script>
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
                stars_path = os.path.join(base_dir, "..", "photos", "stars.gif")
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
        "--app96-url",
        default="http://127.0.0.1:2196/",
        help="app96 web arayüzü için URL",
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
        "app96": {
            "title": "app96",
            "url": args.app96_url,
            "description": "96 dakikalık sayım, IOU analizi ve 12→96 dönüştürücü.",
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
