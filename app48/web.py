from http.server import HTTPServer, BaseHTTPRequestHandler
import argparse
import html
import io
from typing import List, Optional, Dict, Any

from .main import (
    Candle,
    SEQUENCES,
    SEQUENCES_FILTERED,
    normalize_key,
    parse_float,
    parse_time_value,
    estimate_timeframe_minutes,
    find_start_index,
    parse_tod,
    compute_dc_flags,
    compute_offset_alignment,
    adjust_to_output_tz,
    insert_synthetic_48m,
    convert_12m_to_48m,
    analyze_iou,
    IOUResult,
)
import csv
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

    rows: List[Candle] = []
    for row in reader:
        t = parse_time_value(row.get(time_key))
        o = parse_float(row.get(open_key))
        h = parse_float(row.get(high_key))
        l = parse_float(row.get(low_key))
        c = parse_float(row.get(close_key))
        if None in (t, o, h, l, c):
            continue
        rows.append(Candle(ts=t, open=o, high=h, low=l, close=c))
    rows.sort(key=lambda x: x.ts)
    return rows


def format_price(value: float) -> str:
    s = f"{value:.6f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


def format_pip(delta: Optional[float]) -> str:
    if delta is None:
        return "-"
    return f"{delta:+.5f}"


def page(title: str, body: str, active_tab: str = "analyze") -> bytes:
    html_doc = f"""<!doctype html>
<html>
  <head>
    <meta charset='utf-8'>
    <meta name='viewport' content='width=device-width, initial-scale=1'/>
    <title>{html.escape(title)}</title>
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
  <body>
    <header>
      <h2>app48</h2>
    </header>
    <nav class='tabs'>
      <a href='/' class='{ 'active' if active_tab=="analyze" else '' }'>Counter</a>
      <a href='/iou' class='{ 'active' if active_tab=="iou" else '' }'>IOU</a>
      <a href='/convert' class='{ 'active' if active_tab=="convert" else '' }'>12-48</a>
      <a href='/dc' class='{ 'active' if active_tab=="dc" else '' }'>DC List</a>
      <a href='/matrix' class='{ 'active' if active_tab=="matrix" else '' }'>Matrix</a>
    </nav>
    {body}
  </body>
</html>"""
    return html_doc.encode("utf-8")


def render_index() -> bytes:
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
            <div>48m</div>
          </div>
          <div>
            <label>Dizi</label>
            <select name='sequence'>
              <option value='S1'>S1</option>
              <option value='S2' selected>S2</option>
            </select>
          </div>
          <div>
            <label>Girdi TZ</label>
            <select name='input_tz'>
              <option value='UTC-5' selected>UTC-5</option>
              <option value='UTC-4'>UTC-4</option>
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
    return page("app48", body, active_tab="analyze")


def render_convert_index() -> bytes:
    body = """
    <div class='card'>
      <form method='post' action='/convert' enctype='multipart/form-data'>
        <div class='row'>
          <div>
            <label>CSV (12m, UTC-5)</label>
            <input type='file' name='csv' accept='.csv,text/csv' required />
          </div>
        </div>
        <div style='margin-top:12px;'>
          <button type='submit'>48m'e Dönüştür</button>
        </div>
      </form>
    </div>
    <p>Yalnızca 12 dakikalık mumlar desteklenir. Çıktı UTC-4 48m mumlarıdır ve otomatik indirme başlatılır.</p>
    <p>Örnek dosya: <code>ex12to48.csv</code></p>
    """
    return page("app48 - 12m to 48m", body, active_tab="convert")


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
            <div>48m</div>
          </div>
          <div>
            <label>Girdi TZ</label>
            <select name='input_tz'>
              <option value='UTC-5' selected>UTC-5</option>
              <option value='UTC-4'>UTC-4</option>
            </select>
          </div>
          <div>
            <label>Filtre</label>
            <div>
              <label><input type='checkbox' name='only_syn' /> Yalnız sentetik</label>
              <label><input type='checkbox' name='only_real' /> Yalnız gerçek</label>
            </div>
          </div>
        </div>
        <div style='margin-top:12px;'>
          <button type='submit'>DC'leri Listele</button>
        </div>
      </form>
    </div>
    <p>Not: DC tespiti 48m akışına göre, sentetik 18:00 & 18:48 eklenerek yapılır.</p>
    """
    return page("app48 - DC List", body, active_tab="dc")


def render_iou_index() -> bytes:
    body = """
    <div class='card'>
      <h3>IOU (Inverse OC - Uniform sign) Analizi</h3>
      <form method='post' action='/iou' enctype='multipart/form-data'>
        <div class='row'>
          <div>
            <label>CSV Dosyaları (1 haftalık 48m) - En fazla 25 dosya</label>
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
        </div>
        <div style='margin-top:12px;'>
          <button type='submit'>Analiz Et</button>
        </div>
      </form>
    </div>
    <p><strong>IOU Kriterleri:</strong> |OC| ≥ limit VE |PrevOC| ≥ limit VE aynı işaret (++ veya --)</p>
    <p>2 haftalık değil, <strong>1 haftalık 48m veri</strong> kullanılır.</p>
    """
    return page("app48 - IOU", body, active_tab="iou")


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
            <div>48m</div>
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
          <button type='submit'>Oluştur</button>
        </div>
      </form>
    </div>
    <p>Matrix: Tüm offsetler (-3..+3) için saatler ve (veri yoksa) tahminler.</p>
    """
    return page("app48 - Matrix", body, active_tab="matrix")


class AppHandler(BaseHTTPRequestHandler):
    def _parse_multipart(self) -> Dict[str, Any]:
        ct = self.headers.get("Content-Type", "")
        try:
            length = int(self.headers.get("Content-Length", "0") or 0)
        except Exception:
            length = 0
        body = self.rfile.read(length)
        if not ct.lower().startswith("multipart/form-data"):
            raise ValueError("Yalnızca multipart/form-data desteklenir")
        header_bytes = b"Content-Type: " + ct.encode("utf-8") + b"\r\nMIME-Version: 1.0\r\n\r\n"
        msg = BytesParser(policy=email_default).parsebytes(header_bytes + body)
        fields: Dict[str, Any] = {}
        for part in msg.iter_parts():
            cd = part.get("Content-Disposition", "")
            if not cd:
                continue
            params: Dict[str, str] = {}
            for item in cd.split(";"):
                item = item.strip()
                if "=" in item:
                    k, v = item.split("=", 1)
                    params[k.strip().lower()] = v.strip().strip('"')
            name = params.get("name")
            filename = params.get("filename")
            payload = part.get_payload(decode=True) or b""
            if not name:
                continue
            if filename is not None:
                fields[name] = {"filename": filename, "data": payload}
            else:
                charset = part.get_content_charset() or "utf-8"
                try:
                    value = payload.decode(charset, errors="replace")
                except Exception:
                    value = payload.decode("utf-8", errors="replace")
                fields[name] = {"value": value}
        return fields

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
        header_bytes = b"Content-Type: " + ct.encode("utf-8") + b"\r\nMIME-Version: 1.0\r\n\r\n"
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
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        if self.path.startswith("/iou"):
            self.wfile.write(render_iou_index())
        elif self.path.startswith("/dc"):
            self.wfile.write(render_dc_index())
        elif self.path.startswith("/convert"):
            self.wfile.write(render_convert_index())
        elif self.path.startswith("/matrix"):
            self.wfile.write(render_matrix_index())
        else:
            self.wfile.write(render_index())

    def do_POST(self):
        if self.path not in ("/analyze", "/dc", "/matrix", "/convert", "/iou"):
            self.send_error(404)
            return
        
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
                
                # Build HTML header
                body = f"""
                <div class='card'>
                  <h3>📊 IOU Analiz Sonuçları</h3>
                  <div><strong>Dosya Sayısı:</strong> {len(files)}</div>
                  <div><strong>Sequence:</strong> {html.escape(sequence)} (Filtered: {', '.join(map(str, SEQUENCES_FILTERED[sequence]))})</div>
                  <div><strong>Limit:</strong> {limit}</div>
                </div>
                """
                
                # Process each file
                for file_idx, file_obj in enumerate(files, 1):
                    filename = file_obj.get("filename", f"Dosya {file_idx}")
                    raw = file_obj["data"]
                    text = raw.decode("utf-8", errors="replace") if isinstance(raw, (bytes, bytearray)) else str(raw)
                    
                    try:
                        candles = load_candles_from_text(text)
                        if not candles:
                            body += f"<div class='card' style='padding:10px;'><strong>❌ {html.escape(filename)}</strong> - Veri boş</div>"
                            continue
                        
                        # Analyze IOU
                        results = analyze_iou(candles, sequence, limit)
                        total_iou = sum(len(v) for v in results.values())
                        
                        if total_iou == 0:
                            body += f"<div class='card' style='padding:10px;'><strong>📄 {html.escape(filename)}</strong> - <span style='color:#888;'>IOU yok</span></div>"
                            continue
                        
                        # Compact table with all offsets
                        body += f"""
                        <div class='card' style='padding:10px;'>
                          <strong>📄 {html.escape(filename)}</strong> - {len(candles)} mum, <strong>{total_iou} IOU</strong>
                          <table style='margin-top:8px;'>
                            <tr><th>Ofs</th><th>Seq</th><th>Idx</th><th>Timestamp</th><th>OC</th><th>PrevOC</th><th>PIdx</th></tr>
                        """
                        
                        for offset in range(-3, 4):
                            for iou in results[offset]:
                                oc_fmt = format_pip(iou.oc)
                                prev_oc_fmt = format_pip(iou.prev_oc)
                                body += f"<tr><td>{offset:+d}</td><td>{iou.seq_value}</td><td>{iou.index}</td><td>{iou.timestamp.strftime('%m-%d %H:%M')}</td><td>{html.escape(oc_fmt)}</td><td>{html.escape(prev_oc_fmt)}</td><td>{iou.prev_index}</td></tr>"
                        
                        body += "</table></div>"
                        
                    except Exception as e:
                        body += f"<div class='card' style='padding:10px;'><strong>❌ {html.escape(filename)}</strong> - <span style='color:red;'>Hata: {html.escape(str(e))}</span></div>"
                
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(page("app48 - IOU Results", body, active_tab="iou"))
                return
                
            except Exception as e:
                err_msg = f"<div class='card'><h3>Hata</h3><p style='color:red;'>{html.escape(str(e))}</p></div>"
                self.send_response(400)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(page("app48 - Hata", err_msg, active_tab="iou"))
                return
        
        try:
            form = self._parse_multipart()

            file_item = form.get("csv")
            if not file_item or "data" not in file_item:
                raise ValueError("CSV yüklenmedi")

            raw = file_item["data"]
            text = raw.decode("utf-8", errors="replace")

            sequence = (form.get("sequence", {}).get("value") or "S2").strip()
            tz_s = (form.get("input_tz", {}).get("value") or "UTC-5").strip()
            offset_s = (form.get("offset", {}).get("value") or "0").strip() if self.path == "/analyze" else "0"
            show_dc = ("show_dc" in form) if self.path == "/analyze" else False
            only_syn = ("only_syn" in form) if self.path == "/dc" else False
            only_real = ("only_real" in form) if self.path == "/dc" else False

            candles = load_candles_from_text(text)
            if not candles:
                raise ValueError("Veri boş veya çözümlenemedi")

            if self.path == "/convert":
                tf_est = estimate_timeframe_minutes(candles)
                if tf_est is None or abs(tf_est - 12) > 0.6:
                    raise ValueError("Girdi 12 dakikalık akış gibi görünmüyor")
                shifted, _ = adjust_to_output_tz(candles, "UTC-5")
                converted = convert_12m_to_48m(shifted)

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
                filename = file_item.get("filename") or "converted.csv"
                if "." in filename:
                    base, _ = filename.rsplit(".", 1)
                    download_name = base + "_48m.csv"
                else:
                    download_name = filename + "_48m.csv"
                download_name = download_name.strip().replace('"', '') or "converted_48m.csv"

                self.send_response(200)
                self.send_header("Content-Type", "text/csv; charset=utf-8")
                self.send_header("Content-Disposition", f"attachment; filename=\"{download_name}\"")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return

            # Normalize to UTC-4 if needed
            candles, tz_label = adjust_to_output_tz(candles, tz_s)

            # Analiz/matrix için sentetik ekleme
            start_tod = parse_tod("18:00")
            base_idx, align_status = find_start_index(candles, start_tod)
            start_day = candles[base_idx].ts.date() if 0 <= base_idx < len(candles) else None
            candles, added = insert_synthetic_48m(candles, start_day)

            if self.path == "/analyze":
                # Re-find after insertion
                base_idx, align_status = find_start_index(candles, start_tod)
                try:
                    off = int(offset_s)
                except Exception:
                    off = 0
                if off < -3 or off > 3:
                    off = 0
                seq_values = SEQUENCES.get(sequence, SEQUENCES["S2"])[:]

                dc_flags_all = compute_dc_flags(candles)
                alignment = compute_offset_alignment(candles, dc_flags_all, base_idx, seq_values, off, minutes_per_step=48)
                start_idx = alignment.start_idx
                start_ref_ts = alignment.start_ref_ts

                def predicted_ts_for(v: int) -> str:
                    # 48m prediction - DC'leri dikkate al
                    first = seq_values[0]
                    use_target = alignment.missing_steps and v <= alignment.missing_steps
                    
                    if not use_target:
                        # Son dizideki bilinen değeri bul
                        last_known_v = None
                        last_known_ts = None
                        last_known_idx = -1
                        for seq_v, seq_hit in zip(seq_values, alignment.hits):
                            if seq_hit.idx is not None and seq_hit.ts is not None and 0 <= seq_hit.idx < len(candles):
                                last_known_v = seq_v
                                last_known_ts = seq_hit.ts
                                last_known_idx = seq_hit.idx
                        
                        if last_known_v is not None and v > last_known_v:
                            # Son gerçek mumdan başla
                            actual_last_candle_ts = candles[-1].ts
                            actual_last_idx = len(candles) - 1
                            # DC'leri dikkate al
                            non_dc_steps_from_last_known_to_end = 0
                            for i in range(last_known_idx + 1, actual_last_idx + 1):
                                is_dc = dc_flags_all[i] if i < len(dc_flags_all) else False
                                if not is_dc:
                                    non_dc_steps_from_last_known_to_end += 1
                            steps_from_end_to_v = (v - last_known_v) - non_dc_steps_from_last_known_to_end
                            return (actual_last_candle_ts + __import__('datetime').timedelta(minutes=48 * steps_from_end_to_v)).strftime("%Y-%m-%d %H:%M:%S")
                    
                    delta_steps = max(0, v - first)
                    base_ts = alignment.target_ts if use_target else start_ref_ts
                    return (base_ts + __import__('datetime').timedelta(minutes=48*delta_steps)).strftime("%Y-%m-%d %H:%M:%S")

                rows_html = []
                for v, hit in zip(seq_values, alignment.hits):
                    idx = hit.idx
                    ts = hit.ts
                    if idx is None or ts is None or not (0 <= idx < len(candles)):
                        pred_ts = predicted_ts_for(v)
                        pred_cell = f"{pred_ts} (pred, OC -, PrevOC -)"
                        if show_dc:
                            rows_html.append(f"<tr><td>{v}</td><td>-</td><td>{html.escape(pred_cell)}</td><td>-</td></tr>")
                        else:
                            rows_html.append(f"<tr><td>{v}</td><td>-</td><td>{html.escape(pred_cell)}</td></tr>")
                        continue
                    ts_s = ts.strftime("%Y-%m-%d %H:%M:%S")
                    syn_tag = " <em>(syn)</em>" if hit.synthetic else ""
                    pip_label = format_pip(candles[idx].close - candles[idx].open)
                    prev_label = format_pip(candles[idx - 1].close - candles[idx - 1].open) if idx - 1 >= 0 else "-"
                    ts_with_pip = f"{ts_s} (OC {pip_label}, PrevOC {prev_label}){syn_tag}"
                    if show_dc:
                        dc = dc_flags_all[idx]
                        dc_label = f"{dc}"
                        if hit.used_dc:
                            dc_label += " (rule)"
                        rows_html.append(f"<tr><td>{v}</td><td>{idx}</td><td>{html.escape(ts_with_pip)}</td><td>{dc_label}</td></tr>")
                    else:
                        rows_html.append(f"<tr><td>{v}</td><td>{idx}</td><td>{html.escape(ts_with_pip)}</td></tr>")

                target_s = html.escape(alignment.target_ts.strftime('%Y-%m-%d %H:%M:%S')) if alignment.target_ts else "-"
                actual_s = html.escape(alignment.actual_ts.strftime('%Y-%m-%d %H:%M:%S')) if alignment.actual_ts else "-"
                start_idx_s = str(start_idx) if start_idx is not None else "-"

                info_lines = [
                    f"<div><strong>Data:</strong> {len(candles)} candles</div>",
                    f"<div><strong>Zaman Dilimi:</strong> 48m</div>",
                    f"<div><strong>Range:</strong> {html.escape(candles[0].ts.strftime('%Y-%m-%d %H:%M:%S'))} -> {html.escape(candles[-1].ts.strftime('%Y-%m-%d %H:%M:%S'))}</div>",
                    f"<div><strong>TZ:</strong> {html.escape(tz_label)}</div>",
                    f"<div><strong>Synthetic:</strong> inserted {added} candles (days after start)</div>",
                    f"<div><strong>Start:</strong> base_idx={base_idx} ts={html.escape(candles[base_idx].ts.strftime('%Y-%m-%d %H:%M:%S'))} ({align_status}); offset={off} =&gt; target_ts={target_s} ({alignment.offset_status}) idx={start_idx_s} actual_ts={actual_s} missing_steps={alignment.missing_steps}</div>",
                    f"<div><strong>Sequence:</strong> {html.escape(sequence)} {html.escape(str(seq_values))}</div>",
                ]

                if show_dc:
                    header = "<tr><th>Seq</th><th>Index</th><th>Timestamp</th><th>DC</th></tr>"
                else:
                    header = "<tr><th>Seq</th><th>Index</th><th>Timestamp</th></tr>"

                table = f"<table><thead>{header}</thead><tbody>{''.join(rows_html)}</tbody></table>"
                body = "<div class='card'>" + "".join(info_lines) + "</div>" + table
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(page("app48 sonuçlar", body, active_tab="analyze"))
            elif self.path == "/dc":
                # DC list branch
                flags = compute_dc_flags(candles)
                rows_html = []
                count = 0
                for i, c in enumerate(candles):
                    if not flags[i]:
                        continue
                    if only_syn and not getattr(c, "synthetic", False):
                        continue
                    if only_real and getattr(c, "synthetic", False):
                        continue
                    tag = "syn" if getattr(c, "synthetic", False) else "real"
                    ts = c.ts.strftime("%Y-%m-%d %H:%M:%S")
                    rows_html.append(f"<tr><td>{i}</td><td>{html.escape(ts)}</td><td>{tag}</td><td>{c.open}</td><td>{c.high}</td><td>{c.low}</td><td>{c.close}</td></tr>")
                    count += 1

                header = "<tr><th>Index</th><th>Timestamp</th><th>Tag</th><th>Open</th><th>High</th><th>Low</th><th>Close</th></tr>"
                table = f"<table><thead>{header}</thead><tbody>{''.join(rows_html)}</tbody></table>"
                info = (
                    f"<div class='card'>"
                    f"<div><strong>Data:</strong> {len(candles)} candles</div>"
                    f"<div><strong>Zaman Dilimi:</strong> 48m</div>"
                    f"<div><strong>TZ:</strong> {html.escape(tz_label)}</div>"
                    f"<div><strong>DC count:</strong> {count}</div>"
                    f"</div>"
                )
                body = info + table
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(page("app48 DC List", body, active_tab="dc"))
            elif self.path == "/matrix":
                # Matrix branch
                seq_values = SEQUENCES.get(sequence or "S2", SEQUENCES["S2"])[:]
                base_idx, align_status = find_start_index(candles, start_tod)
                dc_flags_all = compute_dc_flags(candles)
                offsets = [-3, -2, -1, 0, 1, 2, 3]
                per_offset = {
                    o: compute_offset_alignment(candles, dc_flags_all, base_idx, seq_values, o, minutes_per_step=48)
                    for o in offsets
                }

                rows = []
                for vi, v in enumerate(seq_values):
                    cells = [f"<td>{v}</td>"]
                    for o in offsets:
                        align_o = per_offset[o]
                        hit = align_o.hits[vi] if vi < len(align_o.hits) else None
                        idx = hit.idx if hit else None
                        ts = hit.ts if hit else None
                        if idx is not None and ts is not None and 0 <= idx < len(candles):
                            ts_s = ts.strftime('%Y-%m-%d %H:%M:%S')
                            oc_label = format_pip(candles[idx].close - candles[idx].open)
                            prev_label = format_pip(candles[idx - 1].close - candles[idx - 1].open) if idx - 1 >= 0 else "-"
                            label = f"{ts_s} (OC {oc_label}, PrevOC {prev_label})"
                            if hit.synthetic:
                                label += " (syn)"
                            if hit.used_dc:
                                label += " (DC)"
                            cells.append(f"<td>{html.escape(label)}</td>")
                        else:
                            first = seq_values[0]
                            delta_steps = max(0, v - first)
                            use_target = align_o.missing_steps and v <= align_o.missing_steps
                            base_ts = align_o.target_ts if use_target else align_o.start_ref_ts
                            pred_ts = (base_ts + __import__('datetime').timedelta(minutes=48*delta_steps)).strftime('%Y-%m-%d %H:%M:%S')
                            cells.append(f"<td>{html.escape(pred_ts)} (pred, OC -, PrevOC -)</td>")
                    rows.append(f"<tr>{''.join(cells)}</tr>")

                header_cells = ''.join(f"<th>{'+'+str(o) if o>0 else str(o)}</th>" for o in offsets)
                thead = f"<tr><th>Seq</th>{header_cells}</tr>"
                table = f"<table><thead>{thead}</thead><tbody>{''.join(rows)}</tbody></table>"

                status_summary = ', '.join(
                    f"{('+' + str(o)) if o > 0 else str(o)}: {per_offset[o].offset_status}"
                    for o in offsets
                )

                info = (
                    f"<div class='card'>"
                    f"<div><strong>Data:</strong> {len(candles)} candles</div>"
                    f"<div><strong>Zaman Dilimi:</strong> 48m</div>"
                    f"<div><strong>Range:</strong> {html.escape(candles[0].ts.strftime('%Y-%m-%d %H:%M:%S'))} -> {html.escape(candles[-1].ts.strftime('%Y-%m-%d %H:%M:%S'))}</div>"
                    f"<div><strong>TZ:</strong> {html.escape(tz_label)}</div>"
                    f"<div><strong>Synthetic:</strong> inserted {added} candles (days after start)</div>"
                    f"<div><strong>Sequence:</strong> {html.escape(sequence or 'S2')}</div>"
                    f"<div><strong>Offset durumları:</strong> {html.escape(status_summary)}</div>"
                    f"</div>"
                )

                body = info + table
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(page("app48 - Matrix", body, active_tab="matrix"))
            else:
                self.send_error(400)
                return
        except Exception as e:
            msg = html.escape(str(e) or "Bilinmeyen hata")
            self.send_response(400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(page("Hata", f"<p>Hata: {msg}</p><p><a href='/'>&larr; Geri</a></p>"))

    def log_message(self, format, *args):
        pass


def run(host: str, port: int):
    httpd = HTTPServer((host, port), AppHandler)
    print(f"app48 web: http://{host}:{port}/")
    httpd.serve_forever()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="app48.web", description="app48 için basit web arayüzü")
    parser.add_argument("--host", default="127.0.0.1", help="Sunucu adresi (vars: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=2020, help="Port (vars: 2020)")
    args = parser.parse_args(argv)
    run(args.host, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
