from http.server import HTTPServer, BaseHTTPRequestHandler
import argparse
import html
import io
import csv
from typing import List, Optional, Dict
from datetime import datetime

from .counter import (
    Candle,
    SEQUENCES_FILTERED,
    normalize_key,
    parse_float,
    parse_time_value,
    analyze_iov,
    fmt_ts,
    fmt_pip,
    IOVResult,
)
from email.parser import BytesParser
from email.policy import default as email_default


def load_candles_from_text(text: str) -> List[Candle]:
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except Exception:
        class _D(csv.Dialect):
            delimiter = ","
            quotechar = '"'
            doublequote = True
            skipinitialspace = True
            lineterminator = "\n"
            quoting = csv.QUOTE_MINIMAL
        dialect = _D()

    f = io.StringIO(text)
    reader = csv.DictReader(f, dialect=dialect)
    if not reader.fieldnames:
        raise ValueError("CSV header bulunamadı")
    field_map = {normalize_key(k): k for k in reader.fieldnames}

    def pick(*alts: str) -> Optional[str]:
        for a in alts:
            if a in field_map:
                return field_map[a]
        return None

    time_key = pick("time", "timestamp", "date", "datetime")
    open_key = pick("open", "o", "open (first)")
    high_key = pick("high", "h")
    low_key = pick("low", "l")
    close_key = pick("close (last)", "close", "last", "c", "close last", "close(last)")
    if not (time_key and open_key and high_key and low_key and close_key):
        raise ValueError("CSV başlıkları eksik. Gerekli: Time, Open, High, Low, Close (Last)")

    candles: List[Candle] = []
    for row in reader:
        t = parse_time_value(row.get(time_key))
        o = parse_float(row.get(open_key))
        h = parse_float(row.get(high_key))
        l = parse_float(row.get(low_key))
        c = parse_float(row.get(close_key))
        if None in (t, o, h, l, c):
            continue
        candles.append(Candle(ts=t, open=o, high=h, low=l, close=c))
    candles.sort(key=lambda x: x.ts)
    return candles


def page(title: str, body: str) -> bytes:
    html_doc = f"""<!doctype html>
<html>
  <head>
    <meta charset='utf-8'>
    <meta name='viewport' content='width=device-width, initial-scale=1'/>
    <title>{html.escape(title)}</title>
    <style>
      /* Theme variables (default 'dark' via script) */
      :root {{
        --bg: #ffffff; --text: #0b1220; --muted: #475569;
        --card: #ffffff; --border: #e5e7eb; --th: #f5f5f5; --code:#f5f5f5;
        --link: #0366d6; --accent:#1a73e8; --summary:#e8f0fe; --soft:#f8f9fa;
        color-scheme: light dark;
      }}
      @media (prefers-color-scheme: dark) {{
        :root {{ --bg:#0d1117; --text:#e6edf3; --muted:#9aa4b2; --card:#0f172a; --border:#30363d; --th:#161b22; --code:#161b22; --link:#58a6ff; --accent:#1f6feb; --summary:#1f6feb22; --soft:#0f172a; }}
      }}
      :root[data-theme="light"] {{ --bg:#ffffff; --text:#0b1220; --muted:#475569; --card:#ffffff; --border:#e5e7eb; --th:#f5f5f5; --code:#f5f5f5; --link:#0366d6; --accent:#1a73e8; --summary:#e8f0fe; --soft:#f8f9fa; }}
      :root[data-theme="dark"]  {{ --bg:#0d1117; --text:#e6edf3; --muted:#9aa4b2; --card:#0f172a; --border:#30363d; --th:#161b22; --code:#161b22; --link:#58a6ff; --accent:#1f6feb; --summary:#1f6feb22; --soft:#0f172a; }}

      body{{font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin:20px; background:#f5f5f5;}}
      header{{margin-bottom:16px; padding:20px; background:white; border-radius:8px; box-shadow:0 1px 3px rgba(0,0,0,0.1);}}
      h1{{margin:0 0 8px 0; color:#1a73e8;}}
      form label{{display:block; margin:12px 0 4px; font-weight:500;}}
      input, select{{padding:8px; font-size:14px; border:1px solid #ddd; border-radius:4px; width:200px;}}
      button{{padding:10px 20px; font-size:14px; cursor:pointer; background:#1a73e8; color:white; border:none; border-radius:4px; margin-top:12px;}}
      button:hover{{background:#1557b0;}}
      .card{{background:white; padding:20px; margin:16px 0; border-radius:8px; box-shadow:0 1px 3px rgba(0,0,0,0.1);}}
      .iov-section{{margin:16px 0; padding:16px; background:#f8f9fa; border-left:4px solid #1a73e8; border-radius:4px;}}
      .iov-item{{margin:12px 0; padding:12px; background:white; border-radius:4px; border:1px solid #e0e0e0;}}
      .seq-badge{{display:inline-block; padding:4px 8px; background:#1a73e8; color:white; border-radius:4px; font-weight:bold; margin-right:8px;}}
      .timestamp{{color:#5f6368; font-size:14px;}}
      .oc-values{{margin-top:8px; font-family:monospace; font-size:13px;}}
      .oc-positive{{color:#0f9d58;}}
      .oc-negative{{color:#d93025;}}
      .no-iov{{color:#5f6368; font-style:italic;}}
      table{{width:100%; border-collapse:collapse; margin-top:12px;}}
      th, td{{padding:8px; text-align:left; border-bottom:1px solid #e0e0e0;}}
      th{{background:#f8f9fa; font-weight:600;}}
      .summary{{background:#e8f0fe; padding:12px; border-radius:4px; margin:16px 0;}}

      /* Dark overrides */
      [data-theme="dark"] body {{ background: var(--bg) !important; color: var(--text) !important; }}
      [data-theme="dark"] header {{ background: var(--card) !important; color: var(--text) !important; border-color: var(--border) !important; }}
      [data-theme="dark"] .card {{ background: var(--card) !important; color: var(--text) !important; }}
      [data-theme="dark"] .iov-section {{ background: var(--soft) !important; border-left-color: var(--accent) !important; }}
      [data-theme="dark"] .iov-item {{ background: var(--card) !important; border-color: var(--border) !important; }}
      [data-theme="dark"] .timestamp {{ color: var(--muted) !important; }}
      [data-theme="dark"] table {{ color: var(--text) !important; }}
      [data-theme="dark"] th, [data-theme="dark"] td {{ border-color: var(--border) !important; }}
      [data-theme="dark"] th {{ background: var(--th) !important; }}
      [data-theme="dark"] .summary {{ background: var(--summary) !important; }}
      [data-theme="dark"] input, [data-theme="dark"] select, [data-theme="dark"] button {{ background: var(--card) !important; color: var(--text) !important; border-color: var(--border) !important; }}
      [data-theme="dark"] a {{ color: var(--link) !important; }}
      .theme-toggle {{ position: fixed; right: 14px; top: 12px; z-index: 9999; background: var(--card); color: var(--text); border: 1px solid var(--border); border-radius: 8px; padding: 6px 10px; font: 13px/1.2 system-ui, -apple-system, Segoe UI, Roboto, sans-serif; cursor: pointer; opacity: .9; }}
      .theme-toggle:hover {{ opacity: 1; }}
    </style>
  </head>
  <body>
    <button id='theme-toggle' class='theme-toggle' type='button' aria-label='Tema'>🌑 Dark</button>
    <script>
      (function() {{
        const KEY = 'x1-theme';
        const doc = document.documentElement;
        const btn = document.getElementById('theme-toggle');
        function label(v) {{ return (v||'auto').replace(/^./, c=>c.toUpperCase()); }}
        function icon(v) {{ return {{auto:'🌙', dark:'🌑', light:'☀️'}}[v||'auto']; }}
        function apply(v) {{ if (v==='auto') {{ delete doc.dataset.theme; }} else {{ doc.dataset.theme = v; }} localStorage.setItem(KEY, v); btn.textContent = icon(v)+' '+label(v); }}
        function next(v) {{ return v==='auto' ? 'dark' : v==='dark' ? 'light' : 'auto'; }}
        apply(localStorage.getItem(KEY) || 'dark');
        btn.addEventListener('click', () => apply(next(localStorage.getItem(KEY) || 'dark')));
      }})();
    </script>
    <header>
      <h1>🎯 app120_iov - IOV Candle Analysis</h1>
      <p>Inverse OC Value (IOV) mum analizi - 120m timeframe</p>
    </header>
    {body}
  </body>
</html>
"""
    return html_doc.encode("utf-8")


def render_index() -> bytes:
    body = """
    <div class='card'>
      <h2>IOV Analizi</h2>
      <form method='post' action='/' enctype='multipart/form-data'>
        <label>CSV Dosyası (2 haftalık 120m data):</label>
        <input type='file' name='csv' accept='.csv' required />
        <div>
          <label>Sequence:</label>
          <select name='sequence'>
            <option value='S1' selected>S1 (Filtered: 7, 13, 21...)</option>
            <option value='S2'>S2 (Filtered: 9, 17, 25...)</option>
          </select>
        </div>
        <label>Limit (mutlak değer):</label>
        <input type='number' name='limit' step='0.001' value='0.1' min='0' required />
        
        <button type='submit'>Analiz Et</button>
      </form>
    </div>
    <div class='card'>
      <h3>ℹ️ IOV Mum Nedir?</h3>
      <p><strong>IOV (Inverse OC Value)</strong> mumu, aşağıdaki kriterleri karşılayan özel mumlardır:</p>
      <ul>
        <li><strong>|OC| ≥ Limit</strong> - Mumun open-close farkı limit değerinin üstünde olmalı</li>
        <li><strong>|PrevOC| ≥ Limit</strong> - Önceki mumun open-close farkı limit değerinin üstünde olmalı</li>
        <li><strong>Zıt İşaret</strong> - OC ve PrevOC birinin (+) birinin (-) olması gerekir</li>
      </ul>
      <p><strong>Not:</strong> S1 için 1 ve 3 değerleri, S2 için 1 ve 5 değerleri analiz edilmez.</p>
    </div>
    """
    return page("app120_iov", body)


def render_results(
    candles: List[Candle],
    sequence: str,
    limit: float,
    results: Dict[int, List[IOVResult]]
) -> bytes:
    total_iov = sum(len(v) for v in results.values())
    
    body = f"""
    <div class='card'>
      <h2>📊 Analiz Sonuçları</h2>
      <div class='summary'>
        <strong>📁 Veri:</strong> {len(candles)} mum ({fmt_ts(candles[0].ts)} → {fmt_ts(candles[-1].ts)})<br>
        <strong>🔢 Sequence:</strong> {sequence} (Filtered: {', '.join(map(str, SEQUENCES_FILTERED[sequence]))})<br>
        <strong>📏 Limit:</strong> {limit}<br>
        <strong>🎯 Toplam IOV Mum:</strong> {total_iov}
      </div>
    </div>
    """
    
    # Only show offsets with IOV candles
    for offset in range(-3, 4):
        iov_list = results[offset]
        
        if iov_list:  # Only display if there are IOV candles
            body += f"""
            <div class='iov-section'>
              <h3>Offset: {offset:+d} ({len(iov_list)} IOV mum)</h3>
            """
            
            for iov in iov_list:
                oc_class = "oc-positive" if iov.oc > 0 else "oc-negative"
                prev_oc_class = "oc-positive" if iov.prev_oc > 0 else "oc-negative"
                
                body += f"""
                <div class='iov-item'>
                  <span class='seq-badge'>Seq {iov.seq_value}</span>
                  <span class='timestamp'>Index: {iov.index} | {fmt_ts(iov.timestamp)}</span>
                  <div class='oc-values'>
                    <strong>OC:</strong> <span class='{oc_class}'>{fmt_pip(iov.oc)}</span> | 
                    <strong>PrevOC:</strong> <span class='{prev_oc_class}'>{fmt_pip(iov.prev_oc)}</span>
                    <span style='color:#888;'>(Prev Index: {iov.prev_index}, {fmt_ts(iov.prev_timestamp)})</span>
                  </div>
                </div>
                """
            
            body += "</div>"
    
    body += """
    <div class='card'>
      <a href='/' style='text-decoration:none;'>
        <button>← Yeni Analiz</button>
      </a>
    </div>
    """
    
    return page("IOV Analysis Results", body)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(render_index())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/":
            try:
                ctype = self.headers.get("Content-Type", "")
                if "multipart/form-data" not in ctype:
                    raise ValueError("Invalid content type")

                boundary = None
                for part in ctype.split(";"):
                    part = part.strip()
                    if part.startswith("boundary="):
                        boundary = part.split("=", 1)[1]
                        break

                if not boundary:
                    raise ValueError("No boundary found")

                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length)

                parser = BytesParser(policy=email_default)
                msg = parser.parsebytes(
                    b"Content-Type: " + ctype.encode() + b"\r\n\r\n" + body
                )

                csv_text = None
                sequence = "S2"
                limit = 0.1

                for part in msg.iter_parts():
                    name = part.get_param("name", header="content-disposition")
                    if name == "csv":
                        csv_text = part.get_content()
                    elif name == "sequence":
                        sequence = part.get_content().strip()
                    elif name == "limit":
                        limit = float(part.get_content().strip())

                if not csv_text:
                    raise ValueError("CSV dosyası yüklenemedi")

                candles = load_candles_from_text(csv_text)
                if not candles:
                    raise ValueError("CSV verisi boş")

                results = analyze_iov(candles, sequence, limit)

                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(render_results(candles, sequence, limit, results))

            except Exception as e:
                error_body = f"""
                <div class='card'>
                  <h2>❌ Hata</h2>
                  <p style='color:red;'>{html.escape(str(e))}</p>
                  <a href='/'><button>← Geri Dön</button></a>
                </div>
                """
                self.send_response(500)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(page("Error", error_body))
        else:
            self.send_response(404)
            self.end_headers()


def run(host: str, port: int):
    """Run function for appsuite integration"""
    server = HTTPServer((host, port), Handler)
    print(f"app120_iov web: http://{host}:{port}/")
    server.serve_forever()


def main(argv=None):
    parser = argparse.ArgumentParser(prog="app120_iov.web")
    parser.add_argument("--port", type=int, default=2121, help="HTTP port (default: 2121)")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind (default: 0.0.0.0)")
    args = parser.parse_args(argv)

    server = HTTPServer((args.host, args.port), Handler)
    print(f"🚀 app120_iov web server running on http://{args.host}:{args.port}")
    print(f"   Open: http://localhost:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n✅ Server stopped")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
