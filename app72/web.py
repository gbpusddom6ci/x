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
    SEQUENCES_FILTERED,
    MINUTES_PER_STEP,
    DEFAULT_START_TOD,
    normalize_key,
    parse_float,
    parse_time_value,
    find_start_index,
    compute_dc_flags,
    compute_offset_alignment,
    predict_time_after_n_steps,
    analyze_iou,
    IOUResult,
)
from .main import (
    Candle as ConverterCandle,
    estimate_timeframe_minutes,
    adjust_to_output_tz,
    convert_12m_to_72m,
    format_price,
)
from email.parser import BytesParser
from email.policy import default as email_default
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
    duration_minutes: int = 72,
) -> List[Dict[str, Any]]:
    """
    Find news events that fall within [start_ts, start_ts + duration_minutes).
    For null-valued events (speeches, statements), check 1 hour before candle start.
    News data is in UTC-4 (same as candle data).

    IMPORTANT: Uses candle year to match news (ignores JSON year).
    """
    end_ts = start_ts + timedelta(minutes=duration_minutes)
    matching = []

    # For null events, extend search to 1 hour before candle start
    extended_start_ts = start_ts - timedelta(hours=1)

    # Get candle year to match with news (JSON might have different year)
    candle_year = start_ts.year

    # Check all dates in events_by_date with matching month-day
    for date_str, events in events_by_date.items():
        try:
            # Parse JSON date (might be any year)
            json_year, json_month, json_day = map(int, date_str.split("-"))

            # Replace with candle year for comparison
            adjusted_date = datetime(candle_year, json_month, json_day)

            # Check if this date is relevant to our time range
            # (could be same day, previous day, or next day due to time range)
            if not (
                adjusted_date.date() >= extended_start_ts.date() - timedelta(days=1)
                and adjusted_date.date() <= end_ts.date() + timedelta(days=1)
            ):
                continue

            for event in events:
                time_24h = event.get("time_24h")

                try:
                    # Handle All Day events - they apply to the whole day
                    if not time_24h:
                        # All Day event - check if the date falls within our range
                        event_date = datetime(candle_year, json_month, json_day)
                        if (
                            extended_start_ts.date()
                            <= event_date.date()
                            <= end_ts.date()
                        ):
                            matching.append(event)
                        continue

                    # Parse time_24h (e.g., "04:48")
                    hour, minute = map(int, time_24h.split(":"))

                    # Create event timestamp using candle year
                    event_ts = datetime(candle_year, json_month, json_day, hour, minute)

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
    </style>
  </head>
    <header>
      <h2>app72</h2>
    </header>
    <nav class='tabs'>
      <a href='/' class='{"active" if active_tab == "analyze" else ""}'>Counter</a>
      <a href='/iou' class='{"active" if active_tab == "iou" else ""}'>IOU</a>
      <a href='/dc' class='{"active" if active_tab == "dc" else ""}'>DC List</a>
      <a href='/matrix' class='{"active" if active_tab == "matrix" else ""}'>Matrix</a>
      <a href='/convert' class='{"active" if active_tab == "convert" else ""}'>12→72</a>
      <a href='/converter' class='{"active" if active_tab == "converter" else ""}'>Converter</a>
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
            <div>72m</div>
          </div>
          <div>
            <label>Girdi TZ</label>
            <select name='input_tz'>
              <option value='UTC-5' selected>UTC-5</option>
              <option value='UTC-4'>UTC-4</option>
            </select>
          </div>
          <div>
            <label>Dizi</label>
            <select name='sequence'>
              <option value='S1'>S1</option>
              <option value='S2' selected>S2</option>
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
    <p><strong>Not:</strong> 18:00 mumu (Pazar dahil) ve Cuma 16:48 mumu ASLA DC olamaz. Pazar hariç 19:12 ve 20:24 mumları da DC olamaz.</p>
    """
    return page("app72", body, active_tab="analyze")


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
            <div>72m</div>
          </div>
          <div>
            <label>Girdi TZ</label>
            <select name='input_tz'>
              <option value='UTC-5' selected>UTC-5</option>
              <option value='UTC-4'>UTC-4</option>
            </select>
          </div>
        </div>
        <div style='margin-top:12px;'>
          <button type='submit'>DC'leri Listele</button>
        </div>
      </form>
    </div>
    <p>Not: app72 sayımında DC'ler her zaman atlanır; bu sayfada tüm DC'ler listelenir.</p>
    <p><strong>Önemli:</strong> 18:00 mumu (Pazar dahil) ve Cuma 16:48 mumu ASLA DC olamaz. Pazar hariç 19:12 ve 20:24 mumları da DC olamaz.</p>
    """
    return page("app72 - DC List", body, active_tab="dc")


def render_iou_index() -> bytes:
    body = """
    <div class='card'>
      <h3>IOU (Inverse OC - Uniform sign) Analizi</h3>
      <form method='post' action='/iou' enctype='multipart/form-data'>
        <div class='row'>
          <div>
            <label>CSV Dosyaları (2 haftalık 72m) - En fazla 25 dosya</label>
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
            <input type='checkbox' name='xyz_analysis' />
          </div>
          <div>
            <label>XYZ Özet Tablosu</label>
            <input type='checkbox' name='xyz_summary_table' />
          </div>
        </div>
        <div style='margin-top:12px;'>
          <button type='submit'>Analiz Et</button>
        </div>
      </form>
    </div>
    <p><strong>IOU Kriterleri:</strong> |OC| ≥ limit VE |PrevOC| ≥ limit VE aynı işaret (++ veya --)</p>
    <p><strong>2 haftalık 72m veri</strong> kullanılır.</p>
    <p><strong>XYZ Analizi:</strong> Habersiz IOU içeren offsetler elenir, kalan offsetler XYZ kümesini oluşturur.</p>
    """
    return page("app72 - IOU", body, active_tab="iou")


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
            <div>72m</div>
          </div>
          <div>
            <label>Girdi TZ</label>
            <select name='input_tz'>
              <option value='UTC-5' selected>UTC-5</option>
              <option value='UTC-4'>UTC-4</option>
            </select>
          </div>
          <div>
            <label>Dizi</label>
            <select name='sequence'>
              <option value='S1'>S1</option>
              <option value='S2' selected>S2</option>
            </select>
          </div>
        </div>
        <div style='margin-top:12px;'>
          <button type='submit'>Matrix Göster</button>
        </div>
      </form>
    </div>
    """
    return page("app72 - Matrix", body, active_tab="matrix")


def render_converter_index() -> bytes:
    body = """
    <div class='card'>
      <form method='post' action='/converter' enctype='multipart/form-data'>
        <label>CSV (12m, UTC-5)</label>
        <input type='file' name='csv' accept='.csv,text/csv' required />
        <div style='margin-top:12px;'>
          <button type='submit'>72m'e Dönüştür</button>
        </div>
      </form>
    </div>
    <p>Girdi UTC-5 12 dakikalık mumlar olmalıdır. Çıktı UTC-4 72 dakikalık mumlar olarak indirilir (7 tane 12m = 1 tane 72m).</p>
    """
    return page("app72 - Converter", body, active_tab="converter")


def parse_multipart(handler: BaseHTTPRequestHandler) -> Dict[str, Dict[str, Any]]:
    ctype = handler.headers.get("Content-Type")
    if not ctype or "multipart/form-data" not in ctype:
        raise ValueError("multipart/form-data bekleniyor")
    length = int(handler.headers.get("Content-Length", "0") or "0")
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


class App72Handler(BaseHTTPRequestHandler):
    def _parse_multipart_multiple_files(self) -> Dict[str, Any]:
        """Parse multipart with multiple file support."""
        ct = self.headers.get("Content-Type", "")
        try:
            length = int(self.headers.get("Content-Length", "0") or 0)
        except Exception:
            length = 0
        body = self.rfile.read(length)
        if not ct.lower().startswith("multipart/form-data"):
            raise ValueError("Yalnızca multipart/form-data desteklenir")
        header_bytes = (
            b"Content-Type: " + ct.encode("utf-8") + b"\r\nMIME-Version: 1.0\r\n\r\n"
        )
        msg = BytesParser(policy=email_default).parsebytes(header_bytes + body)

        files: List[Dict[str, Any]] = []
        params: Dict[str, str] = {}

        for part in msg.iter_parts():
            cd = part.get("Content-Disposition", "")
            if not cd:
                continue
            param_dict: Dict[str, str] = {}
            for item in cd.split(";"):
                item = item.strip()
                if "=" in item:
                    k, v = item.split("=", 1)
                    param_dict[k.strip().lower()] = v.strip().strip('"')
            name = param_dict.get("name")
            filename = param_dict.get("filename")
            payload = part.get_payload(decode=True) or b""
            if not name:
                continue
            if filename is not None:
                files.append({"filename": filename, "data": payload})
            else:
                charset = part.get_content_charset() or "utf-8"
                try:
                    value = payload.decode(charset, errors="replace")
                except Exception:
                    value = payload.decode("utf-8", errors="replace")
                params[name] = value

        return {"files": files, "params": params}

    def do_GET(self):
        # Serve favicon files
        if self.path.startswith("/favicon/"):
            import os

            filename = self.path.split("/")[-1].split("?")[0]  # Remove query params
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
        elif self.path == "/iou":
            body = render_iou_index()
        elif self.path == "/dc":
            body = render_dc_index()
        elif self.path == "/matrix":
            body = render_matrix_index()
        elif self.path == "/converter":
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
        # IOU uses multiple file upload
        if self.path == "/iou":
            try:
                form_data = self._parse_multipart_multiple_files()
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

                xyz_analysis = "xyz_analysis" in params
                xyz_summary_table = "xyz_summary_table" in params

                # Load news data from directory (auto-detects all JSON files)
                news_dir = os.path.join(
                    os.path.dirname(os.path.dirname(__file__)), "news_data"
                )
                events_by_date = load_news_data_from_directory(news_dir)

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
                                body += f"<div class='card' style='padding:10px;'><strong>❌ {html.escape(filename)}</strong> - Veri boş</div>"
                            continue

                        # Analyze IOU
                        results = analyze_iou(candles, sequence, limit)
                        total_iou = sum(len(v) for v in results.values())

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

                        # Compact table with all offsets (only if NOT summary mode)
                        if not xyz_summary_table:
                            body += f"""
                            <div class='card' style='padding:10px;'>
                              <strong>📄 {html.escape(filename)}</strong> - {len(candles)} mum, <strong>{total_iou} IOU</strong>
                              <table style='margin-top:8px;'>
                                <tr><th>Ofs</th><th>Seq</th><th>Idx</th><th>Timestamp</th><th>OC</th><th>PrevOC</th><th>PIdx</th><th>Haber</th></tr>
                            """

                        for offset in range(-3, 4):
                            for iou in results[offset]:
                                oc_fmt = format_pip(iou.oc)
                                prev_oc_fmt = format_pip(iou.prev_oc)

                                # Find news for this candle's timerange (72 minutes)
                                news_events = (
                                    find_news_in_timerange(
                                        events_by_date, iou.timestamp, 72
                                    )
                                    if news_loaded
                                    else []
                                )
                                news_text = format_news_events(news_events)

                                # For XYZ analysis: only NORMAL category events count as "news"
                                # HOLIDAY, SPEECH, ALLDAY events are shown but don't affect XYZ filtering
                                normal_events = [
                                    e
                                    for e in news_events
                                    if categorize_news_event(e) == "NORMAL"
                                ]
                                has_news = bool(normal_events)

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
                                # If at least 1 news-free IOU exists, eliminate this offset
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
                            body += f"<div class='card' style='padding:10px;'><strong>❌ {html.escape(filename)}</strong> - <span style='color:red;'>Hata: {html.escape(str(e))}</span></div>"

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
                self.wfile.write(page("app72 - IOU Results", body, active_tab="iou"))
                return

            except Exception as e:
                err_msg = f"<div class='card'><h3>Hata</h3><p style='color:red;'>{html.escape(str(e))}</p></div>"
                self.send_response(400)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(page("app72 - Hata", err_msg, active_tab="iou"))
                return

        try:
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

            if self.path == "/converter":
                candles = load_candles_from_text(text, ConverterCandle)
                if not candles:
                    raise ValueError("Veri boş veya çözümlenemedi")
                tf_est = estimate_timeframe_minutes(candles)
                if tf_est is None or abs(tf_est - 12) > 1.0:
                    raise ValueError("Girdi 12 dakikalık akış gibi görünmüyor")
                shifted, _ = adjust_to_output_tz(candles, "UTC-5")
                converted = convert_12m_to_72m(shifted)

                buffer = io.StringIO()
                writer = csv.writer(buffer)
                writer.writerow(["Time", "Open", "High", "Low", "Close"])
                for c in converted:
                    writer.writerow(
                        [
                            c.ts.strftime("%Y-%m-%d %H:%M:%S"),
                            format_price(c.open),
                            format_price(c.high),
                            format_price(c.low),
                            format_price(c.close),
                        ]
                    )
                data = buffer.getvalue().encode("utf-8")
                filename = file_obj.get("filename") or "converted.csv"
                if "." in filename:
                    base, _ = filename.rsplit(".", 1)
                    download_name = base + "_72m.csv"
                else:
                    download_name = filename + "_72m.csv"
                download_name = (
                    download_name.strip().replace('"', "") or "converted_72m.csv"
                )

                self.send_response(200)
                self.send_header("Content-Type", "text/csv; charset=utf-8")
                self.send_header(
                    "Content-Disposition", f'attachment; filename="{download_name}"'
                )
                self.end_headers()
                self.wfile.write(data)
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
                    f"<div><strong>Zaman Dilimi:</strong> 72m</div>",
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
                self.wfile.write(page("app72 sonuçlar", body, active_tab="analyze"))
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
                    f"<div><strong>Zaman Dilimi:</strong> 72m</div>"
                    f"<div><strong>Range:</strong> {html.escape(candles[0].ts.strftime('%Y-%m-%d %H:%M:%S'))} -> {html.escape(candles[-1].ts.strftime('%Y-%m-%d %H:%M:%S'))}</div>"
                    f"<div><strong>TZ:</strong> {html.escape(tz_label)}</div>"
                    f"<div><strong>DC count:</strong> {count}</div>"
                    f"</div>"
                )
                body = info + table
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(page("app72 DC List", body, active_tab="dc"))
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
                    f"<div><strong>Zaman Dilimi:</strong> 72m</div>"
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
                self.wfile.write(page("app72 Matrix", body, active_tab="matrix"))
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

    def log_message(self, format, *args):
        pass


def run(host: str, port: int) -> None:
    httpd = HTTPServer((host, port), App72Handler)
    print(f"app72 web: http://{host}:{port}/")
    httpd.serve_forever()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="app72.web", description="app72 için birleşik web arayüzü"
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="Sunucu adresi (vars: 127.0.0.1)"
    )
    parser.add_argument("--port", type=int, default=2172, help="Port (vars: 2172)")
    args = parser.parse_args(argv)
    run(args.host, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
