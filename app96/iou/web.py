# app96/iou/web.py - Minimal stub
# Full IOU web UI to be implemented later

from http.server import HTTPServer, BaseHTTPRequestHandler
import argparse


def make_handler():
    class IOUHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            response = b"""<!doctype html>
<html>
<head><meta charset='utf-8'><title>app96 IOU</title></head>
<body style='font-family: sans-serif; margin: 40px;'>
<h1>app96 IOU Analysis</h1>
<p>96-minute IOU (Inverse OC - Uniform sign) analysis with news integration.</p>
<p><em>Full web UI coming soon...</em></p>
<p>Use CLI: <code>python -m app96.iou.counter --csv data.csv --limit 0.75</code></p>
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
