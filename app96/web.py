# app96/web.py - Minimal stub for appsuite integration
# Full web UI to be implemented later

from http.server import HTTPServer, BaseHTTPRequestHandler
import argparse


def make_handler():
    class App96Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path in {"/", "/index", "/index.html"}:
                response = """<!doctype html>
<html>
<head><meta charset='utf-8'><title>app96</title></head>
<body style='font-family: sans-serif; margin: 40px;'>
<h1>app96 - 96 Minute Analysis</h1>
<p>96-minute timeframe counter, DC analysis, IOU, and 12m→96m converter.</p>
<p><em>Full web UI coming soon...</em></p>
<hr>
<p><strong>CLI Usage:</strong></p>
<ul>
<li><code>python -m app96.counter --csv data.csv --sequence S1 --offset 0</code></li>
<li><code>python -m app96.main --csv input12m.csv --output out96m.csv</code></li>
<li><code>python -m app96.iou.counter --csv data.csv --limit 0.75</code></li>
</ul>
</body>
</html>""".encode('utf-8')
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(response)))
                self.end_headers()
                self.wfile.write(response)
            else:
                self.send_error(404, "Not Found")
        
        def log_message(self, format, *args):
            pass

    return App96Handler


def run(host: str, port: int) -> None:
    handler_cls = make_handler()
    server = HTTPServer((host, port), handler_cls)
    print(f"app96 web: http://{host}:{port}/")
    server.serve_forever()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="app96.web", description="app96 web UI")
    parser.add_argument("--host", default="127.0.0.1", help="Host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=2196, help="Port (default: 2196)")
    args = parser.parse_args(argv)

    run(args.host, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
