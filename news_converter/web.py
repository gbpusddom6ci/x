from http.server import HTTPServer, BaseHTTPRequestHandler
import argparse
import html
import json
import os
from typing import List, Dict, Any

from .parser import parse_markdown_to_json
from email.parser import BytesParser
from email.policy import default as email_default


def page(title: str, body: str) -> bytes:
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
      .success{{color:#0a8a0a; font-weight:600;}}
      .error{{color:#d32f2f; font-weight:600;}}
    </style>
  </head>
  <body>
    <header>
      <h2>News Converter (MD → JSON)</h2>
    </header>
    {body}
  </body>
</html>"""
    return html_doc.encode("utf-8")


def render_index() -> bytes:
    body = """
    <div class='card'>
      <h3>📰 Haber Verilerini Dönüştür</h3>
      <form method='post' action='/convert' enctype='multipart/form-data'>
        <div class='row'>
          <div>
            <label>Markdown Dosyaları (.md) - En fazla 10 dosya</label>
            <input type='file' name='md' accept='.md,text/markdown' multiple required />
          </div>
        </div>
        <div style='margin-top:12px;'>
          <button type='submit'>Dönüştür ve İndir</button>
        </div>
      </form>
    </div>
    <div class='card'>
      <h4>📋 Format Bilgisi</h4>
      <p><strong>Giriş:</strong> ForexFactory tarzı markdown format (3augto6sep.md gibi)</p>
      <p><strong>Çıkış:</strong> JSON format (news_data klasöründe kullanılan format)</p>
      <p><strong>Özellikler:</strong></p>
      <ul>
        <li>✅ Çoklu dosya desteği (tek seferde birden fazla dosya)</li>
        <li>✅ Otomatik yıl tespiti (geçmiş ve gelecek tarihler)</li>
        <li>✅ 12 saat → 24 saat dönüşümü</li>
        <li>✅ Direkt indirme (tek dosya için .json, çoklu için .zip)</li>
      </ul>
    </div>
    """
    return page("News Converter", body)


class NewsConverterHandler(BaseHTTPRequestHandler):
    def _parse_multipart_multiple_files(self) -> Dict[str, Any]:
        """Parse multipart with multiple file support."""
        ct = self.headers.get("Content-Type", "")
        try:
            length = int(self.headers.get("Content-Length", "0") or 0)
        except Exception:
            length = 0
        # File upload size limit: 50 MB
        MAX_UPLOAD_SIZE = 50 * 1024 * 1024
        if length > MAX_UPLOAD_SIZE:
            raise ValueError(f"Dosya boyutu çok büyük (maksimum {MAX_UPLOAD_SIZE // (1024*1024)} MB)")
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
        # Serve favicon files
        if self.path.startswith("/favicon/"):
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
                return
            except FileNotFoundError:
                self.send_error(404, "Favicon not found")
                return
        
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(render_index())
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path != "/convert":
            self.send_error(404)
            return
        
        try:
            form_data = self._parse_multipart_multiple_files()
            files = form_data["files"]
            
            if not files:
                raise ValueError("En az bir MD dosyası yükleyin")
            if len(files) > 10:
                raise ValueError("En fazla 10 dosya yükleyebilirsiniz")
            
            # Convert all files
            converted_files: List[Dict[str, Any]] = []
            for file_obj in files:
                filename = file_obj.get("filename", "unknown.md")
                raw = file_obj["data"]
                text = raw.decode("utf-8", errors="replace") if isinstance(raw, (bytes, bytearray)) else str(raw)
                
                try:
                    # Parse MD to JSON
                    json_data = parse_markdown_to_json(text, filename)
                    
                    # Generate output filename
                    if filename.endswith(".md"):
                        json_filename = filename[:-3] + ".json"
                    else:
                        json_filename = filename + ".json"
                    
                    converted_files.append({
                        "filename": json_filename,
                        "data": json_data,
                        "success": True,
                        "source": filename
                    })
                except Exception as e:
                    converted_files.append({
                        "filename": filename,
                        "data": None,
                        "success": False,
                        "error": str(e),
                        "source": filename
                    })
            
            # If single file, return JSON directly
            if len(converted_files) == 1:
                result = converted_files[0]
                if result["success"]:
                    json_str = json.dumps(result["data"], indent=2, ensure_ascii=False)
                    json_bytes = json_str.encode("utf-8")
                    
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Content-Disposition", f'attachment; filename="{result["filename"]}"')
                    self.send_header("Content-Length", str(len(json_bytes)))
                    self.end_headers()
                    self.wfile.write(json_bytes)
                else:
                    raise ValueError(f"Dönüştürme hatası: {result['error']}")
            else:
                # Multiple files: create ZIP
                import io
                import zipfile
                
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for result in converted_files:
                        if result["success"]:
                            json_str = json.dumps(result["data"], indent=2, ensure_ascii=False)
                            zip_file.writestr(result["filename"], json_str)
                        else:
                            # Add error log
                            error_filename = result["filename"] + ".error.txt"
                            zip_file.writestr(error_filename, f"Error: {result['error']}")
                
                zip_bytes = zip_buffer.getvalue()
                
                self.send_response(200)
                self.send_header("Content-Type", "application/zip")
                self.send_header("Content-Disposition", 'attachment; filename="news_converted.zip"')
                self.send_header("Content-Length", str(len(zip_bytes)))
                self.end_headers()
                self.wfile.write(zip_bytes)
            
        except Exception as e:
            err_msg = f"<div class='card'><h3>Hata</h3><p class='error'>{html.escape(str(e))}</p></div>"
            self.send_response(400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(page("News Converter - Hata", err_msg))

    def log_message(self, format, *args):
        pass


def run(host: str, port: int) -> None:
    server = HTTPServer((host, port), NewsConverterHandler)
    print(f"news_converter web: http://{host}:{port}/")
    server.serve_forever()


def main(argv: List[str] = None) -> int:
    parser = argparse.ArgumentParser(prog="news_converter.web", description="MD to JSON news converter")
    parser.add_argument("--host", default="127.0.0.1", help="Server address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=2199, help="Port (default: 2199)")
    args = parser.parse_args(argv)
    
    run(args.host, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
