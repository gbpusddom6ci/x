# APP96 Implementation Context - Next Session Briefing

## Project Overview
This is the x1 monorepo containing multiple Python-based counter/analysis applications (app48, app72, app80, app96, app120, app321). We are in the process of completing **app96** - a 96-minute timeframe counter and IOU analysis tool.

## What Has Been Completed

### 1. Core Backend Logic (✅ DONE)
- **app96/counter.py**: Full counter implementation with:
  - 96-minute timeframe (MINUTES_PER_STEP = 96)
  - Standard DC rules (no special 20:00 exception like app120)
  - Weekend jump handling
  - Sequences S1 and S2
  - Offset support (-3 to +3)
  - Prediction logic

- **app96/main.py**: 12m→96m converter CLI tool
  - Reads 12-minute CSV data
  - Converts to 96-minute candles
  - Timezone adjustment (UTC-5 → UTC-4)
  - CSV output

- **app96/iou/counter.py**: IOU analysis implementation
  - Detects candles where |OC| ≥ limit AND |PrevOC| ≥ limit AND same sign
  - Filtered sequences (S1 excludes [1,3], S2 excludes [1,5])
  - Scans all offsets (-3 to +3)
  - Time restrictions: 18:00 always excluded, 20:00 excluded except Sunday, Friday 16:00 excluded
  - Tolerance support for near-limit filtering

### 2. System Integration (✅ DONE)
- **appsuite/web.py**: app96 integrated as reverse proxy on port 9206
  - Routes: /app96/* proxied to 127.0.0.1:9206
  - Multi-file upload support
  - Path rewriting for href/action attributes

- **landing/web.py**: app96 link added to landing page with photo

- **WARP.md**: Documentation updated with:
  - app96 quickstart commands
  - CLI usage examples
  - Architecture notes

### 3. Minimal Web UI (⚠️ INCOMPLETE - STUB ONLY)
- **app96/web.py**: Currently a MINIMAL STUB with:
  - Basic HTTP server setup
  - Tab navigation structure (Counter, DC List, Matrix, IOU, Converter)
  - Placeholder forms
  - NO actual functionality implemented
  - NO file upload handling
  - NO result rendering
  - NO news integration display

- **app96/iou/web.py**: Not needed (IOU is integrated in main web.py like app120)

## What Needs To Be Completed

### PRIMARY TASK: Complete app96/web.py
The current web.py is a minimal stub. It needs to be fully implemented following the **app120/web.py** pattern (reference file at `/Users/malware/x1/app120/web.py`).

#### Required Features:

1. **Counter Tab (/)**: 
   - File upload form (single CSV)
   - Timezone selector (UTC-5/UTC-4)
   - Sequence selector (S1/S2)
   - Offset selector (-3 to +3)
   - Show DC checkbox
   - POST handler to analyze CSV and render results table
   - Display: sequence hits with timestamps, indices, OC/PrevOC values, DC flags
   - Prediction for missing data points

2. **DC List Tab (/dc)**:
   - File upload form (single CSV)
   - Timezone selector
   - POST handler to detect and list all DC candles
   - Display: table with index, timestamp, OHLC values for each DC

3. **Matrix Tab (/matrix)**:
   - File upload form (single CSV)
   - Timezone selector
   - Sequence selector
   - POST handler to compute all offsets (-3 to +3) simultaneously
   - Display: matrix table showing sequence values vs offsets
   - Each cell shows timestamp, OC, PrevOC, (pred) for missing data

4. **IOU Tab (/iou)**:
   - **Multi-file upload** (up to 25 CSV files)
   - Sequence selector (S1/S2 filtered)
   - Limit input (default 0.1)
   - Tolerance input (default 0.005)
   - XYZ Analysis checkbox
   - XYZ Summary Table checkbox
   - POST handler to process multiple files:
     - Load each CSV
     - Run IOU analysis for all offsets
     - Integrate news data from `news_data/*.json` (auto-merge all JSON files)
     - Display results per file with news events
     - Categorize news: HOLIDAY, SPEECH, ALLDAY, NORMAL
     - XYZ set filtering: eliminate offsets with news-free IOUs
     - Optional summary table mode showing only XYZ sets per file

5. **Converter Tab (/converter)**:
   - File upload form (single CSV, 12m data)
   - POST handler to convert 12m→96m
   - Return CSV file download (filename_96m.csv)

#### Technical Requirements:

- **Copy and adapt from app120/web.py** (line-by-line reference)
- Change all "120m" references to "96m"
- Change all "app120" labels to "app96"
- Adjust MINUTES_PER_STEP references (96 not 120)
- Import from app96 modules:
  ```python
  from .counter import (...)
  from .main import (...)
  from .iou.counter import analyze_iou, IOUResult, SEQUENCES_FILTERED
  ```
- Keep same HTML/CSS styling
- Keep favicon support (/favicon/* routes)
- Use same multipart form parsing helpers
- News integration: load from `news_data/*.json`, same logic as app120
- Handle timezone adjustment (UTC-5 → UTC-4 with +1h shift)

#### Key Differences from app120:
- **NO IOV** support (app96 doesn't have iov/ module)
- Remove all IOV-related imports, routes, and tabs
- Converter is 12m→96m (not 60m→120m)
- DC rules are standard (no 20:00 special exception)

## File Structure Reference
```
app96/
├── __init__.py          ✅ Done
├── counter.py           ✅ Done
├── main.py              ✅ Done (12m→96m converter)
├── web.py               ⚠️  INCOMPLETE STUB - NEEDS FULL IMPLEMENTATION
└── iou/
    ├── __init__.py      ✅ Done
    └── counter.py       ✅ Done
```

## User's Request
**"Continue fleshing out all unfinished features and build a full-featured web UI for app96, modeled after app120 web UI, disregarding token context size."**

The user wants a complete, production-ready web interface with:
- All tabs functional
- Multi-file upload for IOU
- News integration
- Matrix views
- DC lists
- Full forms and result displays
- Same professional UI as app120

## Next Steps for Implementation

1. **Read the reference**: `/Users/malware/x1/app120/web.py` (already provided in previous context)
2. **Replace app96/web.py** with full implementation:
   - Copy app120/web.py structure
   - Adapt all imports to app96 modules
   - Remove IOV tab and logic
   - Change timeframe references (120→96)
   - Change converter references (60m→120m becomes 12m→96m)
   - Keep all news integration logic
   - Keep all multipart parsing helpers
   - Keep all HTML rendering functions

3. **Test the implementation**:
   ```bash
   python -m app96.web --host 127.0.0.1 --port 2196
   ```

4. **Verify through appsuite**:
   ```bash
   python -m appsuite.web --host 0.0.0.0 --port 2000
   # Access at http://localhost:2000/app96
   ```

## Important Notes

- **Standard DC rules**: app96 uses standard DC detection without app120's 20:00 candle exception
- **No IOV**: app96 only has IOU analysis, not IOV
- **96-minute timeframe**: All time calculations use 96-minute steps
- **News data location**: `news_data/*.json` at repo root (same as app120)
- **Favicon support**: Must serve from `/favicon/*` using relative path `../favicon/`
- **Encoding**: All HTML responses must use UTF-8 (`text/html; charset=utf-8`)

## Reference Commands

```bash
# Start app96 standalone
python -m app96.web --host 127.0.0.1 --port 2196

# Start unified suite (includes app96 on port 9206)
python -m appsuite.web --host 0.0.0.0 --port 2000

# CLI counter example
python -m app96.counter --csv data.csv --sequence S1 --offset 0

# CLI converter example
python -m app96.main --csv input12m.csv --input-tz UTC-5 --output out96m.csv
```

## Success Criteria

✅ All tabs render properly  
✅ File uploads work (single and multiple)  
✅ Counter analysis displays results with proper formatting  
✅ DC list shows all distorted candles  
✅ Matrix displays all offsets in grid format  
✅ IOU analysis processes multiple files with news integration  
✅ XYZ set filtering works correctly  
✅ Converter downloads CSV file  
✅ Favicon loads correctly  
✅ No encoding errors in Turkish text  
✅ Integration with appsuite works (/app96 routes)  

---

**Start by implementing the full app96/web.py following the app120/web.py pattern exactly, with the adjustments noted above.**
