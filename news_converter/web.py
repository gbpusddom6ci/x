from http.server import HTTPServer, BaseHTTPRequestHandler
import argparse
import html
import json
import os
import urllib.parse
from datetime import datetime

from .parser import parse_markdown_to_json


def build_html() -> bytes:
    """Build the HTML page for the converter."""
    page = """<!doctype html>
<html lang='tr'>
  <head>
    <meta charset='utf-8'>
    <meta name='viewport' content='width=device-width, initial-scale=1'>
    <title>News Data Converter (MD → JSON)</title>
    <link rel="icon" type="image/png" sizes="32x32" href="/favicon/favicon-32x32.png?v=2">
    <link rel="icon" type="image/png" sizes="16x16" href="/favicon/favicon-16x16.png?v=2">
    <link rel="shortcut icon" href="/favicon/favicon.ico?v=2">
    <style>
      :root {
        color-scheme: light dark;
        --bg: #f5f5f5;
        --fg: #1f1f1f;
        --card-bg: #ffffff;
        --border: #d9d9d9;
        --accent: #0f62fe;
        --success: #24a148;
        --error: #da1e28;
      }
      @media (prefers-color-scheme: dark) {
        :root {
          --bg: #121212;
          --fg: #f3f3f3;
          --card-bg: #1f1f1f;
          --border: #333333;
        }
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace;
        background: var(--bg);
        color: var(--fg);
        min-height: 100vh;
        padding: 24px 16px;
      }
      .container {
        max-width: 1400px;
        margin: 0 auto;
      }
      header {
        text-align: center;
        margin-bottom: 32px;
      }
      header h1 {
        margin: 0 0 8px;
        font-size: 1.8rem;
      }
      header p {
        margin: 0;
        opacity: 0.8;
      }
      .grid {
        display: grid;
        gap: 24px;
        grid-template-columns: 1fr;
      }
      @media (min-width: 1024px) {
        .grid {
          grid-template-columns: 1fr 1fr;
        }
      }
      .card {
        background: var(--card-bg);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 24px;
      }
      .card h2 {
        margin: 0 0 16px;
        font-size: 1.2rem;
      }
      textarea, pre {
        width: 100%;
        min-height: 400px;
        padding: 12px;
        border: 1px solid var(--border);
        border-radius: 8px;
        font-family: 'Monaco', 'Courier New', monospace;
        font-size: 0.85rem;
        background: var(--bg);
        color: var(--fg);
        resize: vertical;
      }
      pre {
        overflow: auto;
        margin: 0;
      }
      .buttons {
        display: flex;
        gap: 12px;
        margin-top: 16px;
        flex-wrap: wrap;
      }
      button, .button {
        padding: 10px 20px;
        border-radius: 8px;
        border: none;
        font-weight: 600;
        cursor: pointer;
        transition: all 150ms;
        text-decoration: none;
        display: inline-block;
      }
      .btn-primary {
        background: var(--accent);
        color: white;
      }
      .btn-success {
        background: var(--success);
        color: white;
      }
      .btn-secondary {
        background: var(--border);
        color: var(--fg);
      }
      button:hover, .button:hover {
        filter: brightness(1.1);
        transform: translateY(-1px);
      }
      button:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }
      .info {
        margin-top: 16px;
        padding: 12px;
        border-radius: 8px;
        background: var(--bg);
        font-size: 0.9rem;
      }
      .info.success {
        border-left: 4px solid var(--success);
      }
      .info.error {
        border-left: 4px solid var(--error);
      }
      .hidden {
        display: none;
      }
      .year-input {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 12px;
      }
      .year-input input {
        width: 100px;
        padding: 6px 12px;
        border: 1px solid var(--border);
        border-radius: 6px;
        background: var(--bg);
        color: var(--fg);
        font-size: 0.95rem;
      }
      .file-input-wrapper {
        margin-bottom: 12px;
      }
      .file-input-wrapper input[type="file"] {
        display: none;
      }
      .file-upload-btn {
        display: inline-block;
        padding: 8px 16px;
        background: var(--secondary);
        color: white;
        border-radius: 6px;
        cursor: pointer;
        font-size: 0.9rem;
        transition: all 0.2s;
      }
      .file-upload-btn:hover {
        background: var(--primary);
        transform: translateY(-1px);
      }
      .file-name {
        margin-left: 12px;
        color: var(--success);
        font-size: 0.85rem;
      }
    </style>
  </head>
  <body>
    <div class='container'>
      <header>
        <h1>📰 News Data Converter</h1>
        <p>Markdown formatını JSON'a çevirin ve news_data/ klasörüne kaydedin</p>
      </header>

      <div class='grid'>
        <!-- Input Section -->
        <div class='card'>
          <h2>📝 Markdown Input</h2>
          <div class='year-input'>
            <label for='year'>Yıl:</label>
            <input type='number' id='year' value='2025' min='2020' max='2030'>
          </div>
          <div class='file-input-wrapper'>
            <label for='fileInput' class='file-upload-btn'>📁 .md Dosyası Yükle</label>
            <input type='file' id='fileInput' accept='.md,.txt' onchange='loadFile()'>
            <span id='fileName' class='file-name'></span>
          </div>
          <textarea id='mdInput' placeholder='Sun
Mar 30
9:30pm
CNY
Manufacturing PMI
50.5	50.4	50.2
...

Markdown formatınızı buraya yapıştırın veya yukarıdan .md dosyası yükleyin...'></textarea>
          <div class='buttons'>
            <button class='btn-primary' onclick='convert()'>🔄 Convert to JSON</button>
            <button class='btn-secondary' onclick='clearInput()'>🗑️ Clear</button>
          </div>
          <div id='inputInfo' class='info hidden'></div>
        </div>

        <!-- Output Section -->
        <div class='card'>
          <h2>📄 JSON Output</h2>
          <pre id='jsonOutput'>JSON çıktısı burada görünecek...</pre>
          <div class='buttons'>
            <button class='btn-success' onclick='downloadJSON()' id='downloadBtn' disabled>📥 Download JSON</button>
            <button class='btn-success' onclick='saveToNewsData()' id='saveBtn' disabled>💾 Save to news_data/</button>
            <button class='btn-secondary' onclick='copyJSON()' id='copyBtn' disabled>📋 Copy JSON</button>
          </div>
          <div id='outputInfo' class='info hidden'></div>
        </div>
      </div>
    </div>

    <script>
      let currentJSON = null;
      let currentFileName = 'news_data.json';

      function loadFile() {
        const fileInput = document.getElementById('fileInput');
        const file = fileInput.files[0];
        const inputInfo = document.getElementById('inputInfo');
        const fileNameDisplay = document.getElementById('fileName');
        
        if (!file) return;
        
        const reader = new FileReader();
        reader.onload = function(e) {
          document.getElementById('mdInput').value = e.target.result;
          fileNameDisplay.textContent = '✓ ' + file.name;
          // .md uzantısını .json ile değiştir
          currentFileName = file.name.replace(/\\.(md|txt)$/i, '.json');
          showInfo(inputInfo, `📁 ${file.name} yüklendi (${(file.size/1024).toFixed(1)} KB)`, 'success');
          setTimeout(() => inputInfo.classList.add('hidden'), 3000);
        };
        reader.onerror = function() {
          showInfo(inputInfo, '❌ Dosya okunamadı!', 'error');
          fileNameDisplay.textContent = '';
        };
        reader.readAsText(file, 'UTF-8');
      }

      function convert() {
        const mdInput = document.getElementById('mdInput').value;
        const year = parseInt(document.getElementById('year').value);
        const outputInfo = document.getElementById('outputInfo');
        const inputInfo = document.getElementById('inputInfo');
        
        if (!mdInput.trim()) {
          showInfo(inputInfo, 'Lütfen markdown içeriği girin!', 'error');
          return;
        }

        // Send to server
        fetch('./convert', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({content: mdInput, year: year})
        })
        .then(res => res.json())
        .then(data => {
          if (data.error) {
            showInfo(outputInfo, 'Hata: ' + data.error, 'error');
            currentJSON = null;
            updateButtons(false);
            return;
          }
          
          currentJSON = data;
          document.getElementById('jsonOutput').textContent = JSON.stringify(data, null, 2);
          
          const meta = data.meta || {};
          const msg = `✅ Başarıyla parse edildi!
📊 ${meta.total_days || 0} gün, ${meta.total_events || 0} haber
📅 ${meta.date_range || 'N/A'}`;
          
          showInfo(outputInfo, msg, 'success');
          updateButtons(true);
        })
        .catch(err => {
          showInfo(outputInfo, 'Sunucu hatası: ' + err.message, 'error');
          currentJSON = null;
          updateButtons(false);
        });
      }

      function downloadJSON() {
        if (!currentJSON) return;
        
        const meta = currentJSON.meta || {};
        const filename = prompt('Dosya adı (örn: 30marto3may.json):', currentFileName);
        if (!filename) return;
        
        const blob = new Blob([JSON.stringify(currentJSON, null, 2)], {type: 'application/json'});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
      }

      function saveToNewsData() {
        if (!currentJSON) return;
        
        const filename = prompt('news_data/ klasörüne kaydetmek için dosya adı:', currentFileName);
        if (!filename) return;
        
        const outputInfo = document.getElementById('outputInfo');
        
        fetch('./save', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({data: currentJSON, filename: filename})
        })
        .then(res => res.json())
        .then(data => {
          if (data.error) {
            showInfo(outputInfo, '❌ Kayıt hatası: ' + data.error, 'error');
          } else {
            showInfo(outputInfo, `✅ Kaydedildi: ${data.path}`, 'success');
          }
        })
        .catch(err => {
          showInfo(outputInfo, '❌ Sunucu hatası: ' + err.message, 'error');
        });
      }

      function copyJSON() {
        if (!currentJSON) return;
        
        const text = JSON.stringify(currentJSON, null, 2);
        navigator.clipboard.writeText(text).then(() => {
          const outputInfo = document.getElementById('outputInfo');
          showInfo(outputInfo, '✅ JSON kopyalandı!', 'success');
          setTimeout(() => outputInfo.classList.add('hidden'), 2000);
        });
      }

      function clearInput() {
        document.getElementById('mdInput').value = '';
        document.getElementById('fileInput').value = '';
        document.getElementById('fileName').textContent = '';
        document.getElementById('jsonOutput').textContent = 'JSON çıktısı burada görünecek...';
        document.getElementById('inputInfo').classList.add('hidden');
        document.getElementById('outputInfo').classList.add('hidden');
        currentJSON = null;
        currentFileName = 'news_data.json';
        updateButtons(false);
      }

      function showInfo(element, message, type) {
        element.textContent = message;
        element.className = `info ${type}`;
        element.classList.remove('hidden');
      }

      function updateButtons(enabled) {
        document.getElementById('downloadBtn').disabled = !enabled;
        document.getElementById('saveBtn').disabled = !enabled;
        document.getElementById('copyBtn').disabled = !enabled;
      }
    </script>
  </body>
</html>"""
    return page.encode('utf-8')


class ConverterHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in {"/", "/index", "/index.html"}:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(build_html())
        elif self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"ok")
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

    def do_POST(self):
        if self.path == "/convert":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                md_content = data.get('content', '')
                year = data.get('year', 2025)
                
                # Parse markdown to JSON
                result = parse_markdown_to_json(md_content, year)
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))
                
            except Exception as e:
                error_response = {"error": str(e)}
                self.send_response(400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps(error_response).encode('utf-8'))
        
        elif self.path == "/save":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                json_data = data.get('data')
                filename = data.get('filename', 'data.json')
                
                # Ensure filename ends with .json
                if not filename.endswith('.json'):
                    filename += '.json'
                
                # Save to news_data/
                news_data_dir = os.path.join(os.path.dirname(__file__), '..', 'news_data')
                os.makedirs(news_data_dir, exist_ok=True)
                
                file_path = os.path.join(news_data_dir, filename)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, indent=2, ensure_ascii=False)
                
                response = {"success": True, "path": file_path}
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps(response).encode('utf-8'))
                
            except Exception as e:
                error_response = {"error": str(e)}
                self.send_response(400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps(error_response).encode('utf-8'))
        
        else:
            self.send_error(404, "Not Found")

    def log_message(self, format, *args):
        pass


def run(host: str, port: int) -> None:
    server = HTTPServer((host, port), ConverterHandler)
    print(f"📰 News Converter: http://{host}:{port}/")
    server.serve_forever()


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="news_converter.web",
        description="Markdown to JSON converter for news data"
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host address")
    parser.add_argument("--port", type=int, default=3000, help="Port number")
    args = parser.parse_args(argv)
    
    run(args.host, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
