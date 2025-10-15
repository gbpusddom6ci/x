import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, time as dtime, timedelta
from typing import List, Optional, Tuple, Dict


MINUTES_PER_STEP = 120
DEFAULT_START_TOD = dtime(hour=18, minute=0)


@dataclass
class Candle:
    ts: datetime
    open: float
    high: float
    low: float
    close: float


# Original sequences
SEQUENCES_FULL: Dict[str, List[int]] = {
    "S1": [1, 3, 7, 13, 21, 31, 43, 57, 73, 91, 111, 133, 157],
    "S2": [1, 5, 9, 17, 25, 37, 49, 65, 81, 101, 121, 145, 169],
}

# Filtered sequences (1,3 excluded for S1; 1,5 excluded for S2)
SEQUENCES_FILTERED: Dict[str, List[int]] = {
    "S1": [7, 13, 21, 31, 43, 57, 73, 91, 111, 133, 157],
    "S2": [9, 17, 25, 37, 49, 65, 81, 101, 121, 145, 169],
}


@dataclass
class IOUResult:
    """Result for a single IOU candle"""
    seq_value: int
    index: int
    timestamp: datetime
    oc: float
    prev_oc: float
    prev_index: int
    prev_timestamp: datetime


def normalize_key(name: str) -> str:
    return name.strip().strip('"').strip("'").lower()


def parse_float(val: str) -> Optional[float]:
    if val is None:
        return None
    s = str(val).strip()
    if s == "" or s.lower() in {"nan", "null", "none"}:
        return None
    if "," in s and "." not in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def parse_time_value(val: str) -> Optional[datetime]:
    if val is None:
        return None
    s = str(val).strip()
    if s == "":
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt
    except Exception:
        pass
    fmts = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%d.%m.%Y %H:%M:%S",
        "%d.%m.%Y %H:%M",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M",
    ]
    for fmt in fmts:
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            continue
    return None


def load_candles(path: str) -> List[Candle]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
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

        out: List[Candle] = []
        for row in reader:
            t = parse_time_value(row.get(time_key))
            o = parse_float(row.get(open_key))
            h = parse_float(row.get(high_key))
            l = parse_float(row.get(low_key))
            c = parse_float(row.get(close_key))
            if None in (t, o, h, l, c):
                continue
            out.append(Candle(ts=t, open=o, high=h, low=l, close=c))
    out.sort(key=lambda x: x.ts)
    return out


def find_start_index(candles: List[Candle], start_tod: dtime) -> Tuple[int, str]:
    if not candles:
        return 0, "no-data"
    min_date = min(c.ts.date() for c in candles)
    target = datetime.combine(min_date, start_tod)
    for i, c in enumerate(candles):
        if c.ts == target:
            return i, "aligned"
    for i, c in enumerate(candles):
        if c.ts >= target and c.ts.time() == start_tod:
            return i, "aligned"
    for i, c in enumerate(candles):
        if c.ts.time() == start_tod:
            return i, "tod-found"
    return 0, "fallback-first"


def compute_dc_flags(candles: List[Candle]) -> List[Optional[bool]]:
    flags: List[Optional[bool]] = [None] * len(candles)
    for i in range(1, len(candles)):
        prev = candles[i - 1]
        cur = candles[i]
        within = min(prev.open, prev.close) <= cur.close <= max(prev.open, prev.close)
        cond = cur.high <= prev.high and cur.low >= prev.low and within
        if cur.ts.hour == DEFAULT_START_TOD.hour and cur.ts.minute == DEFAULT_START_TOD.minute:
            cond = False
        else:
            is_week_close = False
            if cur.ts.hour == 16 and cur.ts.minute == 0:
                if i + 1 >= len(candles):
                    is_week_close = True
                else:
                    gap_minutes = (candles[i + 1].ts - cur.ts).total_seconds() / 60
                    if gap_minutes > MINUTES_PER_STEP:
                        is_week_close = True
            if is_week_close:
                cond = False
        prev_flag = bool(flags[i - 1]) if flags[i - 1] is not None else False
        if prev_flag and cond:
            cond = False
        flags[i] = bool(cond)
    return flags


@dataclass
class SequenceAllocation:
    idx: Optional[int]
    ts: Optional[datetime]
    used_dc: bool


def compute_sequence_allocations(
    candles: List[Candle],
    dc_flags: List[Optional[bool]],
    start_idx: int,
    seq_values: List[int],
) -> List[SequenceAllocation]:
    if not seq_values:
        return []
    allocations: List[SequenceAllocation] = [SequenceAllocation(None, None, False) for _ in seq_values]
    if not candles or start_idx < 0 or start_idx >= len(candles):
        return allocations

    def is_dc_candle(idx: int) -> bool:
        flag = dc_flags[idx] if 0 <= idx < len(dc_flags) else None
        return bool(flag)

    first_ts = candles[start_idx].ts
    allocations[0] = SequenceAllocation(
        idx=start_idx,
        ts=first_ts,
        used_dc=is_dc_candle(start_idx),
    )

    prev_idx = start_idx
    prev_val = seq_values[0]
    for i in range(1, len(seq_values)):
        cur_val = seq_values[i]
        if cur_val <= prev_val:
            allocations[i] = allocations[i - 1]
            prev_val = cur_val
            continue
        steps_needed = cur_val - prev_val
        cur_idx = prev_idx
        counted = 0
        last_dc_idx: Optional[int] = None
        while counted < steps_needed and cur_idx + 1 < len(candles):
            cur_idx += 1
            flag_val = dc_flags[cur_idx]
            is_dc = bool(flag_val) if flag_val is not None else False
            if is_dc:
                if counted == steps_needed - 1:
                    last_dc_idx = cur_idx
                continue
            counted += 1
        if counted == steps_needed and 0 <= cur_idx < len(candles):
            assigned_idx = cur_idx
            assigned_ts = candles[cur_idx].ts
            used_dc = False
            if last_dc_idx is not None:
                assigned_idx = last_dc_idx
                assigned_ts = candles[last_dc_idx].ts
                used_dc = True
            allocations[i] = SequenceAllocation(idx=assigned_idx, ts=assigned_ts, used_dc=used_dc)
            prev_idx = cur_idx
            prev_val = cur_val
        else:
            allocations[i] = SequenceAllocation(idx=None, ts=None, used_dc=False)
            prev_idx = cur_idx
            prev_val = cur_val
    return allocations


def determine_offset_start(
    candles: List[Candle],
    base_idx: int,
    offset: int,
    minutes_per_step: int = MINUTES_PER_STEP,
    dc_flags: Optional[List[Optional[bool]]] = None,
) -> Tuple[Optional[int], Optional[datetime], str]:
    """
    NEW LOGIC (2025-10-07): Offset = Non-DC candle count
    
    Determines the offset start index by counting non-DC candles from base.
    DC candles are skipped in counting.
    """
    if not candles or base_idx < 0 or base_idx >= len(candles):
        return None, None, "no-data"
    
    if dc_flags is None:
        dc_flags = [False] * len(candles)
    
    # Offset 0: return base itself
    if offset == 0:
        base_ts = candles[base_idx].ts.replace(second=0, microsecond=0)
        return base_idx, base_ts, "aligned"
    
    # Count non-DC candles from base
    current_idx = base_idx
    non_dc_count = 0
    target_count = abs(offset)
    direction = 1 if offset > 0 else -1
    
    while 0 <= current_idx < len(candles):
        current_idx += direction
        
        # Out of bounds check
        if current_idx < 0:
            return None, None, "before-data"
        if current_idx >= len(candles):
            return None, None, "after-data"
        
        # Check if DC
        is_dc = dc_flags[current_idx] if current_idx < len(dc_flags) else False
        
        # Skip DC candles
        if is_dc:
            continue
        
        # Count this non-DC candle
        non_dc_count += 1
        
        # Reached target?
        if non_dc_count == target_count:
            target_ts = candles[current_idx].ts.replace(second=0, microsecond=0)
            return current_idx, target_ts, "aligned"
    
    # Ran out of data
    if offset > 0:
        return None, None, "after-data"
    else:
        return None, None, "before-data"


def analyze_iou(
    candles: List[Candle],
    sequence: str,
    limit: float,
    tolerance: float = 0.005,
) -> Dict[int, List[IOUResult]]:
    """
    Analyze IOU candles for all offsets (-3 to +3).
    
    Returns: Dict[offset] -> List[IOUResult]
    """
    results: Dict[int, List[IOUResult]] = {}
    
    start_tod = DEFAULT_START_TOD
    base_idx, _ = find_start_index(candles, start_tod)
    dc_flags = compute_dc_flags(candles)
    
    # Use FULL sequence for allocation, then filter for IOU analysis
    seq_values_full = SEQUENCES_FULL[sequence]
    seq_values_filtered = SEQUENCES_FILTERED[sequence]
    
    for offset in range(-3, 4):
        iou_list: List[IOUResult] = []
        
        start_idx, target_ts, offset_status = determine_offset_start(candles, base_idx, offset, MINUTES_PER_STEP, dc_flags)
        base_ts = candles[base_idx].ts.replace(second=0, microsecond=0)
        if target_ts is None:
            target_ts = base_ts + timedelta(minutes=MINUTES_PER_STEP * offset)
        
        missing_steps = 0
        
        # If exact target not found, find next available and calculate missing steps
        if start_idx is None or start_idx < 0 or start_idx >= len(candles):
            # Find first candle after target
            after_idx: Optional[int] = None
            for i, candle in enumerate(candles):
                ts_norm = candle.ts.replace(second=0, microsecond=0)
                if ts_norm >= target_ts:
                    after_idx = i
                    break
            
            if after_idx is not None and 0 <= after_idx < len(candles):
                start_idx = after_idx
                actual_ts = candles[start_idx].ts
                delta_minutes = int((actual_ts - target_ts).total_seconds() // 60)
                if delta_minutes < 0:
                    delta_minutes = 0
                missing_steps = max(0, delta_minutes // MINUTES_PER_STEP)
            else:
                # Really no data to work with
                results[offset] = iou_list
                continue
        
        # Build compute sequence (app120 style)
        actual_start_count = missing_steps + 1
        seq_compute: List[int] = [actual_start_count]
        for v in seq_values_full:
            if v > missing_steps:
                if v != actual_start_count:
                    seq_compute.append(v)
        
        # Compute allocations for synthetic sequence
        allocations = compute_sequence_allocations(candles, dc_flags, start_idx, seq_compute)
        
        # Build mapping: original seq_value -> allocation
        seq_map: Dict[int, SequenceAllocation] = {}
        for idx, val in enumerate(seq_compute):
            seq_map[val] = allocations[idx]
        
        # For values <= missing_steps, mark as None
        for v in seq_values_full:
            if v <= missing_steps:
                seq_map[v] = SequenceAllocation(None, None, False)
        
        # Analyze only filtered sequence values
        for seq_val in seq_values_filtered:
            alloc = seq_map.get(seq_val)
            if alloc is None or alloc.idx is None:
                continue
            
            idx = alloc.idx
            if idx <= 0 or idx >= len(candles):
                continue
            
            candle = candles[idx]
            prev_candle = candles[idx - 1]
            
            oc = candle.close - candle.open
            prev_oc = prev_candle.close - prev_candle.open
            
            # Check IOU criteria
            # 1. Both |OC| and |PrevOC| must be >= limit
            # Skip if too close to limit (within ±tolerance for safety)
            if abs(abs(oc) - limit) < tolerance or abs(abs(prev_oc) - limit) < tolerance:
                continue  # Too close to limit, unreliable
            
            # 2. OC and PrevOC must have SAME signs (opposite of IOV)
            if not ((oc > 0 and prev_oc > 0) or (oc < 0 and prev_oc < 0)):
                continue
            
            # This is an IOU candle!
            iou_list.append(IOUResult(
                seq_value=seq_val,
                index=idx,
                timestamp=candle.ts,
                oc=oc,
                prev_oc=prev_oc,
                prev_index=idx - 1,
                prev_timestamp=prev_candle.ts,
            ))
        
        results[offset] = iou_list
    
    return results


def fmt_ts(dt: Optional[datetime]) -> str:
    if dt is None:
        return "-"
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def fmt_pip(delta: float) -> str:
    return f"{delta:+.5f}"


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(
        prog="app120.iou.counter",
        description="120m IOU (Inverse OC - Uniform sign) Analysis",
    )
    p.add_argument("--csv", required=True, help="CSV dosyası (120m mumlar)")
    p.add_argument(
        "--sequence",
        choices=["S1", "S2"],
        default="S1",
        help="Sequence seçimi (varsayılan: S1)",
    )
    p.add_argument(
        "--limit",
        type=float,
        default=0.1,
        help="IOU limit değeri (varsayılan: 0.1)",
    )
    args = p.parse_args(argv)

    candles = load_candles(args.csv)
    if not candles:
        print("Uyarı: veri yüklenemedi ya da boş")
        return 1
    print(f"Data: {len(candles)} candles")
    print(f"Range: {fmt_ts(candles[0].ts)} -> {fmt_ts(candles[-1].ts)}")
    print(f"Sequence: {args.sequence} (Filtered: {SEQUENCES_FILTERED[args.sequence]})")
    print(f"Limit: {args.limit}")
    print()

    results = analyze_iou(candles, args.sequence, args.limit)
    
    total_iou = sum(len(v) for v in results.values())
    print(f"Total IOU candles found: {total_iou}")
    print()
    
    # Only show offsets with IOU candles
    for offset in range(-3, 4):
        iou_list = results[offset]
        if iou_list:  # Only print if there are IOU candles
            print(f"Offset: {offset:+d}")
            for iou in iou_list:
                print(f"  Seq={iou.seq_value}, Index={iou.index}, Time={fmt_ts(iou.timestamp)}")
                print(f"    OC: {fmt_pip(iou.oc)}, PrevOC: {fmt_pip(iou.prev_oc)}")
            print()
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
