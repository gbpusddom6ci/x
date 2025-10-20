# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

Quickstart commands

- Unified suite (reverse proxy + all apps):
  ```bash path=null start=null
  python -m appsuite.web --host 0.0.0.0 --port 2000
  ```
  - Internals: launches app48/app72/app80/app120/app321/news_converter on 127.0.0.1 ports 9200–9205 and serves them under /app48, /app72, /app80, /app120, /app321, /news. Health: GET /health. Static: /favicon/*, /photos/*, /stars.gif.

- Start individual web UIs (defaults):
  ```bash path=null start=null
  python -m app48.web --host 127.0.0.1 --port 2020
  python -m app72.web --host 127.0.0.1 --port 2172
  python -m app80.web --host 127.0.0.1 --port 2180
  python -m app120.web --host 127.0.0.1 --port 2120
  python -m app321.web --host 127.0.0.1 --port 2019
  python -m landing.web --host 127.0.0.1 --port 2000
  ```

- CLI counters (examples):
  ```bash path=null start=null
  python -m app48.main --csv data.csv --input-tz UTC-5 --sequence S2 --offset 0 --show-dc
  python -m app72.counter --csv data.csv --sequence S1 --offset +1
  python -m app80.counter --csv data.csv --sequence S2 --offset +2
  python -m app120.counter --csv data.csv --sequence S1 --offset 0 --predict-next
  python -m app321.main --csv data.csv --sequence S2 --offset 0 --show-dc
  ```

- Converters (CLI):
  ```bash path=null start=null
  # 12m→72m
  python -m app72.main --csv input12m.csv --input-tz UTC-5 --output out72m.csv
  # 20m→80m
  python -m app80.main --csv input20m.csv --input-tz UTC-5 --output out80m.csv
  # 60m→120m
  python -m app120.main --csv input60m.csv --input-tz UTC-5 --output out120m.csv
  ```

- Environment setup (optional):
  ```bash path=null start=null
  python -m venv .venv && source .venv/bin/activate
  pip install -r requirements.txt  # only gunicorn by default; code uses stdlib
  ```

- Docker (appsuite by default):
  ```bash path=null start=null
  docker build -t x1 .
  docker run --rm -e PORT=2000 -p 2000:2000 x1
  ```
  - The image CMD starts: `python -m appsuite.web --host 0.0.0.0 --port $PORT`

- Lint and tests:
  - No repo-level linter or test suite is configured (no pytest/tox/ruff config detected).

Architecture overview

- Monorepo of pure-stdlib Python services and CLIs:
  - app48, app72, app80, app120, app321 each provide CSV-driven “counter” analysis (CLI) and a minimal http.server UI (web.py). app120 also includes iou/ and iov/ analyzers and a richer web UI (multi-file upload, news integration).
  - landing renders a static hub to app UIs. appsuite is a reverse proxy that concurrently launches all backends and serves them under URL prefixes.
  - news_converter is a small http.server app to convert ForexFactory-like Markdown to JSON; IOU UIs use JSON files under news_data/.

- CSV ingestion and normalization (shared patterns across apps):
  - csv.Sniffer-driven delimiter detection (comma/semicolon/tab) with fallback to comma.
  - Header normalization accepts multiple aliases for Time/Open/High/Low/Close (Last).
  - Timestamps parsed from several formats, rows sorted ascending by ts.
  - Timezone is treated as naive UTC-4; if input-tz is UTC-5, timestamps are shifted +1h to align to UTC-4.

- Core counting model (sequences, DC, offsets):
  - Anchor is 18:00; offsets span −3..+3 relative to the 18:00 base.
  - Sequences: S1/S2 fixed integer sets; counting advances by step differences.
  - DC (Distorted Candle) base rule: high≤prev.high, low≥prev.low, close within prev open–close; consecutive DCs disallowed. Each app adds time-based exceptions in its counter.
  - DCs are skipped while counting; if the final step lands on a DC, it can be used as the hit (used_dc=True).
  - Missing-steps alignment: if the target timestamp is absent, align to the first candle with ts ≥ target, compute missing_steps, and start accordingly. Prediction advances by timeframe minutes; 72/80/120 handle weekend jumps, 48/60 do not.

- IOU/IOV analysis (app120):
  - IOU: OC and PrevOC above limit and same sign; applies tolerance to drop near-limit values. IOV: above limit and opposite signs.
  - Both scan all offsets (−3..+3) using filtered sequences (early values removed). Web UI supports up to 25 CSV files.
  - News integration: news_data/*.json is auto-merged. Matching checks [start, start+TF); for null-value events (speeches/statements) also [start−1h, start+TF). Holidays are displayed but don’t eliminate offsets. IOU “XYZ set” filters out offsets that contain any news-free IOU; remaining offsets form the XYZ set.

- Reverse proxy (appsuite):
  - Spawns per-app servers on 127.0.0.1:9200–9205, proxies GET/POST, rewrites href/action paths to keep links working under prefixes, serves /health and static assets.

Operational invariants and gotchas

- Treat data as UTC-4; pass input-tz UTC-5 when needed or use converters (which normalize to UTC-4).
- 18:00 is the anchor across apps. Weekend jump rules apply in 72/80/120 only.
- IOU tolerance check occurs after passing the absolute limit check.
- news_data JSON is additive-merged; candle year is used when correlating dates (JSON year can be ignored for matching).
- All web handlers are stateless, single-threaded http.server instances.

Deploy hints (repo-specific)

- Procfile, railway.toml, and render.yaml invoke appsuite.web with $PORT (health check at /health). Dockerfile does the same.
- requirements.txt only includes gunicorn (optional, for production); everything else relies on the Python standard library.
