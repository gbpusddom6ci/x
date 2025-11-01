from http.server import HTTPServer, BaseHTTPRequestHandler
import argparse
import html
import io
import csv
import json
import os
from typing import List, Optional, Dict, Any, Type

from .counter import (
    Candle as CounterCandle,
    SEQUENCES,
    MINUTES_PER_STEP,
    DEFAULT_START_TOD,
    normalize_key,
    parse_float,
    parse_time_value,
    find_start_index,
    compute_dc_flags,
    compute_offset_alignment,
    predict_time_after_n_steps,
)
from .main import (
    Candle as ConverterCandle,
    estimate_timeframe_minutes,
    adjust_to_output_tz,
    convert_60m_to_120m,
    format_price,
)
from .iov.counter import (
    analyze_iov,
    SEQUENCES_FILTERED,
    IOVResult,
)
from .iou.counter import (
    analyze_iou,
    IOUResult,
)
from email.parser import BytesParser
from email.policy import default as email_default
from .iou.pattern import find_valid_patterns, format_pattern_results

from datetime import timedelta, datetime


def load_candles_from_text(text: str, candle_cls: Type) -> List:
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
        raise ValueError(
            "CSV başlıkları eksik. Gerekli: Time, Open, High, Low, Close (Last)"
        )

    candles: List = []
    for row in reader:
        t = parse_time_value(row.get(time_key))
        o = parse_float(row.get(open_key))
        h = parse_float(row.get(high_key))
        l = parse_float(row.get(low_key))
        c = parse_float(row.get(close_key))
        if None in (t, o, h, l, c):
            continue
        candles.append(candle_cls(ts=t, open=o, high=h, low=l, close=c))
    candles.sort(key=lambda x: x.ts)
    return candles


def format_pip(delta: Optional[float]) -> str:
    if delta is None:
        return "-"
    return f"{delta:+.5f}"


def load_news_data_from_directory(
    directory_path: str,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Load all ForexFactory news data from JSON files in a directory.
    Returns a dict: date_string -> list of events for that date.
    Automatically merges all JSON files in the directory.
    """
    if not os.path.exists(directory_path) or not os.path.isdir(directory_path):
        return {}

    events_by_date: Dict[str, List[Dict[str, Any]]] = {}

    try:
        # Find all JSON files in directory
        json_files = [f for f in os.listdir(directory_path) if f.endswith(".json")]

        for json_file in json_files:
            json_path = os.path.join(directory_path, json_file)
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Index events by date
                for day in data.get("days", []):
                    date_str = day.get("date")  # e.g., "2025-03-17"
                    events = day.get("events", [])
                    if date_str:
                        # Merge events if date already exists
                        if date_str in events_by_date:
                            events_by_date[date_str].extend(events)
                        else:
                            events_by_date[date_str] = events
            except Exception:
                # Skip invalid JSON files
                continue

        return events_by_date
    except Exception:
        return {}


def find_news_in_timerange(
    events_by_date: Dict[str, List[Dict[str, Any]]],
    start_ts: datetime,
    duration_minutes: int = 120,
) -> List[Dict[str, Any]]:
    """
    Find news events that fall within [start_ts, start_ts + duration_minutes).
    For null-valued events (speeches, statements), check 1 hour before candle start.
    News data is in UTC-4 (same as candle data).
    """
    end_ts = start_ts + timedelta(minutes=duration_minutes)
    matching = []

    # For null events, extend search to 1 hour before candle start
    extended_start_ts = start_ts - timedelta(hours=1)

    # Check both start and end date (in case range spans midnight)
    dates_to_check = {start_ts.strftime("%Y-%m-%d")}
    if end_ts.date() != start_ts.date():
        dates_to_check.add(end_ts.strftime("%Y-%m-%d"))
    if extended_start_ts.date() != start_ts.date():
        dates_to_check.add(extended_start_ts.strftime("%Y-%m-%d"))

    for date_str in dates_to_check:
        events = events_by_date.get(date_str, [])

        for event in events:
            time_24h = event.get("time_24h")

            try:
                # Handle All Day events - they apply to the whole day
                if not time_24h:
                    # All Day event - check if the date matches
                    year, month, day = map(int, date_str.split("-"))
                    event_date = datetime(year, month, day)
                    if extended_start_ts.date() <= event_date.date() <= end_ts.date():
                        matching.append(event)
                    continue

                # Parse time_24h (e.g., "04:48")
                hour, minute = map(int, time_24h.split(":"))

                # Parse the date from date_str to handle multi-day ranges
                year, month, day = map(int, date_str.split("-"))
                event_ts = datetime(year, month, day, hour, minute)

                # Check if event has null values (speeches, statements)
                values = event.get("values", {})
                is_null_event = (
                    values.get("actual") is None
                    and values.get("forecast") is None
                    and values.get("previous") is None
                )

                # For null events: check 1 hour before candle to candle end
                # For regular events: check candle start to candle end
                if is_null_event:
                    if extended_start_ts <= event_ts < end_ts:
                        matching.append(event)
                else:
                    if start_ts <= event_ts < end_ts:
                        matching.append(event)
            except Exception:
                continue

    return matching


def categorize_news_event(event: Dict[str, Any]) -> str:
    """
    Categorize news event into one of four types:
    - HOLIDAY: title contains 'holiday' + All Day + null values
    - SPEECH: has time_24h + null values (speeches, statements)
    - ALLDAY: All Day + null values (but not holiday)
    - NORMAL: has values (actual/forecast/previous) - regardless of time

    Returns category string: 'HOLIDAY', 'SPEECH', 'ALLDAY', 'NORMAL', or 'UNKNOWN'
    """
    title = event.get("title", "").lower()
    time_label = event.get("time_label", "").lower()
    time_24h = event.get("time_24h")
    values = event.get("values", {})

    # Check if event has any values
    has_values = any(
        v is not None
        for v in [values.get("actual"), values.get("forecast"), values.get("previous")]
    )
    is_null = not has_values
    is_all_day = time_label == "all day" or time_24h is None

    # Category decision tree
    if "holiday" in title and is_all_day and is_null:
        return "HOLIDAY"
    elif has_values:
        # If event has values, it's NORMAL (affects XYZ) - regardless of having time or being All Day
        return "NORMAL"
    elif time_24h and is_null:
        return "SPEECH"
    elif is_all_day and is_null:
        return "ALLDAY"

    return "UNKNOWN"


def format_news_events(events: List[Dict[str, Any]]) -> str:
    """
    Format news events for display in IOU table.
    Format: var: [CATEGORY] CURRENCY Title (actual:X, forecast:Y, prev:Z); ...
    Categories: HOLIDAY, SPEECH, ALLDAY, NORMAL
    """
    if not events:
        return "-"

    parts = []
    for event in events:
        currency = event.get("currency", "?")
        title = event.get("title", "Unknown")
        values = event.get("values", {})

        # Categorize the event
        category = categorize_news_event(event)

        # Add category prefix for non-NORMAL events
        if category in ["HOLIDAY", "SPEECH", "ALLDAY"]:
            prefix = f"[{category}] "
        else:
            prefix = ""

        actual = values.get("actual")
        forecast = values.get("forecast")
        previous = values.get("previous")

        # Format values
        if actual is None and forecast is None and previous is None:
            # Event without values (e.g., speeches, bank holidays, all day events)
            parts.append(f"{prefix}{currency} {title}")
        else:
            val_strs = []
            if actual is not None:
                val_strs.append(f"actual:{actual}")
            if forecast is not None:
                val_strs.append(f"forecast:{forecast}")
            if previous is not None:
                val_strs.append(f"prev:{previous}")
            parts.append(f"{prefix}{currency} {title} ({', '.join(val_strs)})")

    return "var: " + "; ".join(parts)


def page(title: str, body: str, active_tab: str = "analyze") -> bytes:
    html_doc = f"""<!doctype html>
<html>
  <head>
    <meta charset='utf-8'>
    <meta name='viewport' content='width=device-width, initial-scale=1'/>
    <title>{html.escape(title)}</title>
    <link rel="icon" type="image/png" sizes="32x32" href="/favicon/favicon-32x32.png?v=2">
    <link rel="icon" type="image/png" sizes="16x16" href="/favicon/favicon-16x16.png?v=2">
    <link rel="shortcut icon" href="/favicon/favicon.ico?v=2">
    <style>
      /* Theme variables (default 'dark' via script) */
      :root {{
        --bg: #ffffff; --text: #0b1220; --muted: #475569;
        --card: #ffffff; --border: #e5e7eb; --th: #f5f5f5;
        --code: #f5f5f5; --link: #0366d6; --active-bg: #e6f2ff; --active-fg: #024ea2;
        color-scheme: light dark;
      }}
      @media (prefers-color-scheme: dark) {{
        :root {{ --bg:#0d1117; --text:#e6edf3; --muted:#9aa4b2; --card:#0f172a; --border:#30363d; --th:#161b22; --code:#161b22; --link:#58a6ff; --active-bg:#1f6feb22; --active-fg:#c9d1d9; }}
      }}
      :root[data-theme="light"] {{ --bg:#ffffff; --text:#0b1220; --muted:#475569; --card:#ffffff; --border:#e5e7eb; --th:#f5f5f5; --code:#f5f5f5; --link:#0366d6; --active-bg:#e6f2ff; --active-fg:#024ea2; }}
      :root[data-theme="dark"]  {{ --bg:#0d1117; --text:#e6edf3; --muted:#9aa4b2; --card:#0f172a; --border:#30363d; --th:#161b22; --code:#161b22; --link:#58a6ff; --active-bg:#1f6feb22; --active-fg:#c9d1d9; }}
      body{{font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin:20px;}}
      header{{margin-bottom:16px;}}
      form label{{display:block; margin:8px 0 4px;}}
      input, select{{padding:6px; font-size:14px;}}
      button{{padding:8px 12px; font-size:14px; cursor:pointer;}}
      .row{{display:flex; gap:16px; flex-wrap:wrap; align-items:flex-end;}}
      .card{{border:1px solid #ddd; border-radius:8px; padding:12px; margin:12px 0;}}
      table{{border-collapse:collapse; width:100%;}}
      th, td{{border:1px solid #ddd; padding:6px 8px; text-align:left;}}
      th{{background:#f5f5f5;}}
      code{{background:#f5f5f5; padding:2px 4px; border-radius:4px;}}
      .tabs{{display:flex; gap:12px; margin-bottom:12px;}}
      .tabs a{{text-decoration:none; color:#0366d6; padding:6px 8px; border-radius:6px;}}
      .tabs a.active{{background:#e6f2ff; color:#024ea2;}}

      /* Dark overrides */
      [data-theme="dark"] body {{ background: var(--bg) !important; color: var(--text) !important; }}
      [data-theme="dark"] .card {{ background: var(--card) !important; border-color: var(--border) !important; color: var(--text) !important; }}
      [data-theme="dark"] table {{ color: var(--text) !important; }}
      [data-theme="dark"] th {{ background: var(--th) !important; color: var(--text) !important; }}
      [data-theme="dark"] th, [data-theme="dark"] td {{ border-color: var(--border) !important; }}
      [data-theme="dark"] code {{ background: var(--code) !important; color: var(--text) !important; }}
      [data-theme="dark"] .tabs a {{ color: var(--link) !important; }}
      [data-theme="dark"] .tabs a.active {{ background: var(--active-bg) !important; color: var(--active-fg) !important; }}
      [data-theme="dark"] input, [data-theme="dark"] select, [data-theme="dark"] button {{ background: var(--card) !important; color: var(--text) !important; border-color: var(--border) !important; }}
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
      <h2>app120</h2>
    </header>
    <nav class='tabs'>
      <a href='/' class='{"active" if active_tab == "analyze" else ""}'>Counter</a>
      <a href='/dc' class='{"active" if active_tab == "dc" else ""}'>DC List</a>
      <a href='/matrix' class='{"active" if active_tab == "matrix" else ""}'>Matrix</a>
      <a href='/iov' class='{"active" if active_tab == "iov" else ""}'>IOV</a>
      <a href='/iou' class='{"active" if active_tab == "iou" else ""}'>IOU</a>
      <a href='/convert' class='{"active" if active_tab == "convert" else ""}'>60→120 Converter</a>
    </nav>
    {body}
  </body>
</html>"""
    return html_doc.encode("utf-8")


def render_analyze_index() -> bytes:
    body = """
    <div class='card'>
      <form method='post' action='/analyze' enctype='multipart/form-data'>
        <div class='row'>
          <div>
            <label>CSV</label>
            <input type='file' name='csv' accept='.csv,text/csv' required />
          </div>
          <div>
            <label>Zaman Dilimi</label>
            <div>120m</div>
          </div>
          <div>
            <label>Girdi TZ</label>
            <select name='input_tz'>
              <option value='UTC-5'>UTC-5</option>
              <option value='UTC-4' selected>UTC-4</option>
            </select>
          </div>
          <div>
            <label>Dizi</label>
            <select name='sequence'>
              <option value='S1' selected>S1</option>
              <option value='S2'>S2</option>
            </select>
          </div>
          <div>
            <label>Offset</label>
            <select name='offset'>
              <option value='-3'>-3</option>
              <option value='-2'>-2</option>
              <option value='-1'>-1</option>
              <option value='0' selected>0</option>
              <option value='+1'>+1</option>
              <option value='+2'>+2</option>
              <option value='+3'>+3</option>
            </select>
          </div>
          <div>
            <label>DC Göster</label>
            <input type='checkbox' name='show_dc' checked />
          </div>
        </div>
        <div style='margin-top:12px;'>
          <button type='submit'>Analiz Et</button>
        </div>
      </form>
    </div>
    <p>CSV başlıkları: <code>Time, Open, High, Low, Close (Last)</code> (eş anlamlılar desteklenir).</p>
    """
    return page("app120", body, active_tab="analyze")


def render_dc_index() -> bytes:
    body = """
    <div class='card'>
      <form method='post' action='/dc' enctype='multipart/form-data'>
        <div class='row'>
          <div>
            <label>CSV</label>
            <input type='file' name='csv' accept='.csv,text/csv' required />
          </div>
          <div>
            <label>Zaman Dilimi</label>
            <div>120m</div>
          </div>
          <div>
            <label>Girdi TZ</label>
            <select name='input_tz'>
              <option value='UTC-5'>UTC-5</option>
              <option value='UTC-4' selected>UTC-4</option>
            </select>
          </div>
        </div>
        <div style='margin-top:12px;'>
          <button type='submit'>DC'leri Listele</button>
        </div>
      </form>
    </div>
    <p>Not: app120 sayımında DC'ler her zaman atlanır; bu sayfada tüm DC'ler listelenir.</p>
    """
    return page("app120 - DC List", body, active_tab="dc")


def render_matrix_index() -> bytes:
    body = """
    <div class='card'>
      <form method='post' action='/matrix' enctype='multipart/form-data'>
        <div class='row'>
          <div>
            <label>CSV</label>
            <input type='file' name='csv' accept='.csv,text/csv' required />
          </div>
          <div>
            <label>Zaman Dilimi</label>
            <div>120m</div>
          </div>
          <div>
            <label>Girdi TZ</label>
            <select name='input_tz'>
              <option value='UTC-5'>UTC-5</option>
              <option value='UTC-4' selected>UTC-4</option>
            </select>
          </div>
          <div>
            <label>Dizi</label>
            <select name='sequence'>
              <option value='S1' selected>S1</option>
              <option value='S2'>S2</option>
            </select>
          </div>
        </div>
        <div style='margin-top:12px;'>
          <button type='submit'>Matrix Göster</button>
        </div>
      </form>
    </div>
    """
    return page("app120 - Matrix", body, active_tab="matrix")


def render_iov_index() -> bytes:
    body = """
    <div class='card'>
      <h3>IOV (Inverse OC Value) Analizi</h3>
      <p>2 haftalık 120m veride, OC ve PrevOC değerlerinin limit üstünde ve zıt işaretli olduğu özel mumları tespit eder.</p>
      <form method='post' action='/iov' enctype='multipart/form-data'>
        <div class='row'>
          <div>
            <label>CSV Dosyaları (2 haftalık 120m) - En fazla 25 dosya</label>
            <input type='file' name='csv' accept='.csv,text/csv' multiple required />
          </div>
          <div>
            <label>Sequence</label>
            <select name='sequence'>
              <option value='S1' selected>S1 (1,3 hariç)</option>
              <option value='S2'>S2 (1,5 hariç)</option>
            </select>
          </div>
          <div>
            <label>Limit (mutlak değer)</label>
            <input type='number' name='limit' step='0.001' value='0.1' min='0' required />
          </div>
          <div>
            <label>Tolerance (güvenlik payı)</label>
            <input type='number' name='tolerance' step='0.001' value='0.005' min='0' required />
          </div>
          <div>
            <button type='submit'>Analiz Et</button>
          </div>
        </div>
      </form>
    </div>
    <div class='card'>
      <h4>IOV Mum Kriterleri:</h4>
      <ul>
        <li><strong>|OC| ≥ Limit</strong> - Mumun open-close farkı limit değerinin üstünde olmalı</li>
        <li><strong>|PrevOC| ≥ Limit</strong> - Önceki mumun open-close farkı limit değerinin üstünde olmalı</li>
        <li><strong>Zıt İşaret</strong> - OC ve PrevOC birinin (+) birinin (-) olması gerekir</li>
      </ul>
      <p><strong>Not:</strong> Tüm offsetler (-3..+3) otomatik taranır.</p>
    </div>
    """
    return page("app120 - IOV", body, active_tab="iov")


def render_iou_index() -> bytes:
    body = """
    <div class='card'>
      <h3>IOU (Inverse OC - Uniform sign) Analizi</h3>
      <p>2 haftalık 120m veride, OC ve PrevOC değerlerinin limit üstünde ve AYNI işaretli olduğu özel mumları tespit eder.</p>
      <form method='post' action='/iou' enctype='multipart/form-data'>
        <div class='row'>
          <div>
            <label>CSV Dosyaları (2 haftalık 120m) - En fazla 25 dosya</label>
            <input type='file' name='csv' accept='.csv,text/csv' multiple required />
          </div>
          <div>
            <label>Sequence</label>
            <select name='sequence'>
              <option value='S1' selected>S1 (1,3 hariç)</option>
              <option value='S2'>S2 (1,5 hariç)</option>
            </select>
          </div>
          <div>
            <label>Limit (mutlak değer)</label>
            <input type='number' name='limit' step='0.001' value='0.1' min='0' required />
          </div>
          <div>
            <label>Tolerance (güvenlik payı)</label>
            <input type='number' name='tolerance' step='0.001' value='0.005' min='0' required />
          </div>
          <div>
            <label>XYZ Küme Analizi</label>
            <input type='checkbox' name='xyz_analysis' checked />
          </div>
          <div>
            <label>XYZ Özet Tablosu</label>
            <input type='checkbox' name='xyz_summary_table' />
          </div>
          <div>
            <label>Pattern Analizi</label>
            <input type='checkbox' name='pattern_analysis' />
          </div>
          <div>
            <button type='submit'>Analiz Et</button>
          </div>
        </div>
      </form>
    </div>
    <div class='card'>
      <h4>IOU Mum Kriterleri:</h4>
      <ul>
        <li><strong>|OC| ≥ Limit</strong> - Mumun open-close farkı limit değerinin üstünde olmalı</li>
        <li><strong>|PrevOC| ≥ Limit</strong> - Önceki mumun open-close farkı limit değerinin üstünde olmalı</li>
        <li><strong>Aynı İşaret</strong> - OC ve PrevOC her ikisi de (+) VEYA her ikisi de (-) olmalı</li>
      </ul>
      <p><strong>Not:</strong> Tüm offsetler (-3..+3) otomatik taranır.</p>
      <p><strong>XYZ Analizi:</strong> Habersiz IOU içeren offsetler elenir, kalan offsetler XYZ kümesini oluşturur.</p>
    </div>
    """
    return page("app120 - IOU", body, active_tab="iou")


def render_converter_index() -> bytes:
    body = """
    <div class='card'>
      <form method='post' action='/convert' enctype='multipart/form-data'>
        <label>CSV (60m, UTC-5) — Birden fazla dosya yükleyebilirsiniz (maks. 50)</label>
        <input type='file' name='csv' accept='.csv,text/csv' multiple required />
        <div style='margin-top:12px;'>
          <button type='submit'>120m'e Dönüştür</button>
        </div>
      </form>
    </div>
    <p>Tek dosya yüklenirse CSV indirilir; birden fazla dosya yüklenirse ZIP (her biri ayrı CSV) indirilir.</p>
    """
    return page("app120 - Converter", body, active_tab="convert")


def parse_multipart(handler: BaseHTTPRequestHandler) -> Dict[str, Dict[str, Any]]:
    ctype = handler.headers.get("Content-Type")
    if not ctype or "multipart/form-data" not in ctype:
        raise ValueError("multipart/form-data bekleniyor")
    length = int(handler.headers.get("Content-Length", "0") or "0")
    # File upload size limit: 50 MB
    MAX_UPLOAD_SIZE = 50 * 1024 * 1024
    if length > MAX_UPLOAD_SIZE:
        raise ValueError(f"Dosya boyutu çok büyük (maksimum {MAX_UPLOAD_SIZE // (1024*1024)} MB)")
    form = BytesParser(policy=email_default).parsebytes(
        b"Content-Type: " + ctype.encode("utf-8") + b"\n\n" + handler.rfile.read(length)
    )
    out: Dict[str, Dict[str, Any]] = {}
    for part in form.iter_parts():
        if part.get_content_disposition() != "form-data":
            continue
        name = part.get_param("name", header="content-disposition")
        if not name:
            continue
        filename = part.get_filename()
        payload = part.get_payload(decode=True)
        if filename:
            data = payload
            if data is None:
                content = part.get_content()
                data = (
                    content.encode("utf-8", errors="replace")
                    if isinstance(content, str)
                    else content
                )
            out[name] = {"filename": filename, "data": data or b""}
        else:
            if payload is not None:
                value = payload.decode("utf-8", errors="replace")
            else:
                content = part.get_content()
                value = (
                    content
                    if isinstance(content, str)
                    else content.decode("utf-8", errors="replace")
                )
            out[name] = {"value": value}
    return out


def parse_multipart_with_multiple_files(
    handler: BaseHTTPRequestHandler,
) -> Dict[str, Any]:
    """Parse multipart form data with support for multiple files with same name."""
    ctype = handler.headers.get("Content-Type")
    if not ctype or "multipart/form-data" not in ctype:
        raise ValueError("multipart/form-data bekleniyor")
    length = int(handler.headers.get("Content-Length", "0") or "0")
    # File upload size limit: 50 MB
    MAX_UPLOAD_SIZE = 50 * 1024 * 1024
    if length > MAX_UPLOAD_SIZE:
        raise ValueError(f"Dosya boyutu çok büyük (maksimum {MAX_UPLOAD_SIZE // (1024*1024)} MB)")
    form = BytesParser(policy=email_default).parsebytes(
        b"Content-Type: " + ctype.encode("utf-8") + b"\n\n" + handler.rfile.read(length)
    )

    files: List[Dict[str, Any]] = []
    params: Dict[str, str] = {}

    for part in form.iter_parts():
        if part.get_content_disposition() != "form-data":
            continue
        name = part.get_param("name", header="content-disposition")
        if not name:
            continue
        filename = part.get_filename()
        payload = part.get_payload(decode=True)

        if filename:
            # It's a file
            data = payload
            if data is None:
                content = part.get_content()
                data = (
                    content.encode("utf-8", errors="replace")
                    if isinstance(content, str)
                    else content
                )
            files.append({"filename": filename, "data": data or b""})
        else:
            # It's a regular form field
            if payload is not None:
                value = payload.decode("utf-8", errors="replace")
            else:
                content = part.get_content()
                value = (
                    content
                    if isinstance(content, str)
                    else content.decode("utf-8", errors="replace")
                )
            params[name] = value

    return {"files": files, "params": params}


class App120Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Serve favicon files
        if self.path.startswith("/favicon/"):
            import os

            filename = self.path.split("/")[-1].split("?")[0]  # Remove query params
            # Path traversal protection
            filename = os.path.basename(filename)
            if not filename or ".." in filename or "/" in filename:
                self.send_error(400, "Invalid filename")
                return
            favicon_path = os.path.join(
                os.path.dirname(__file__), "..", "favicon", filename
            )
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
                return
            except FileNotFoundError:
                self.send_error(404, "Favicon not found")
                return

        if self.path == "/":
            body = render_analyze_index()
        elif self.path == "/dc":
            body = render_dc_index()
        elif self.path == "/matrix":
            body = render_matrix_index()
        elif self.path == "/iov":
            body = render_iov_index()
        elif self.path == "/iou":
            body = render_iou_index()
        elif self.path == "/convert":
            body = render_converter_index()
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        # Stage 2: Pattern analysis with joker selections
        if self.path == "/iou_analyze":
            try:
                self._handle_iou_final_analysis()
                return
            except Exception as e:
                err_msg = f"<div class='card'><h3>Hata</h3><p style='color:red;'>{html.escape(str(e))}</p></div>"
                self.send_response(400)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(page("app120 - Hata", err_msg, active_tab="iou"))
                return
        
        try:
            # Converter: multiple files (up to 50) -> ZIP; single file -> CSV
            if self.path == "/convert":
                form_data = parse_multipart_with_multiple_files(self)
                files = form_data.get("files", [])
                if not files:
                    raise ValueError("En az bir CSV dosyası yükleyin")
                if len(files) > 50:
                    raise ValueError("En fazla 50 dosya yükleyebilirsiniz")

                import zipfile

                if len(files) == 1:
                    file_obj = files[0]
                    raw = file_obj.get("data", b"")
                    text = (
                        raw.decode("utf-8", errors="replace")
                        if isinstance(raw, (bytes, bytearray))
                        else str(raw)
                    )
                    candles = load_candles_from_text(text, ConverterCandle)
                    if not candles:
                        raise ValueError("Veri boş veya çözümlenemedi")
                    tf_est = estimate_timeframe_minutes(candles)
                    if tf_est is None or abs(tf_est - 60) > 1.0:
                        raise ValueError("Girdi 60 dakikalık akış gibi görünmüyor")
                    shifted, _ = adjust_to_output_tz(candles, "UTC-5")
                    converted = convert_60m_to_120m(shifted)

                    buffer = io.StringIO()
                    writer = csv.writer(buffer)
                    writer.writerow(["Time", "Open", "High", "Low", "Close"])
                    for c in converted:
                        writer.writerow([
                            c.ts.strftime("%Y-%m-%d %H:%M:%S"),
                            format_price(c.open),
                            format_price(c.high),
                            format_price(c.low),
                            format_price(c.close),
                        ])
                    data = buffer.getvalue().encode("utf-8")
                    filename = file_obj.get("filename") or "converted.csv"
                    if "." in filename:
                        base, _ = filename.rsplit(".", 1)
                        download_name = base + "_120m.csv"
                    else:
                        download_name = filename + "_120m.csv"
                    download_name = download_name.strip().replace('"', "") or "converted_120m.csv"

                    self.send_response(200)
                    self.send_header("Content-Type", "text/csv; charset=utf-8")
                    self.send_header("Content-Disposition", f'attachment; filename="{download_name}"')
                    self.end_headers()
                    self.wfile.write(data)
                    return

                # Multi-file: ZIP
                zip_buf = io.BytesIO()
                with zipfile.ZipFile(zip_buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
                    for idx, fobj in enumerate(files, 1):
                        fname = fobj.get("filename") or f"file_{idx}.csv"
                        raw = fobj.get("data", b"")
                        text = (
                            raw.decode("utf-8", errors="replace")
                            if isinstance(raw, (bytes, bytearray))
                            else str(raw)
                        )
                        candles = load_candles_from_text(text, ConverterCandle)
                        if not candles:
                            raise ValueError(f"Veri boş: {fname}")
                        tf_est = estimate_timeframe_minutes(candles)
                        if tf_est is None or abs(tf_est - 60) > 1.0:
                            raise ValueError(f"60m değil: {fname}")
                        shifted, _ = adjust_to_output_tz(candles, "UTC-5")
                        converted = convert_60m_to_120m(shifted)

                        buf = io.StringIO()
                        writer = csv.writer(buf)
                        writer.writerow(["Time", "Open", "High", "Low", "Close"])
                        for c in converted:
                            writer.writerow([
                                c.ts.strftime("%Y-%m-%d %H:%M:%S"),
                                format_price(c.open),
                                format_price(c.high),
                                format_price(c.low),
                                format_price(c.close),
                            ])
                        csv_bytes = buf.getvalue().encode("utf-8")
                        if "." in fname:
                            base, _ = fname.rsplit(".", 1)
                            out_name = base + "_120m.csv"
                        else:
                            out_name = fname + "_120m.csv"
                        out_name = out_name.strip().replace('"', "") or f"converted_{idx}_120m.csv"
                        zf.writestr(out_name, csv_bytes)

                data = zip_buf.getvalue()
                self.send_response(200)
                self.send_header("Content-Type", "application/zip")
                self.send_header("Content-Disposition", 'attachment; filename="converted_120m.zip"')
                self.end_headers()
                self.wfile.write(data)
                return

            # IOV and IOU use multiple file upload, others use single file
            if self.path in ["/iov", "/iou"]:
                # Handle multiple files for IOV/IOU
                pass  # Will be handled in specific path blocks below
            else:
                # Single file upload for other paths
                form = parse_multipart(self)
                file_obj = form.get("csv")
                if not file_obj or "data" not in file_obj:
                    raise ValueError("CSV dosyası bulunamadı")
                raw = file_obj["data"]
                text = (
                    raw.decode("utf-8", errors="replace")
                    if isinstance(raw, (bytes, bytearray))
                    else str(raw)
                )


            if self.path == "/iov":
                # Use multiple file parser
                form_data = parse_multipart_with_multiple_files(self)
                files = form_data["files"]
                params = form_data["params"]

                if not files:
                    raise ValueError("En az bir CSV dosyası yükleyin")
                if len(files) > 25:
                    raise ValueError("En fazla 25 dosya yükleyebilirsiniz")

                sequence = (params.get("sequence") or "S1").strip()
                if sequence not in SEQUENCES_FILTERED:
                    sequence = "S1"
                limit_str = (params.get("limit") or "0.1").strip()
                try:
                    limit = float(limit_str)
                except:
                    limit = 0.1

                tolerance_str = (params.get("tolerance") or "0.005").strip()
                try:
                    tolerance = float(tolerance_str)
                except:
                    tolerance = 0.005

                # Build HTML header
                body = f"""
                <div class='card'>
                  <h3>📊 IOV Analiz Sonuçları</h3>
                  <div><strong>Dosya Sayısı:</strong> {len(files)}</div>
                  <div><strong>Sequence:</strong> {html.escape(sequence)} (Filtered: {", ".join(map(str, SEQUENCES_FILTERED[sequence]))})</div>
                  <div><strong>Limit:</strong> {limit}</div>
                </div>
                """

                # Process each file
                for file_idx, file_obj in enumerate(files, 1):
                    filename = file_obj.get("filename", f"Dosya {file_idx}")
                    raw = file_obj["data"]
                    text = (
                        raw.decode("utf-8", errors="replace")
                        if isinstance(raw, (bytes, bytearray))
                        else str(raw)
                    )

                    try:
                        candles = load_candles_from_text(text, CounterCandle)
                        if not candles:
                            body += f"<div class='card'><h3>❌ {html.escape(filename)}</h3><p style='color:red;'>Veri boş veya çözümlenemedi</p></div>"
                            continue

                        # Analyze IOV
                        results = analyze_iov(candles, sequence, limit)
                        total_iov = sum(len(v) for v in results.values())

                        # Skip if no IOV found
                        if total_iov == 0:
                            body += f"<div class='card' style='padding:10px;'><strong>📄 {html.escape(filename)}</strong> - <span style='color:#888;'>IOV yok</span></div>"
                            continue

                        # Compact header and single table with all offsets
                        body += f"""
                        <div class='card' style='padding:10px;'>
                          <strong>📄 {html.escape(filename)}</strong> - {len(candles)} mum, <strong>{total_iov} IOV</strong>
                          <table style='margin-top:8px;'>
                            <tr><th>Ofs</th><th>Seq</th><th>Idx</th><th>Timestamp</th><th>OC</th><th>PrevOC</th><th>PIdx</th></tr>
                        """

                        # Add all IOV candles from all offsets to single table
                        for offset in range(-3, 4):
                            iov_list = results[offset]
                            for iov in iov_list:
                                oc_fmt = format_pip(iov.oc)
                                prev_oc_fmt = format_pip(iov.prev_oc)
                                body += f"<tr><td>{offset:+d}</td><td>{iov.seq_value}</td><td>{iov.index}</td><td>{iov.timestamp.strftime('%m-%d %H:%M')}</td><td>{html.escape(oc_fmt)}</td><td>{html.escape(prev_oc_fmt)}</td><td>{iov.prev_index}</td></tr>"

                        body += "</table></div>"

                    except Exception as e:
                        body += f"<div class='card'><h3>❌ {html.escape(filename)}</h3><p style='color:red;'>Hata: {html.escape(str(e))}</p></div>"

                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(page("app120 - IOV Results", body, active_tab="iov"))
                return

            if self.path == "/iou":
                # Use multiple file parser
                form_data = parse_multipart_with_multiple_files(self)
                files = form_data["files"]
                params = form_data["params"]

                if not files:
                    raise ValueError("En az bir CSV dosyası yükleyin")
                if len(files) > 25:
                    raise ValueError("En fazla 25 dosya yükleyebilirsiniz")

                sequence = (params.get("sequence") or "S1").strip()
                if sequence not in SEQUENCES_FILTERED:
                    sequence = "S1"
                limit_str = (params.get("limit") or "0.1").strip()
                try:
                    limit = float(limit_str)
                except:
                    limit = 0.1

                tolerance_str = (params.get("tolerance") or "0.005").strip()
                try:
                    tolerance = float(tolerance_str)
                except:
                    tolerance = 0.005

                xyz_analysis = "xyz_analysis" in params
                xyz_summary_table = "xyz_summary_table" in params
                pattern_analysis = "pattern_analysis" in params
                
                # Get previous results if this is an appended analysis
                previous_results = params.get("previous_results", "")

                # Load news data from directory (auto-detects all JSON files)
                news_dir = os.path.join(
                    os.path.dirname(os.path.dirname(__file__)), "news_data"
                )
                events_by_date = load_news_data_from_directory(news_dir)
                
                # Stage 1: If both XYZ and Pattern analysis enabled, render joker selection interface
                if xyz_analysis and pattern_analysis:
                    self._render_joker_selection(files, sequence, limit, xyz_analysis, pattern_analysis, events_by_date, previous_results)
                    return

                # Count loaded files
                json_files_count = 0
                if os.path.exists(news_dir) and os.path.isdir(news_dir):
                    json_files_count = len(
                        [f for f in os.listdir(news_dir) if f.endswith(".json")]
                    )

                news_loaded = bool(events_by_date)

                # Build HTML header
                body = f"""
                <div class='card'>
                  <h3>📊 IOU Analiz Sonuçları</h3>
                  <div><strong>Dosya Sayısı:</strong> {len(files)}</div>
                  <div><strong>Sequence:</strong> {html.escape(sequence)} (Filtered: {", ".join(map(str, SEQUENCES_FILTERED[sequence]))})</div>
                  <div><strong>Limit:</strong> {limit}</div>
                  <div><strong>Tolerance:</strong> {tolerance}</div>
                  <div><strong>Haber Verisi:</strong> {f"✅ {json_files_count} JSON dosyası yüklendi ({len(events_by_date)} gün)" if news_loaded else "❌ news_data/ klasöründe JSON bulunamadı"}</div>
                  <div><strong>XYZ Analizi:</strong> {"✅ Aktif" if xyz_analysis else "❌ Pasif"}</div>
                  <div><strong>XYZ Özet Tablosu:</strong> {"✅ Aktif" if xyz_summary_table else "❌ Pasif"}</div>
                </div>
                """

                # For summary table mode: collect all results first
                summary_data = [] if xyz_summary_table else None

                # Process each file
                for file_idx, file_obj in enumerate(files, 1):
                    filename = file_obj.get("filename", f"Dosya {file_idx}")
                    raw = file_obj["data"]
                    text = (
                        raw.decode("utf-8", errors="replace")
                        if isinstance(raw, (bytes, bytearray))
                        else str(raw)
                    )

                    try:
                        candles = load_candles_from_text(text, CounterCandle)
                        if not candles:
                            if not xyz_summary_table:
                                body += f"<div class='card'><h3>❌ {html.escape(filename)}</h3><p style='color:red;'>Veri boş veya çözümlenemedi</p></div>"
                            continue

                        # Analyze IOU
                        results = analyze_iou(candles, sequence, limit, tolerance)
                        total_iou = sum(len(v) for v in results.values())

                        # Skip if no IOU found
                        if total_iou == 0:
                            if not xyz_summary_table:
                                body += f"<div class='card' style='padding:10px;'><strong>📄 {html.escape(filename)}</strong> - <span style='color:#888;'>IOU yok</span></div>"
                            continue

                        # XYZ Analysis: Track news-free IOUs per offset for THIS file
                        file_xyz_data = {
                            offset: {"news_free": 0, "with_news": 0}
                            for offset in range(-3, 4)
                        }
                        eliminated_candles = {
                            offset: [] for offset in range(-3, 4)
                        }  # Track which candles eliminated each offset

                        # Compact header and single table with all offsets (only if NOT summary mode)
                        if not xyz_summary_table:
                            body += f"""
                            <div class='card' style='padding:10px;'>
                              <strong>📄 {html.escape(filename)}</strong> - {len(candles)} mum, <strong>{total_iou} IOU</strong>
                              <table style='margin-top:8px;'>
                                <tr><th>Ofs</th><th>Seq</th><th>Idx</th><th>Timestamp</th><th>OC</th><th>PrevOC</th><th>PIdx</th><th>Haber</th></tr>
                            """

                        # Add all IOU candles from all offsets to single table
                        for offset in range(-3, 4):
                            iou_list = results[offset]
                            for iou in iou_list:
                                oc_fmt = format_pip(iou.oc)
                                prev_oc_fmt = format_pip(iou.prev_oc)

                                # Find news for this candle's timerange (120 minutes)
                                news_events = (
                                    find_news_in_timerange(
                                        events_by_date, iou.timestamp, 120
                                    )
                                    if news_loaded
                                    else []
                                )
                                news_text = format_news_events(news_events)

                                # For XYZ analysis: NORMAL and SPEECH category events count as "news"
                                # HOLIDAY, ALLDAY events are shown but don't affect XYZ filtering
                                # SPEECH events (with 1-hour-before search) affect XYZ as they have market impact
                                affecting_events = [
                                    e
                                    for e in news_events
                                    if categorize_news_event(e) in ["NORMAL", "SPEECH"]
                                ]
                                has_news = bool(affecting_events)

                                # Track for XYZ analysis (per file)
                                if xyz_analysis:
                                    if has_news:
                                        file_xyz_data[offset]["with_news"] += 1
                                    else:
                                        file_xyz_data[offset]["news_free"] += 1
                                        # Track the candle that eliminated this offset
                                        eliminated_candles[offset].append(
                                            iou.timestamp.strftime("%m-%d %H:%M")
                                        )

                                if not xyz_summary_table:
                                    body += f"<tr><td>{offset:+d}</td><td>{iou.seq_value}</td><td>{iou.index}</td><td>{iou.timestamp.strftime('%m-%d %H:%M')}</td><td>{html.escape(oc_fmt)}</td><td>{html.escape(prev_oc_fmt)}</td><td>{iou.prev_index}</td><td style='font-size:11px;max-width:400px;'>{html.escape(news_text)}</td></tr>"

                        if not xyz_summary_table:
                            body += "</table>"

                        # Display XYZ Set Analysis Results for THIS file
                        if xyz_analysis and not xyz_summary_table:
                            xyz_set = []
                            eliminated = []

                            for offset in range(-3, 4):
                                news_free_count = file_xyz_data[offset]["news_free"]
                                if news_free_count > 0:
                                    eliminated.append(offset)
                                else:
                                    xyz_set.append(offset)

                            xyz_set_str = ", ".join(
                                [f"{o:+d}" if o != 0 else "0" for o in xyz_set]
                            )
                            eliminated_str = ", ".join(
                                [f"{o:+d}" if o != 0 else "0" for o in eliminated]
                            )

                            body += f"""
                            <div style='margin-top:12px; padding:8px; background:#f0f9ff; border:1px solid #0ea5e9; border-radius:4px;'>
                              <strong>🎯 XYZ Kümesi:</strong> <code>{html.escape(xyz_set_str) if xyz_set else "Ø (boş)"}</code><br>
                              <strong>Elenen:</strong> <code>{html.escape(eliminated_str) if eliminated else "Ø (yok)"}</code>
                              <details style='margin-top:4px;'>
                                <summary style='cursor:pointer;'>Detaylar</summary>
                                <table style='margin-top:4px; font-size:12px;'>
                                  <tr><th>Offset</th><th>Habersiz</th><th>Haberli</th><th>Durum</th></tr>
                            """

                            for offset in range(-3, 4):
                                nf = file_xyz_data[offset]["news_free"]
                                wn = file_xyz_data[offset]["with_news"]
                                status = (
                                    "❌ Elendi" if offset in eliminated else "✅ XYZ'de"
                                )
                                offset_str = f"{offset:+d}" if offset != 0 else "0"
                                body += f"<tr><td>{offset_str}</td><td>{nf}</td><td>{wn}</td><td>{status}</td></tr>"

                            body += """
                                </table>
                              </details>
                            </div>
                            """

                        if not xyz_summary_table:
                            body += "</div>"

                        # Collect data for summary table
                        if xyz_summary_table and xyz_analysis:
                            xyz_set = []
                            eliminated = []
                            eliminated_details = []

                            for offset in range(-3, 4):
                                news_free_count = file_xyz_data[offset]["news_free"]
                                if news_free_count > 0:
                                    eliminated.append(offset)
                                    # Get candle times for this offset
                                    candle_times = ", ".join(
                                        eliminated_candles[offset][:3]
                                    )  # Max 3 times
                                    if len(eliminated_candles[offset]) > 3:
                                        candle_times += "..."
                                    eliminated_details.append(
                                        f"{offset:+d}: {candle_times}"
                                    )
                                else:
                                    xyz_set.append(offset)

                            xyz_set_str = (
                                ", ".join(
                                    [f"{o:+d}" if o != 0 else "0" for o in xyz_set]
                                )
                                if xyz_set
                                else "Ø"
                            )
                            eliminated_str = (
                                " | ".join(eliminated_details)
                                if eliminated_details
                                else "Ø"
                            )

                            summary_data.append(
                                {
                                    "filename": filename,
                                    "xyz_set": xyz_set_str,
                                    "eliminated": eliminated_str,
                                }
                            )

                    except Exception as e:
                        if not xyz_summary_table:
                            body += f"<div class='card'><h3>❌ {html.escape(filename)}</h3><p style='color:red;'>Hata: {html.escape(str(e))}</p></div>"

                # Render summary table if enabled
                if xyz_summary_table and summary_data:
                    body += """
                    <div class='card' style='padding:10px;'>
                      <h3>📊 XYZ Özet Tablosu</h3>
                      <table style='margin-top:8px;'>
                        <tr><th>Dosya Adı</th><th>XYZ Kümesi</th><th>Elenen Offsetler (Mum Saatleri)</th></tr>
                    """

                    for item in summary_data:
                        body += f"""
                        <tr>
                          <td>{html.escape(item["filename"])}</td>
                          <td><code>{html.escape(item["xyz_set"])}</code></td>
                          <td style='font-size:11px;'>{html.escape(item["eliminated"])}</td>
                        </tr>
                        """

                    body += """
                      </table>
                    </div>
                    """

                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(page("app120 - IOU Results", body, active_tab="iou"))
                return

            candles = load_candles_from_text(text, CounterCandle)
            if not candles:
                raise ValueError("Veri boş veya çözümlenemedi")

            sequence = (
                (form.get("sequence", {}).get("value") or "S2").strip()
                if self.path in ("/analyze", "/matrix")
                else "S2"
            )
            offset_s = (
                (form.get("offset", {}).get("value") or "0").strip()
                if self.path == "/analyze"
                else "0"
            )
            show_dc = ("show_dc" in form) if self.path == "/analyze" else False
            tz_label_sel = (form.get("input_tz", {}).get("value") or "UTC-5").strip()

            tz_norm = tz_label_sel.upper().replace(" ", "")
            tz_label = "UTC-4 -> UTC-4 (+0h)"
            if tz_norm in {"UTC-5", "UTC-05", "UTC-05:00", "-05:00"}:
                delta = timedelta(hours=1)
                candles = [
                    CounterCandle(
                        ts=c.ts + delta,
                        open=c.open,
                        high=c.high,
                        low=c.low,
                        close=c.close,
                    )
                    for c in candles
                ]
                tz_label = "UTC-5 -> UTC-4 (+1h)"

            if self.path == "/analyze":
                try:
                    offset = int(offset_s)
                except Exception:
                    offset = 0
                if offset < -3 or offset > 3:
                    offset = 0
                seq_values = SEQUENCES.get(sequence, SEQUENCES["S2"])[:]
                base_idx, align_status = find_start_index(candles, DEFAULT_START_TOD)
                dc_flags = compute_dc_flags(candles)
                alignment = compute_offset_alignment(
                    candles, dc_flags, base_idx, seq_values, offset
                )

                info_lines = [
                    f"<div><strong>Data:</strong> {len(candles)} candles</div>",
                    f"<div><strong>Zaman Dilimi:</strong> 120m</div>",
                    f"<div><strong>Range:</strong> {html.escape(candles[0].ts.strftime('%Y-%m-%d %H:%M:%S'))} -> {html.escape(candles[-1].ts.strftime('%Y-%m-%d %H:%M:%S'))}</div>",
                    f"<div><strong>TZ:</strong> {html.escape(tz_label)}</div>",
                    f"<div><strong>Start:</strong> base(18:00): idx={base_idx} ts={html.escape(candles[base_idx].ts.strftime('%Y-%m-%d %H:%M:%S'))} ({align_status}); "
                    f"offset={offset} =&gt; target_ts={html.escape(alignment.target_ts.strftime('%Y-%m-%d %H:%M:%S') if alignment.target_ts else '-')} ({alignment.offset_status}) "
                    f"idx={(alignment.start_idx if alignment.start_idx is not None else '-')} actual_ts={html.escape(alignment.actual_ts.strftime('%Y-%m-%d %H:%M:%S') if alignment.actual_ts else '-')} "
                    f"missing_steps={alignment.missing_steps}</div>",
                    f"<div><strong>Sequence:</strong> {html.escape(sequence)} {html.escape(str(seq_values))}</div>",
                ]

                rows_html = []
                for v, hit in zip(seq_values, alignment.hits):
                    idx = hit.idx
                    ts = hit.ts
                    if idx is None or ts is None or not (0 <= idx < len(candles)):
                        first = seq_values[0]
                        use_target = (
                            alignment.missing_steps and v <= alignment.missing_steps
                        )

                        # Son bilinen gerçek veriyi bul
                        if not use_target:
                            last_known_v = None
                            last_known_ts = None
                            last_known_idx = -1
                            for seq_v, seq_hit in zip(seq_values, alignment.hits):
                                if (
                                    seq_hit.idx is not None
                                    and seq_hit.ts is not None
                                    and 0 <= seq_hit.idx < len(candles)
                                ):
                                    last_known_v = seq_v
                                    last_known_ts = seq_hit.ts
                                    last_known_idx = seq_hit.idx
                            if last_known_v is not None and v > last_known_v:
                                # Son gerçek mumdan başla
                                actual_last_candle_ts = candles[-1].ts
                                actual_last_idx = len(candles) - 1
                                # DC'leri dikkate al - sadece NON-DC adımları say
                                non_dc_steps_from_last_known_to_end = 0
                                for i in range(last_known_idx + 1, actual_last_idx + 1):
                                    is_dc = dc_flags[i] if i < len(dc_flags) else False
                                    if not is_dc:
                                        non_dc_steps_from_last_known_to_end += 1
                                steps_from_end_to_v = (
                                    v - last_known_v
                                ) - non_dc_steps_from_last_known_to_end
                                pred_ts = predict_time_after_n_steps(
                                    actual_last_candle_ts, steps_from_end_to_v
                                )
                            else:
                                delta_steps = max(0, v - first)
                                base_ts = (
                                    alignment.start_ref_ts
                                    or alignment.target_ts
                                    or candles[base_idx].ts
                                )
                                pred_ts = predict_time_after_n_steps(
                                    base_ts, delta_steps
                                )
                        else:
                            delta_steps = max(0, v - first)
                            base_ts = (
                                alignment.target_ts
                                or alignment.start_ref_ts
                                or candles[base_idx].ts
                            )
                            pred_ts = predict_time_after_n_steps(base_ts, delta_steps)

                        pred_label = (
                            html.escape(pred_ts.strftime("%Y-%m-%d %H:%M:%S"))
                            + " (pred, OC -, PrevOC -)"
                        )
                        if show_dc:
                            rows_html.append(
                                f"<tr><td>{v}</td><td>-</td><td>{pred_label}</td><td>-</td></tr>"
                            )
                        else:
                            rows_html.append(
                                f"<tr><td>{v}</td><td>-</td><td>{pred_label}</td></tr>"
                            )
                        continue
                    ts_s = ts.strftime("%Y-%m-%d %H:%M:%S")
                    pip_label = format_pip(candles[idx].close - candles[idx].open)
                    prev_label = (
                        format_pip(candles[idx - 1].close - candles[idx - 1].open)
                        if idx - 1 >= 0
                        else "-"
                    )
                    ts_with_pip = f"{ts_s} (OC {pip_label}, PrevOC {prev_label})"
                    if show_dc:
                        dc_flag = dc_flags[idx]
                        dc_label = f"{dc_flag}"
                        if hit.used_dc:
                            dc_label += " (rule)"
                        rows_html.append(
                            f"<tr><td>{v}</td><td>{idx}</td><td>{html.escape(ts_with_pip)}</td><td>{dc_label}</td></tr>"
                        )
                    else:
                        rows_html.append(
                            f"<tr><td>{v}</td><td>{idx}</td><td>{html.escape(ts_with_pip)}</td></tr>"
                        )

                header = "<tr><th>Seq</th><th>Index</th><th>Timestamp</th>"
                if show_dc:
                    header += "<th>DC</th>"
                header += "</tr>"
                table = f"<table><thead>{header}</thead><tbody>{''.join(rows_html)}</tbody></table>"
                body = "<div class='card'>" + "".join(info_lines) + "</div>" + table
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(page("app120 sonuçlar", body, active_tab="analyze"))
                return

            dc_flags = compute_dc_flags(candles)
            if self.path == "/dc":
                rows_html = []
                count = 0
                for i, c in enumerate(candles):
                    if not dc_flags[i]:
                        continue
                    ts = c.ts.strftime("%Y-%m-%d %H:%M:%S")
                    rows_html.append(
                        f"<tr><td>{i}</td><td>{html.escape(ts)}</td><td>{c.open}</td><td>{c.high}</td><td>{c.low}</td><td>{c.close}</td></tr>"
                    )
                    count += 1
                header = "<tr><th>Index</th><th>Timestamp</th><th>Open</th><th>High</th><th>Low</th><th>Close</th></tr>"
                table = f"<table><thead>{header}</thead><tbody>{''.join(rows_html)}</tbody></table>"
                info = (
                    f"<div class='card'>"
                    f"<div><strong>Data:</strong> {len(candles)} candles</div>"
                    f"<div><strong>Zaman Dilimi:</strong> 120m</div>"
                    f"<div><strong>Range:</strong> {html.escape(candles[0].ts.strftime('%Y-%m-%d %H:%M:%S'))} -> {html.escape(candles[-1].ts.strftime('%Y-%m-%d %H:%M:%S'))}</div>"
                    f"<div><strong>TZ:</strong> {html.escape(tz_label)}</div>"
                    f"<div><strong>DC count:</strong> {count}</div>"
                    f"</div>"
                )
                body = info + table
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(page("app120 DC List", body, active_tab="dc"))
                return

            if self.path == "/matrix":
                seq_values = SEQUENCES.get(sequence, SEQUENCES["S2"])[:]
                base_idx, align_status = find_start_index(candles, DEFAULT_START_TOD)
                offsets = [-3, -2, -1, 0, 1, 2, 3]
                per_offset = {
                    o: compute_offset_alignment(
                        candles, dc_flags, base_idx, seq_values, o
                    )
                    for o in offsets
                }

                header_cells = "".join(
                    f"<th>{'+' + str(o) if o > 0 else str(o)}</th>" for o in offsets
                )
                rows = []
                for vi, v in enumerate(seq_values):
                    cells = [f"<td>{v}</td>"]
                    for o in offsets:
                        alignment = per_offset[o]
                        hit = alignment.hits[vi] if vi < len(alignment.hits) else None
                        idx = hit.idx if hit else None
                        ts = hit.ts if hit else None
                        if (
                            idx is not None
                            and ts is not None
                            and 0 <= idx < len(candles)
                        ):
                            ts_s = ts.strftime("%Y-%m-%d %H:%M:%S")
                            oc_label = format_pip(
                                candles[idx].close - candles[idx].open
                            )
                            prev_label = (
                                format_pip(
                                    candles[idx - 1].close - candles[idx - 1].open
                                )
                                if idx - 1 >= 0
                                else "-"
                            )
                            label = f"{ts_s} (OC {oc_label}, PrevOC {prev_label})"
                            if hit.used_dc:
                                label += " (DC)"
                            cells.append(f"<td>{html.escape(label)}</td>")
                        else:
                            first = seq_values[0]
                            use_target = (
                                alignment.missing_steps and v <= alignment.missing_steps
                            )

                            # Son bilinen gerçek veriyi bul
                            if not use_target:
                                last_known_v = None
                                last_known_ts = None
                                last_known_idx = -1
                                for seq_v, seq_hit in zip(seq_values, alignment.hits):
                                    if (
                                        seq_hit.idx is not None
                                        and seq_hit.ts is not None
                                        and 0 <= seq_hit.idx < len(candles)
                                    ):
                                        last_known_v = seq_v
                                        last_known_ts = seq_hit.ts
                                        last_known_idx = seq_hit.idx
                                if last_known_v is not None and v > last_known_v:
                                    # Son gerçek mumdan başla
                                    actual_last_candle_ts = candles[-1].ts
                                    actual_last_idx = len(candles) - 1
                                    # DC'leri dikkate al - sadece NON-DC adımları say
                                    non_dc_steps_from_last_known_to_end = 0
                                    for i in range(
                                        last_known_idx + 1, actual_last_idx + 1
                                    ):
                                        is_dc = (
                                            dc_flags[i] if i < len(dc_flags) else False
                                        )
                                        if not is_dc:
                                            non_dc_steps_from_last_known_to_end += 1
                                    steps_from_end_to_v = (
                                        v - last_known_v
                                    ) - non_dc_steps_from_last_known_to_end
                                    ts_pred = predict_time_after_n_steps(
                                        actual_last_candle_ts, steps_from_end_to_v
                                    )
                                else:
                                    delta_steps = max(0, v - first)
                                    base_ts = (
                                        alignment.start_ref_ts
                                        or alignment.target_ts
                                        or candles[base_idx].ts
                                    )
                                    ts_pred = predict_time_after_n_steps(
                                        base_ts, delta_steps
                                    )
                            else:
                                delta_steps = max(0, v - first)
                                base_ts = (
                                    alignment.target_ts
                                    or alignment.start_ref_ts
                                    or candles[base_idx].ts
                                )
                                ts_pred = predict_time_after_n_steps(
                                    base_ts, delta_steps
                                )

                            cells.append(
                                f"<td>{html.escape(ts_pred.strftime('%Y-%m-%d %H:%M:%S'))} (pred, OC -, PrevOC -)</td>"
                            )
                    rows.append(f"<tr>{''.join(cells)}</tr>")

                status_summary = ", ".join(
                    f"{('+' + str(o)) if o > 0 else str(o)}: {per_offset[o].offset_status}"
                    for o in offsets
                )

                table = f"<table><thead><tr><th>Seq</th>{header_cells}</tr></thead><tbody>{''.join(rows)}</tbody></table>"
                info = (
                    f"<div class='card'>"
                    f"<div><strong>Data:</strong> {len(candles)} candles</div>"
                    f"<div><strong>Zaman Dilimi:</strong> 120m</div>"
                    f"<div><strong>Range:</strong> {html.escape(candles[0].ts.strftime('%Y-%m-%d %H:%M:%S'))} -> {html.escape(candles[-1].ts.strftime('%Y-%m-%d %H:%M:%S'))}</div>"
                    f"<div><strong>TZ:</strong> {html.escape(tz_label)}</div>"
                    f"<div><strong>Sequence:</strong> {html.escape(sequence)}</div>"
                    f"<div><strong>Offset durumları:</strong> {html.escape(status_summary)}</div>"
                    f"</div>"
                )

                body = info + table
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(page("app120 Matrix", body, active_tab="matrix"))
                return

            raise ValueError("Bilinmeyen istek")
        except Exception as e:
            msg = html.escape(str(e) or "Bilinmeyen hata")
            self.send_response(400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                page("Hata", f"<p>Hata: {msg}</p><p><a href='/'>&larr; Geri</a></p>")
            )

    def _render_joker_selection(
        self, files, sequence, limit, xyz_analysis, pattern_analysis, events_by_date, previous_results=""
    ):
        """Stage 1: Calculate XYZ for all files and show joker selection interface."""
        import base64
        
        file_xyz_results = []
        for file_idx, file_obj in enumerate(files):
            filename = file_obj.get("filename", f"Dosya {file_idx + 1}")
            raw = file_obj["data"]
            text = (
                raw.decode("utf-8", errors="replace")
                if isinstance(raw, (bytes, bytearray))
                else str(raw)
            )
            
            try:
                candles = load_candles_from_text(text, CounterCandle)
                if not candles:
                    file_xyz_results.append({
                        "filename": filename,
                        "xyz_set": [],
                        "data_base64": base64.b64encode(raw).decode('ascii'),
                        "note": "Veri okunamadı"
                    })
                    continue
                
                results = analyze_iou(candles, sequence, limit)
                total_iou = sum(len(v) for v in results.values())
                
                file_xyz_data = {offset: {"news_free": 0, "with_news": 0} for offset in range(-3, 4)}
                
                if total_iou > 0:
                    for offset in range(-3, 4):
                        for iou in results[offset]:
                            news_events = (
                                find_news_in_timerange(events_by_date, iou.timestamp, 120)
                                if events_by_date
                                else []
                            )
                            affecting_events = [
                                e for e in news_events if categorize_news_event(e) in ["NORMAL", "SPEECH"]
                            ]
                            has_news = bool(affecting_events)
                            
                            if has_news:
                                file_xyz_data[offset]["with_news"] += 1
                            else:
                                file_xyz_data[offset]["news_free"] += 1
                
                xyz_set = []
                for offset in range(-3, 4):
                    if file_xyz_data[offset]["news_free"] == 0:
                        xyz_set.append(offset)
                
                note = "IOU yok" if total_iou == 0 else None
                file_xyz_results.append({
                    "filename": filename,
                    "xyz_set": xyz_set,
                    "data_base64": base64.b64encode(raw).decode('ascii'),
                    "note": note
                })
            except Exception as e:
                file_xyz_results.append({
                    "filename": filename,
                    "xyz_set": [],
                    "data_base64": base64.b64encode(raw).decode('ascii'),
                    "note": f"Hata: {str(e)[:50]}"
                })
                continue
        
        if not file_xyz_results:
            raise ValueError("Hiçbir dosyada IOU bulunamadı")
        
        body = f"""
        <div class='card'>
          <h3>🎯 Joker Dosya Seçimi</h3>
          <p>Her dosya için XYZ kümesi hesaplandı. İstediğiniz dosyayı <strong>Joker</strong> yaparak tüm offsetlerde kullanılabilir hale getirebilirsiniz.</p>
          <form method='post' action='/iou_analyze'>
            <input type='hidden' name='sequence' value='{html.escape(sequence)}' />
            <input type='hidden' name='limit' value='{limit}' />
            <input type='hidden' name='pattern_analysis' value='{"true" if pattern_analysis else "false"}' />
            <input type='hidden' name='previous_results' value='{html.escape(previous_results)}' />
            <table style='margin-top:12px;'>
              <tr>
                <th>Dosya Adı</th>
                <th>XYZ Kümesi</th>
                <th>Joker (Tüm Offsetler)</th>
              </tr>
        """
        
        for idx, file_data in enumerate(file_xyz_results):
            xyz_str = ", ".join([f"{o:+d}" if o != 0 else "0" for o in file_data["xyz_set"]])
            if not xyz_str:
                xyz_str = "Ø (boş)"
            
            note_html = ""
            if file_data.get("note"):
                note_html = f" <small style='color:#888;'>({html.escape(file_data['note'])})</small>"
            
            body += f"""
              <tr>
                <td>{html.escape(file_data["filename"])}{note_html}</td>
                <td><code>{html.escape(xyz_str)}</code></td>
                <td><input type='checkbox' name='joker_{idx}' value='1' /></td>
              </tr>
              <input type='hidden' name='file_{idx}_name' value='{html.escape(file_data["filename"])}' />
              <input type='hidden' name='file_{idx}_xyz' value='{html.escape(",".join(map(str, file_data["xyz_set"])))}' />
              <input type='hidden' name='file_{idx}_data' value='{file_data["data_base64"]}' />
            """
        
        body += f"""
            </table>
            <input type='hidden' name='file_count' value='{len(file_xyz_results)}' />
            <div style='margin-top:16px;'>
              <button type='submit'>Pattern Analizi Başlat</button>
            </div>
          </form>
        </div>
        """
        
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(page("app120 - Joker Seçimi", body, active_tab="iou"))
    
    def _handle_iou_final_analysis(self):
        """Stage 2: Perform pattern analysis with joker selections."""
        import base64
        from urllib.parse import parse_qs
        
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        parsed = parse_qs(body)
        
        params = {k: v[0] if v else '' for k, v in parsed.items()}
        
        file_count = int(params.get("file_count", "0"))
        if file_count == 0:
            raise ValueError("Dosya bilgisi bulunamadı")
        
        sequence = params.get("sequence", "S1").strip()
        limit_str = params.get("limit", "0.1").strip()
        try:
            limit = float(limit_str)
        except:
            limit = 0.1
        
        pattern_analysis = params.get("pattern_analysis", "false").lower() == "true"
        
        pattern_xyz_data = []
        for idx in range(file_count):
            filename = params.get(f"file_{idx}_name", f"Dosya {idx + 1}")
            xyz_str = params.get(f"file_{idx}_xyz", "")
            is_joker = f"joker_{idx}" in params
            
            if is_joker:
                xyz_set = list(range(-3, 4))
            else:
                if xyz_str:
                    xyz_set = [int(x.strip()) for x in xyz_str.split(",") if x.strip()]
                else:
                    xyz_set = []
            
            pattern_xyz_data.append((filename, xyz_set))
        
        # Only run pattern analysis if enabled
        if pattern_analysis:
            pattern_results = find_valid_patterns(pattern_xyz_data, max_branches=1000)
            pattern_html = format_pattern_results(pattern_results)
        else:
            pattern_results = []
            pattern_html = "<p><strong>Pattern Analizi:</strong> Devre dışı</p>"
        
        final_offsets = []
        if pattern_results:
            for result in pattern_results:
                if result.pattern:
                    final_offset = result.pattern[-1]
                    final_offsets.append(final_offset)
        
        final_offsets_summary = ""
        if final_offsets:
            unique_offsets = []
            seen = set()
            for offset in final_offsets:
                if offset not in seen:
                    unique_offsets.append(offset)
                    seen.add(offset)
            
            offset_strs = [f"{o:+d}" if o != 0 else "0" for o in unique_offsets]
            final_offsets_summary = f"""
            <div class='card' style='padding:10px; background:#fff7ed; border:1px solid #f97316;'>
              <h3>📌 Pattern Son Değerleri</h3>
              <p><strong>{len(final_offsets)} pattern tespit edildi.</strong> Benzersiz son offsetler: <code>{', '.join(offset_strs)}</code></p>
            </div>
            """
        
        # Check if there are previous results to display
        previous_html = params.get("previous_results", "")
        if previous_html:
            try:
                previous_html = base64.b64decode(previous_html.encode('ascii')).decode('utf-8')
            except:
                previous_html = ""
        
        # Build current results
        current_results = f"""
        <div class='card' style='border: 2px solid #10b981;'>
          <h3>📊 Pattern Analiz Sonuçları</h3>
          <div><strong>Dosya Sayısı:</strong> {file_count}</div>
          <div><strong>Sequence:</strong> {html.escape(sequence)}</div>
          <div><strong>Limit:</strong> {limit}</div>
        </div>
        {final_offsets_summary}
        <div class='card' style='padding:10px; background:#f0fdf4; border:1px solid #10b981;'>
          <h3>🔍 Pattern Analizi</h3>
          {pattern_html}
        </div>
        """
        
        # Combine previous and current results
        all_results_html = previous_html + current_results if previous_html else current_results
        
        # Encode all results for next iteration
        all_results_base64 = base64.b64encode(all_results_html.encode('utf-8')).decode('ascii')
        
        # Add "Additional Analysis" form at the bottom
        additional_form = f"""
        <hr style='margin: 40px 0; border: none; border-top: 2px dashed #ccc;'>
        <div class='card' style='background: #fffbeb; border: 2px dashed #f59e0b;'>
          <h3>➕ Ek IOU Analizi Yap</h3>
          <p>Üstteki sonuçlar korunarak yeni analiz ekleyebilirsiniz.</p>
          <form method='post' action='/iou' enctype='multipart/form-data'>
            <input type='hidden' name='previous_results' value='{html.escape(all_results_base64)}' />
            <div class='row'>
              <div>
                <label>CSV Dosyaları (2 haftalık 120m) - En fazla 25 dosya</label>
                <input type='file' name='csv' accept='.csv,text/csv' multiple required />
              </div>
              <div>
                <label>Sequence</label>
                <select name='sequence'>
                  <option value='S1' selected>S1</option>
                  <option value='S2'>S2</option>
                </select>
              </div>
              <div>
                <label>Limit</label>
                <input type='number' name='limit' value='0.1' step='0.01' min='0' style='width:80px' />
              </div>
              <div>
                <label>XYZ Küme Analizi</label>
                <input type='checkbox' name='xyz_analysis' checked />
              </div>
              <div>
                <label>Pattern Analizi</label>
                <input type='checkbox' name='pattern_analysis' checked />
              </div>
            </div>
            <div style='margin-top:12px;'>
              <button type='submit'>Ek Analiz Yap</button>
            </div>
          </form>
        </div>
        """
        
        body = all_results_html + additional_form
        
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(page("app120 - Pattern Analiz", body, active_tab="iou"))

    def log_message(self, format, *args):
        pass


def run(host: str, port: int) -> None:
    httpd = HTTPServer((host, port), App120Handler)
    print(f"app120 web: http://{host}:{port}/")
    httpd.serve_forever()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="app120.web", description="app120 için birleşik web arayüzü"
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="Sunucu adresi (vars: 127.0.0.1)"
    )
    parser.add_argument("--port", type=int, default=2120, help="Port (vars: 2120)")
    args = parser.parse_args(argv)
    run(args.host, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
