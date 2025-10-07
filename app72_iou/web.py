"""
App72 IOU News Checker - Web Interface
Flask app for uploading IOU CSV and checking ForexFactory news
"""

import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import json
import tempfile

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app72_iou.news_checker import check_iou_news


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>App72 IOU News Checker</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }
        
        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
        }
        
        .header p {
            font-size: 1.1rem;
            opacity: 0.9;
        }
        
        .card {
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        
        .upload-section {
            text-align: center;
        }
        
        .upload-box {
            border: 3px dashed #667eea;
            border-radius: 8px;
            padding: 40px;
            margin: 20px 0;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .upload-box:hover {
            border-color: #764ba2;
            background: #f8f9ff;
        }
        
        .upload-box.dragover {
            border-color: #764ba2;
            background: #f0f2ff;
        }
        
        input[type="file"] {
            display: none;
        }
        
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 6px;
            font-size: 1rem;
            cursor: pointer;
            transition: transform 0.2s;
        }
        
        .btn:hover {
            transform: translateY(-2px);
        }
        
        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        .settings {
            display: flex;
            gap: 20px;
            margin: 20px 0;
            flex-wrap: wrap;
        }
        
        .setting-group {
            flex: 1;
            min-width: 200px;
        }
        
        .setting-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: 600;
            color: #333;
        }
        
        .setting-group input, .setting-group select {
            width: 100%;
            padding: 10px;
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            font-size: 1rem;
        }
        
        .results {
            margin-top: 30px;
        }
        
        .results table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }
        
        .results th, .results td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e0e0e0;
        }
        
        .results th {
            background: #f5f5f5;
            font-weight: 600;
            color: #333;
        }
        
        .results tr:hover {
            background: #f9f9f9;
        }
        
        .news-cell {
            max-width: 400px;
            word-wrap: break-word;
        }
        
        .news-high {
            color: #dc3545;
            font-weight: 600;
        }
        
        .news-med {
            color: #fd7e14;
            font-weight: 600;
        }
        
        .loading {
            display: none;
            text-align: center;
            padding: 20px;
        }
        
        .loading.active {
            display: block;
        }
        
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 10px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .download-btn {
            background: #28a745;
            margin-top: 15px;
        }
        
        .error {
            background: #f8d7da;
            color: #721c24;
            padding: 15px;
            border-radius: 6px;
            margin: 15px 0;
        }
        
        .success {
            background: #d4edda;
            color: #155724;
            padding: 15px;
            border-radius: 6px;
            margin: 15px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 App72 IOU News Checker</h1>
            <p>ForexFactory economic calendar integration</p>
        </div>
        
        <div class="card">
            <div class="upload-section">
                <h2>Upload IOU CSV File</h2>
                
                <div class="upload-box" id="uploadBox">
                    <p style="font-size: 3rem; margin-bottom: 10px;">📁</p>
                    <p style="font-size: 1.2rem; margin-bottom: 10px;">
                        Drag & drop your CSV file here
                    </p>
                    <p style="color: #666;">or</p>
                    <br>
                    <label for="fileInput" class="btn">
                        Browse Files
                    </label>
                    <input type="file" id="fileInput" accept=".csv">
                </div>
                
                <div class="settings">
                    <div class="setting-group">
                        <label for="candleMinutes">Candle Duration (minutes):</label>
                        <input type="number" id="candleMinutes" value="72" min="1" max="1440">
                    </div>
                    <div class="setting-group">
                        <label for="year">Year:</label>
                        <input type="number" id="year" value="2025" min="2020" max="2030">
                    </div>
                </div>
                
                <button class="btn" id="processBtn" disabled>
                    🔍 Check ForexFactory News
                </button>
                
                <div class="loading" id="loading">
                    <div class="spinner"></div>
                    <p>Fetching ForexFactory data...</p>
                </div>
                
                <div id="message"></div>
            </div>
        </div>
        
        <div class="card results" id="resultsCard" style="display: none;">
            <h2>Results</h2>
            <button class="btn download-btn" id="downloadBtn">
                ⬇️ Download CSV with News
            </button>
            <div id="resultsTable"></div>
        </div>
    </div>
    
    <script>
        let uploadedFile = null;
        let resultsData = null;
        
        const uploadBox = document.getElementById('uploadBox');
        const fileInput = document.getElementById('fileInput');
        const processBtn = document.getElementById('processBtn');
        const loading = document.getElementById('loading');
        const message = document.getElementById('message');
        const resultsCard = document.getElementById('resultsCard');
        const resultsTable = document.getElementById('resultsTable');
        const downloadBtn = document.getElementById('downloadBtn');
        
        // File input change
        fileInput.addEventListener('change', (e) => {
            handleFileSelect(e.target.files[0]);
        });
        
        // Drag and drop
        uploadBox.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadBox.classList.add('dragover');
        });
        
        uploadBox.addEventListener('dragleave', () => {
            uploadBox.classList.remove('dragover');
        });
        
        uploadBox.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadBox.classList.remove('dragover');
            handleFileSelect(e.dataTransfer.files[0]);
        });
        
        function handleFileSelect(file) {
            if (!file || !file.name.endsWith('.csv')) {
                showMessage('Please select a CSV file', 'error');
                return;
            }
            
            uploadedFile = file;
            showMessage(`✓ File selected: ${file.name}`, 'success');
            processBtn.disabled = false;
        }
        
        // Process button
        processBtn.addEventListener('click', async () => {
            if (!uploadedFile) return;
            
            const candleMinutes = parseInt(document.getElementById('candleMinutes').value);
            const year = parseInt(document.getElementById('year').value);
            
            loading.classList.add('active');
            processBtn.disabled = true;
            message.innerHTML = '';
            
            const formData = new FormData();
            formData.append('file', uploadedFile);
            formData.append('candle_minutes', candleMinutes);
            formData.append('year', year);
            
            try {
                const response = await fetch('/process', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.success) {
                    resultsData = result.data;
                    displayResults(result.data);
                    showMessage(`✓ Processed ${result.data.length} rows`, 'success');
                } else {
                    showMessage(`Error: ${result.error}`, 'error');
                }
            } catch (error) {
                showMessage(`Error: ${error.message}`, 'error');
            } finally {
                loading.classList.remove('active');
                processBtn.disabled = false;
            }
        });
        
        function displayResults(data) {
            if (!data || data.length === 0) {
                resultsTable.innerHTML = '<p>No results</p>';
                return;
            }
            
            const headers = Object.keys(data[0]);
            
            let html = '<table><thead><tr>';
            headers.forEach(h => {
                html += `<th>${h}</th>`;
            });
            html += '</tr></thead><tbody>';
            
            data.forEach(row => {
                html += '<tr>';
                headers.forEach(h => {
                    let value = row[h];
                    let className = '';
                    
                    if (h === 'News' && value && value !== '-') {
                        if (value.includes('[HIG')) className = 'news-high';
                        else if (value.includes('[MED')) className = 'news-med';
                        className += ' news-cell';
                    }
                    
                    html += `<td class="${className}">${value}</td>`;
                });
                html += '</tr>';
            });
            
            html += '</tbody></table>';
            resultsTable.innerHTML = html;
            resultsCard.style.display = 'block';
        }
        
        // Download CSV
        downloadBtn.addEventListener('click', () => {
            if (!resultsData) return;
            
            const headers = Object.keys(resultsData[0]);
            let csv = headers.join(',') + '\\n';
            
            resultsData.forEach(row => {
                const values = headers.map(h => {
                    let val = row[h] || '';
                    // Escape commas and quotes
                    if (val.includes(',') || val.includes('"')) {
                        val = '"' + val.replace(/"/g, '""') + '"';
                    }
                    return val;
                });
                csv += values.join(',') + '\\n';
            });
            
            const blob = new Blob([csv], { type: 'text/csv' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'iou_with_news.csv';
            a.click();
        });
        
        function showMessage(msg, type) {
            message.innerHTML = `<div class="${type}">${msg}</div>`;
        }
    </script>
</body>
</html>
"""


class NewsCheckerHandler(SimpleHTTPRequestHandler):
    """Custom HTTP handler for news checker"""
    
    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/' or self.path == '':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode())
        else:
            self.send_error(404)
    
    def do_POST(self):
        """Handle POST requests"""
        if self.path == '/process':
            try:
                # Parse multipart form data
                content_length = int(self.headers['Content-Length'])
                body = self.rfile.read(content_length)
                
                # Simple multipart parser
                boundary = self.headers['Content-Type'].split('boundary=')[1]
                parts = body.split(f'--{boundary}'.encode())
                
                file_content = None
                candle_minutes = 72
                year = 2025
                
                for part in parts:
                    if b'filename=' in part:
                        # Extract file content
                        content_start = part.find(b'\r\n\r\n') + 4
                        file_content = part[content_start:].rstrip(b'\r\n')
                    elif b'name="candle_minutes"' in part:
                        content_start = part.find(b'\r\n\r\n') + 4
                        candle_minutes = int(part[content_start:].decode().strip())
                    elif b'name="year"' in part:
                        content_start = part.find(b'\r\n\r\n') + 4
                        year = int(part[content_start:].decode().strip())
                
                if not file_content:
                    self.send_json_response({'success': False, 'error': 'No file uploaded'})
                    return
                
                # Save to temp file
                with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as tmp:
                    tmp.write(file_content)
                    tmp_path = tmp.name
                
                # Process the file
                results = check_iou_news(tmp_path, candle_minutes=candle_minutes, year=year)
                
                # Clean up temp file
                os.unlink(tmp_path)
                
                # Send response
                self.send_json_response({
                    'success': True,
                    'data': results
                })
                
            except Exception as e:
                self.send_json_response({
                    'success': False,
                    'error': str(e)
                })
        else:
            self.send_error(404)
    
    def send_json_response(self, data):
        """Send JSON response"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def log_message(self, format, *args):
        """Custom log format"""
        print(f"[{self.log_date_time_string()}] {format % args}")


def run_server(port=2172):
    """Run the web server"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, NewsCheckerHandler)
    print(f"\n🚀 App72 IOU News Checker running on http://localhost:{port}")
    print(f"📊 Upload your IOU CSV to check ForexFactory news\n")
    httpd.serve_forever()


if __name__ == '__main__':
    run_server()
