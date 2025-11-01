# app96/iou/web.py - Minimal stub
# Full IOU web UI to be implemented later

from http.server import HTTPServer, BaseHTTPRequestHandler
import argparse


def make_handler():
    class IOUHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            response = b"""<!doctype html>
<html>
  <head>
    <meta charset='utf-8'>
    <meta name='viewport' content='width=device-width, initial-scale=1'/>
    <title>app96 IOU</title>
    <style>
      :root { --bg:#ffffff; --text:#0b1220; --card:#ffffff; --border:#e5e7eb; --th:#f5f5f5; color-scheme: light dark; }
      @media (prefers-color-scheme: dark) { :root { --bg:#0d1117; --text:#e6edf3; --card:#0f172a; --border:#30363d; --th:#161b22; } }
      :root[data-theme="light"] { --bg:#ffffff; --text:#0b1220; --card:#ffffff; --border:#e5e7eb; --th:#f5f5f5; }
      :root[data-theme="dark"]  { --bg:#0d1117; --text:#e6edf3; --card:#0f172a; --border:#30363d; --th:#161b22; }
      body{ font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin:40px; }
      .card{ border:1px solid #e5e7eb; border-radius:8px; padding:16px; }
      [data-theme="dark"] body { background: var(--bg) !important; color: var(--text) !important; }
      [data-theme="dark"] .card { background: var(--card) !important; border-color: var(--border) !important; }
      .theme-toggle { position: fixed; right:14px; top:12px; z-index:9999; background: var(--card); color: var(--text); border:1px solid var(--border); border-radius:8px; padding:6px 10px; font:13px/1.2 system-ui, -apple-system, Segoe UI, Roboto, sans-serif; cursor:pointer; opacity:.9; }
      .theme-toggle:hover { opacity:1; }
    </style>
  </head>
  <body>
    <button id='theme-toggle' class='theme-toggle' type='button' aria-label='Theme'>Dark</button>
    <script>(function(){const KEY='x1-theme';const d=document.documentElement;const b=document.getElementById('theme-toggle');function L(v){return(v||'auto').replace(/^./,c=>c.toUpperCase())}function I(v){return{auto:'\xF0\x9F\x8C\x99',dark:'\xF0\x9F\x8C\x91',light:'\xE2\x98\x80\xEF\xB8\x8F'}[v||'auto']}function A(v){if(v==='auto'){delete d.dataset.theme}else{d.dataset.theme=v}localStorage.setItem(KEY,v);b.textContent=I(v)+' '+L(v)}function N(v){return v==='auto'?'dark':v==='dark'?'light':'auto'}A(localStorage.getItem(KEY)||'dark');b.addEventListener('click',()=>A(N(localStorage.getItem(KEY)||'dark')));})();</script>
    <div class='card'>
      <h1>app96 IOU Analysis</h1>
      <p>96-minute IOU (Inverse OC - Uniform sign) analysis with news integration.</p>
      <p><em>Full web UI coming soon...</em></p>
      <p>Use CLI: <code>python -m app96.iou.counter --csv data.csv --limit 0.75</code></p>
    </div>
  </body>
 </html>"""
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)
        
        def log_message(self, format, *args):
            pass

    return IOUHandler


def run(host: str, port: int) -> None:
    handler_cls = make_handler()
    server = HTTPServer((host, port), handler_cls)
    print(f"app96 IOU web: http://{host}:{port}/")
    server.serve_forever()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="app96.iou.web", description="app96 IOU web UI")
    parser.add_argument("--host", default="127.0.0.1", help="Host")
    parser.add_argument("--port", type=int, default=2197, help="Port")
    args = parser.parse_args(argv)

    run(args.host, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
