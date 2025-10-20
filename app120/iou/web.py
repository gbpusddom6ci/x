from http.server import HTTPServer, BaseHTTPRequestHandler
import argparse
import html
import io
import csv
import json
import os
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from .counter import (
    analyze_iou,
    load_candles,
    fmt_ts,
    fmt_pip,
    SEQUENCES_FILTERED,
    IOUResult,
    Candle,
    normalize_key,
    parse_float,
    parse_time_value,
)
from email.parser import BytesParser
from email.policy import default as email_default


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


def is_holiday_event(event: Dict[str, Any]) -> bool:
    """
    Check if an event is a holiday (should not affect XYZ analysis).
    Holidays are identified by title containing 'Holiday' or 'Bank Holiday'.
    """
    title = event.get("title", "").lower()
    return "holiday" in title


def categorize_news_event(event: Dict[str, Any]) -> str:
    """
    Categorize news event into one of four types:
    - HOLIDAY: title contains 'holiday' + All Day + null values
    - SPEECH: has time_24h + null values (speeches, statements)
    - ALLDAY: All Day + null values (but not holiday)
    - NORMAL: has time_24h + has values (actual/forecast/previous)

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
    elif time_24h and is_null:
        return "SPEECH"
    elif is_all_day and is_null:
        return "ALLDAY"
    elif time_24h and has_values:
        return "NORMAL"

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
        raise ValueError(
            "CSV başlıkları eksik. Gerekli: Time, Open, High, Low, Close (Last)"
        )

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
    </style>
  </head>
  <body>
    <header>
      <h1>🎯 app120_iou - IOU Candle Analysis</h1>
      <p>Inverse OC - Uniform sign (IOU) mum analizi - 120m timeframe</p>
    </header>
    {body}
  </body>
</html>
"""
    return html_doc.encode("utf-8")


def render_index() -> bytes:
    body = """
    <div class='card'>
      <h2>IOU Analizi</h2>
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
        <label>Tolerance (güvenlik payı):</label>
        <input type='number' name='tolerance' step='0.001' value='0.005' min='0' required />
        <div>
          <label>
            <input type='checkbox' name='xyz_analysis' /> XYZ Küme Analizi
          </label>
        </div>

        <button type='submit'>Analiz Et</button>
      </form>
    </div>
    <div class='card'>
      <h3>ℹ️ IOU Mum Nedir?</h3>
      <p><strong>IOU (Inverse OC - Uniform sign)</strong> mumu, aşağıdaki kriterleri karşılayan özel mumlardır:</p>
      <ul>
        <li><strong>|OC| ≥ Limit</strong> - Mumun open-close farkı limit değerinin üstünde olmalı</li>
        <li><strong>|PrevOC| ≥ Limit</strong> - Önceki mumun open-close farkı limit değerinin üstünde olmalı</li>
        <li><strong>Aynı İşaret</strong> - OC ve PrevOC her ikisi de (+) VEYA her ikisi de (-) olmalı</li>
      </ul>
      <p><strong>Not:</strong> S1 için 1 ve 3 değerleri, S2 için 1 ve 5 değerleri analiz edilmez.</p>
      <p><strong>XYZ Analizi:</strong> Habersiz IOU içeren offsetler elenir, kalan offsetler XYZ kümesini oluşturur.</p>
    </div>
    """
    return page("app120_iou", body)


def render_results(
    candles: List[Candle],
    sequence: str,
    limit: float,
    results: Dict[int, List[IOUResult]],
    xyz_analysis: bool = False,
    events_by_date: Optional[Dict[str, List[Dict[str, Any]]]] = None,
) -> bytes:
    total_iou = sum(len(v) for v in results.values())

    body = f"""
    <div class='card'>
      <h2>📊 Analiz Sonuçları</h2>
      <div class='summary'>
        <strong>📁 Veri:</strong> {len(candles)} mum ({fmt_ts(candles[0].ts)} → {fmt_ts(candles[-1].ts)})<br>
        <strong>🔢 Sequence:</strong> {sequence} (Filtered: {", ".join(map(str, SEQUENCES_FILTERED[sequence]))})<br>
        <strong>📏 Limit:</strong> {limit}<br>
        <strong>🎯 Toplam IOU Mum:</strong> {total_iou}<br>
        <strong>🎯 XYZ Analizi:</strong> {"✅ Aktif" if xyz_analysis else "❌ Pasif"}
      </div>
    </div>
    """

    # XYZ Analysis: Track news-free IOUs per offset
    if xyz_analysis:
        file_xyz_data = {
            offset: {"news_free": 0, "with_news": 0} for offset in range(-3, 4)
        }

    # Only show offsets with IOU candles
    for offset in range(-3, 4):
        iou_list = results[offset]

        if iou_list:  # Only display if there are IOU candles
            body += f"""
            <div class='iou-section'>
              <h3>Offset: {offset:+d} ({len(iou_list)} IOU mum)</h3>
            """

            for iou in iou_list:
                oc_class = "oc-positive" if iou.oc > 0 else "oc-negative"
                prev_oc_class = "oc-positive" if iou.prev_oc > 0 else "oc-negative"

                # Check for news if xyz_analysis is enabled
                news_text = "-"
                has_news = False
                if xyz_analysis and events_by_date:
                    news_events = find_news_in_timerange(
                        events_by_date, iou.timestamp, 120
                    )
                    news_text = format_news_events(news_events)

                    # For XYZ analysis: only NORMAL category events count as "news"
                    # HOLIDAY, SPEECH, ALLDAY events are shown but don't affect XYZ filtering
                    normal_events = [
                        e for e in news_events if categorize_news_event(e) == "NORMAL"
                    ]
                    has_news = bool(normal_events)

                    # Track for XYZ analysis
                    if has_news:
                        file_xyz_data[offset]["with_news"] += 1
                    else:
                        file_xyz_data[offset]["news_free"] += 1

                body += f"""
                <div class='iou-item'>
                  <span class='seq-badge'>Seq {iou.seq_value}</span>
                  <span class='timestamp'>Index: {iou.index} | {fmt_ts(iou.timestamp)}</span>
                  <div class='oc-values'>
                    <strong>OC:</strong> <span class='{oc_class}'>{fmt_pip(iou.oc)}</span> |
                    <strong>PrevOC:</strong> <span class='{prev_oc_class}'>{fmt_pip(iou.prev_oc)}</span>
                    <span style='color:#888;'>(Prev Index: {iou.prev_index}, {fmt_ts(iou.prev_timestamp)})</span>
                """

                if xyz_analysis:
                    body += f"<br><strong>Haber:</strong> <span style='font-size:11px;'>{html.escape(news_text)}</span>"

                body += """
                  </div>
                </div>
                """

            body += "</div>"

    # Display XYZ Set Analysis Results
    if xyz_analysis:
        xyz_set = []
        eliminated = []

        for offset in range(-3, 4):
            news_free_count = file_xyz_data[offset]["news_free"]
            if news_free_count > 0:
                eliminated.append(offset)
            else:
                xyz_set.append(offset)

        xyz_set_str = ", ".join([f"{o:+d}" if o != 0 else "0" for o in xyz_set])
        eliminated_str = ", ".join([f"{o:+d}" if o != 0 else "0" for o in eliminated])

        body += f"""
        <div class='card' style='background:#e8f0fe; border-left:4px solid #1a73e8;'>
          <h3>🎯 XYZ Küme Analizi</h3>
          <p><strong>Mantık:</strong> Habersiz IOU içeren offsetler elenir.</p>
          <div class='summary'>
            <strong>XYZ Kümesi:</strong> <code style='background:#fff; padding:4px 8px; border-radius:4px;'>{html.escape(xyz_set_str) if xyz_set else "Ø (boş)"}</code><br>
            <strong>Elenen Offsetler:</strong> <code style='background:#fff; padding:4px 8px; border-radius:4px;'>{html.escape(eliminated_str) if eliminated else "Ø (yok)"}</code>
          </div>
          <table style='margin-top:12px;'>
            <thead>
              <tr><th>Offset</th><th>Habersiz IOU</th><th>Haberli IOU</th><th>Durum</th></tr>
            </thead>
            <tbody>
        """

        for offset in range(-3, 4):
            nf = file_xyz_data[offset]["news_free"]
            wn = file_xyz_data[offset]["with_news"]
            status = "❌ Elendi" if offset in eliminated else "✅ XYZ'de"
            offset_str = f"{offset:+d}" if offset != 0 else "0"
            body += f"<tr><td>{offset_str}</td><td>{nf}</td><td>{wn}</td><td>{status}</td></tr>"

        body += """
            </tbody>
          </table>
        </div>
        """

    body += """
    <div class='card'>
      <a href='/' style='text-decoration:none;'>
        <button>← Yeni Analiz</button>
      </a>
    </div>
    """

    return page("IOU Analysis Results", body)


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
                tolerance = 0.005
                xyz_analysis = False

                for part in msg.iter_parts():
                    name = part.get_param("name", header="content-disposition")
                    if name == "csv":
                        csv_text = part.get_content()
                    elif name == "sequence":
                        sequence = part.get_content().strip()
                    elif name == "limit":
                        limit = float(part.get_content().strip())
                    elif name == "tolerance":
                        tolerance = float(part.get_content().strip())
                    elif name == "xyz_analysis":
                        xyz_analysis = True

                if not csv_text:
                    raise ValueError("CSV dosyası yüklenemedi")

                candles = load_candles_from_text(csv_text)
                if not candles:
                    raise ValueError("CSV verisi boş")

                results = analyze_iou(candles, sequence, limit, tolerance)

                # Load news data if xyz_analysis is enabled
                events_by_date = None
                if xyz_analysis:
                    news_dir = os.path.join(
                        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                        "news_data",
                    )
                    events_by_date = load_news_data_from_directory(news_dir)

                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(
                    render_results(
                        candles, sequence, limit, results, xyz_analysis, events_by_date
                    )
                )

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
    print(f"app120.iou web: http://{host}:{port}/")
    server.serve_forever()


def main(argv=None):
    parser = argparse.ArgumentParser(prog="app120.iou.web")
    parser.add_argument(
        "--port", type=int, default=2121, help="HTTP port (default: 2121)"
    )
    parser.add_argument(
        "--host", default="0.0.0.0", help="Host to bind (default: 0.0.0.0)"
    )
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
