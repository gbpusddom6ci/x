import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, time as dtime, timedelta, timezone
from typing import List, Optional, Tuple, Dict


@dataclass
class Candle:
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    synthetic: bool = False


SEQUENCES: Dict[str, List[int]] = {
    "S1": [1, 3, 7, 13, 21, 31, 43, 57, 73, 91, 111, 133, 157],
    "S2": [1, 5, 9, 17, 25, 37, 49, 65, 81, 101, 121, 145, 169],
}

# Filtered sequences for IOU analysis (exclude early values)
SEQUENCES_FILTERED: Dict[str, List[int]] = {
    "S1": [7, 13, 21, 31, 43, 57, 73, 91, 111, 133, 157],  # 1,3 excluded
    "S2": [9, 17, 25, 37, 49, 65, 81, 101, 121, 145, 169],  # 1,5 excluded
}

DEFAULT_START_TOD = dtime(hour=18, minute=0)
MINUTES_PER_STEP = 48  # 48m timeframe


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
        if s.isdigit():
            iv = int(s)
            if iv >= 10**12:
                return datetime.fromtimestamp(iv / 1000, tz=timezone.utc).replace(tzinfo=None)
            return datetime.fromtimestamp(iv, tz=timezone.utc).replace(tzinfo=None)
    except Exception:
        pass
    iso_try = s.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(iso_try)
        # Bu uygulamada zamanlar yerel saat olarak ele alınır.
        # CSV "-04:00" içeriyorsa, UTC'ye çevirmeden tz bilgisini düşür.
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


def sniff_dialect(path: str) -> csv.Dialect:
    with open(path, "r", encoding="utf-8", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        try:
            return csv.Sniffer().sniff(sample, delimiters=",;\t")
        except Exception:
            class _D(csv.Dialect):
                delimiter = ","
                quotechar = '"'
                doublequote = True
                skipinitialspace = True
                lineterminator = "\n"
                quoting = csv.QUOTE_MINIMAL
            return _D()


def load_candles(path: str) -> List[Candle]:
    dialect = sniff_dialect(path)
    rows: List[Candle] = []
    with open(path, "r", encoding="utf-8", newline="") as f:
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


def fmt_ts(dt: Optional[datetime]) -> str:
    if dt is None:
        return "-"
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def fmt_pip(delta: Optional[float]) -> str:
    if delta is None:
        return "-"
    return f"{delta:+.5f}"


def estimate_timeframe_minutes(candles: List[Candle]) -> Optional[float]:
    if len(candles) < 2:
        return None
    deltas = [(candles[i].ts - candles[i - 1].ts).total_seconds() / 60 for i in range(1, min(len(candles), 200))]
    deltas = [d for d in deltas if d > 0]
    if not deltas:
        return None
    deltas.sort()
    mid = len(deltas) // 2
    if len(deltas) % 2 == 1:
        return deltas[mid]
    return (deltas[mid - 1] + deltas[mid]) / 2


def parse_tod(s: str) -> dtime:
    hh, mm = s.split(":", 1)
    return dtime(hour=int(hh), minute=int(mm))


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
        prev_flag = bool(flags[i - 1]) if flags[i - 1] is not None else False
        if prev_flag and cond:
            cond = False
        flags[i] = bool(cond)
    return flags


def compute_sequence_indices_skip_dc(
    candles: List[Candle],
    dc_flags: List[Optional[bool]],
    start_idx: int,
    seq_values: List[int],
) -> List[Optional[int]]:
    allocations = compute_sequence_allocations(candles, dc_flags, start_idx, seq_values)
    return [alloc.idx for alloc in allocations]


@dataclass
class SequenceAllocation:
    idx: Optional[int]
    ts: Optional[datetime]
    used_dc: bool
    synthetic: bool


def compute_sequence_allocations(
    candles: List[Candle],
    dc_flags: List[Optional[bool]],
    start_idx: int,
    seq_values: List[int],
) -> List[SequenceAllocation]:
    if not seq_values:
        return []
    allocations: List[SequenceAllocation] = [SequenceAllocation(None, None, False, False) for _ in seq_values]
    if not candles or start_idx < 0 or start_idx >= len(candles):
        return allocations

    def is_dc_candle(idx: int) -> bool:
        flag = dc_flags[idx] if 0 <= idx < len(dc_flags) else None
        if not flag:
            return False
        tod = candles[idx].ts.time()
        return not (dtime(13, 12) <= tod <= dtime(19, 36))

    first_candle = candles[start_idx]
    allocations[0] = SequenceAllocation(
        idx=start_idx,
        ts=first_candle.ts,
        used_dc=is_dc_candle(start_idx),
        synthetic=getattr(first_candle, "synthetic", False),
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
        dc_candidate: Optional[int] = None
        while counted < steps_needed and cur_idx + 1 < len(candles):
            cur_idx += 1
            flag_val = dc_flags[cur_idx]
            is_dc = bool(flag_val) if flag_val is not None else False
            tod = candles[cur_idx].ts.time()
            dc_exception = (dtime(13, 12) <= tod <= dtime(19, 36))
            if is_dc and not dc_exception:
                if counted == steps_needed - 1:
                    dc_candidate = cur_idx
                continue
            counted += 1
        if counted == steps_needed and 0 <= cur_idx < len(candles):
            assign_idx = cur_idx
            assign_ts = candles[cur_idx].ts
            used_dc = False
            if dc_candidate is not None:
                assign_idx = dc_candidate
                assign_ts = candles[dc_candidate].ts
                used_dc = True
            allocations[i] = SequenceAllocation(
                idx=assign_idx,
                ts=assign_ts,
                used_dc=used_dc,
                synthetic=getattr(candles[assign_idx], "synthetic", False),
            )
            prev_idx = cur_idx
            prev_val = cur_val
        else:
            allocations[i] = SequenceAllocation(None, None, False, False)
            prev_idx = cur_idx
            prev_val = cur_val
    return allocations


@dataclass
class OffsetComputation:
    target_ts: datetime
    offset_status: str
    start_idx: Optional[int]
    actual_ts: Optional[datetime]
    start_ref_ts: datetime
    missing_steps: int
    hits: List[SequenceAllocation]


def determine_offset_start(
    candles: List[Candle],
    base_idx: int,
    offset: int,
    minutes_per_step: int = 48,
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


def compute_offset_alignment(
    candles: List[Candle],
    dc_flags: List[Optional[bool]],
    base_idx: int,
    seq_values: List[int],
    offset: int,
    minutes_per_step: int = 48,
) -> OffsetComputation:
    start_idx, target_ts, offset_status = determine_offset_start(candles, base_idx, offset, minutes_per_step, dc_flags)
    base_ts = candles[base_idx].ts.replace(second=0, microsecond=0)
    if target_ts is None:
        target_ts = base_ts + timedelta(minutes=minutes_per_step * offset)
    start_ref_ts = target_ts
    hits: List[SequenceAllocation] = [SequenceAllocation(None, None, False, False) for _ in seq_values]
    actual_ts: Optional[datetime] = None
    missing_steps = 0

    if start_idx is not None and 0 <= start_idx < len(candles):
        actual_ts = candles[start_idx].ts
        start_ref_ts = actual_ts.replace(second=0, microsecond=0)
        hits = compute_sequence_allocations(candles, dc_flags, start_idx, seq_values)
        return OffsetComputation(
            target_ts=target_ts,
            offset_status=offset_status,
            start_idx=start_idx,
            actual_ts=actual_ts,
            start_ref_ts=start_ref_ts,
            missing_steps=missing_steps,
            hits=hits,
        )

    after_idx: Optional[int] = None
    for i, candle in enumerate(candles):
        ts_norm = candle.ts.replace(second=0, microsecond=0)
        if ts_norm >= target_ts:
            after_idx = i
            break

    if after_idx is not None and 0 <= after_idx < len(candles):
        start_idx = after_idx
        actual_ts = candles[start_idx].ts
        start_ref_ts = actual_ts.replace(second=0, microsecond=0)
        delta_minutes = int((actual_ts - target_ts).total_seconds() // 60)
        if delta_minutes < 0:
            delta_minutes = 0
        missing_steps = max(0, delta_minutes // minutes_per_step)
        actual_start_count = missing_steps + 1
        seq_compute: List[int] = [actual_start_count]
        value_to_pos = {actual_start_count: 0}
        for v in seq_values:
            if v > missing_steps:
                if v == actual_start_count:
                    value_to_pos[v] = 0
                else:
                    value_to_pos[v] = len(seq_compute)
                    seq_compute.append(v)

        allocations_compute = compute_sequence_allocations(candles, dc_flags, start_idx, seq_compute)
        value_to_alloc = {val: allocations_compute[idx] for idx, val in enumerate(seq_compute)}
        hits = []
        for v in seq_values:
            if v <= missing_steps:
                hits.append(SequenceAllocation(None, None, False, False))
            else:
                hits.append(value_to_alloc.get(v, SequenceAllocation(None, None, False, False)))

        return OffsetComputation(
            target_ts=target_ts,
            offset_status=offset_status,
            start_idx=start_idx,
            actual_ts=actual_ts,
            start_ref_ts=start_ref_ts,
            missing_steps=missing_steps,
            hits=hits,
        )

    return OffsetComputation(
        target_ts=target_ts,
        offset_status=offset_status,
        start_idx=None,
        actual_ts=None,
        start_ref_ts=start_ref_ts,
        missing_steps=0,
        hits=hits,
    )


def adjust_to_output_tz(candles: List[Candle], input_tz: str) -> Tuple[List[Candle], str]:
    tz_norm = (input_tz or "").strip().upper().replace(" ", "")
    shift_hours = 0
    if tz_norm in {"UTC-5", "UTC-05", "UTC-05:00", "-05:00"}:
        shift_hours = 1
        label = "UTC-5 -> UTC-4 (+1h)"
    else:
        label = "UTC-4 -> UTC-4 (+0h)"
    if shift_hours == 0:
        return candles, label
    delta = timedelta(hours=shift_hours)
    shifted: List[Candle] = [
        Candle(
            ts=c.ts + delta,
            open=c.open,
            high=c.high,
            low=c.low,
            close=c.close,
            synthetic=c.synthetic,
        )
        for c in candles
    ]
    return shifted, label


def insert_synthetic_48m(candles: List[Candle], start_day: Optional[datetime.date]) -> Tuple[List[Candle], int]:
    # Insert 18:00 and 18:48 between 17:12 and 19:36 for every day except start_day.
    if not candles:
        return candles, 0
    by_dt: Dict[datetime, Candle] = {c.ts: c for c in candles}
    dates = sorted({c.ts.date() for c in candles})

    def dt_at(d, hh, mm):
        return datetime.combine(d, dtime(hour=hh, minute=mm))

    added = 0
    for d in dates:
        if start_day is not None and d == start_day:
            continue
        t1712 = dt_at(d, 17, 12)
        t1800 = dt_at(d, 18, 0)
        t1848 = dt_at(d, 18, 48)
        t1936 = dt_at(d, 19, 36)
        c0 = by_dt.get(t1712)
        c3 = by_dt.get(t1936)
        if c0 is None or c3 is None:
            continue
        # Only add if missing
        if t1800 not in by_dt:
            # linear interpolation fraction 1/3
            close = c0.close + (c3.close - c0.close) / 3.0
            open_ = c0.close
            high = max(open_, close)
            low = min(open_, close)
            c1 = Candle(ts=t1800, open=open_, high=high, low=low, close=close, synthetic=True)
            by_dt[t1800] = c1
            added += 1
        if t1848 not in by_dt:
            # fraction 2/3
            close = c0.close + 2.0 * (c3.close - c0.close) / 3.0
            prev = by_dt.get(t1800) or c0
            open_ = prev.close
            high = max(open_, close)
            low = min(open_, close)
            c2 = Candle(ts=t1848, open=open_, high=high, low=low, close=close, synthetic=True)
            by_dt[t1848] = c2
            added += 1
    new_list = list(by_dt.values())
    new_list.sort(key=lambda x: x.ts)
    return new_list, added


def _align_to_48_minutes(ts: datetime) -> datetime:
    # Anchor 48 dakikalık blokları her gün 18:00'e göre hizala.
    anchor = datetime.combine(ts.date(), dtime(hour=18, minute=0))
    if ts < anchor:
        anchor -= timedelta(days=1)
    delta_minutes = int((ts - anchor).total_seconds() // 60)
    block_index = delta_minutes // 48
    return anchor + timedelta(minutes=block_index * 48)


def convert_12m_to_48m(candles: List[Candle]) -> List[Candle]:
    if not candles:
        raise ValueError("Veri boş")

    ordered = sorted(candles, key=lambda c: c.ts)

    groups: Dict[datetime, List[Candle]] = {}
    order: List[datetime] = []

    for candle in ordered:
        block_ts = _align_to_48_minutes(candle.ts)
        if block_ts not in groups:
            groups[block_ts] = []
            order.append(block_ts)
        groups[block_ts].append(candle)

    aggregated: List[Candle] = []
    for block_ts in order:
        block = groups[block_ts]
        if not block:
            continue
        open_ = block[0].open
        close_ = block[-1].close
        high_ = max(c.high for c in block)
        low_ = min(c.low for c in block)
        aggregated.append(Candle(ts=block_ts, open=open_, high=high_, low=low_, close=close_))

    if not aggregated:
        raise ValueError("48 dakikalık mum üretilemedi")

    for i in range(len(aggregated) - 1):
        next_open = aggregated[i + 1].open
        aggregated[i].close = next_open
        if next_open >= aggregated[i].high:
            aggregated[i].high = next_open
        if next_open <= aggregated[i].low:
            aggregated[i].low = next_open

    last = aggregated[-1]
    if last.close >= last.high:
        last.high = last.close
    if last.close <= last.low:
        last.low = last.close

    return aggregated


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="app48", description="48m counting with DC-skip and synthetic gap candles (UTC-4)")
    p.add_argument("--csv", required=True, help="CSV dosya yolu")
    p.add_argument("--input-tz", choices=["UTC-4", "UTC-5"], default="UTC-5", help="Girdi TZ (UTC-4/UTC-5); çıktı UTC-4")
    p.add_argument("--sequence", choices=list(SEQUENCES.keys()), default="S2", help="Kullanılacak dizi: S1 veya S2")
    p.add_argument("--offset", type=int, choices=[-3, -2, -1, 0, 1, 2, 3], default=0, help="Başlangıç ofseti (-3..+3)")
    p.add_argument("--show-dc", action="store_true", help="Çıktıda DC bilgisini göster")

    args = p.parse_args(argv)

    candles = load_candles(args.csv)
    if not candles:
        print("Uyarı: veri yüklenemedi ya da boş")
        return 1

    # Normalize to UTC-4 output
    candles, tz_label = adjust_to_output_tz(candles, args.input_tz)

    tf_minutes_est = estimate_timeframe_minutes(candles)
    print(f"Data: {len(candles)} candles")
    print(f"Range: {fmt_ts(candles[0].ts)} -> {fmt_ts(candles[-1].ts)}")
    print(f"TZ: {tz_label}")

    # Start fixed at 18:00 (UTC-4 view)
    start_tod = dtime(hour=18, minute=0)
    base_idx, align_status = find_start_index(candles, start_tod)
    start_day = candles[base_idx].ts.date() if 0 <= base_idx < len(candles) else None

    # Insert synthetic 18:00 and 18:48 for every day except start_day
    candles2, added = insert_synthetic_48m(candles, start_day)
    if added:
        print(f"Synthetic inserted: {added} candles (18:00, 18:48 for days after start)")
    candles = candles2

    # Re-find start after insertion to ensure index validity
    base_idx, align_status = find_start_index(candles, start_tod)

    seq_values = SEQUENCES[args.sequence][:]
    dc_flags = compute_dc_flags(candles)
    alignment = compute_offset_alignment(
        candles,
        dc_flags,
        base_idx,
        seq_values,
        args.offset,
        minutes_per_step=48,
    )
    start_idx = alignment.start_idx
    target_ts = alignment.target_ts
    print(
        f"Start: base_idx={base_idx} ts={fmt_ts(candles[base_idx].ts)} ({align_status}); "
        f"offset={args.offset} -> target_ts={fmt_ts(target_ts)} ({alignment.offset_status}) "
        f"idx={start_idx if start_idx is not None else '-'} actual_ts={fmt_ts(alignment.actual_ts)} "
        f"missing_steps={alignment.missing_steps}"
    )

    print(f"Sequence: {args.sequence} {seq_values}")

    hits = alignment.hits

    def predicted_ts_for(v: int, use_target: bool = False) -> datetime:
        # 48m prediction - DC'leri dikkate al
        first = seq_values[0]
        
        # Eğer veri dışındaysak, son gerçek mumdan başla
        if not use_target:
            # Son dizideki bilinen değeri bul
            last_known_v = None
            last_known_ts = None
            last_known_idx = -1
            for seq_v, hit in zip(seq_values, alignment.hits):
                if hit.idx is not None and hit.ts is not None and 0 <= hit.idx < len(candles):
                    last_known_v = seq_v
                    last_known_ts = hit.ts
                    last_known_idx = hit.idx
            
            # Eğer v son bilinen değerden sonraysa:
            if last_known_v is not None and v > last_known_v:
                # Son gerçek mumdan başla
                actual_last_candle_ts = candles[-1].ts
                actual_last_idx = len(candles) - 1
                
                # DC'leri dikkate al - sadece NON-DC adımları say
                non_dc_steps_from_last_known_to_end = 0
                for i in range(last_known_idx + 1, actual_last_idx + 1):
                    is_dc = dc_flags[i] if i < len(dc_flags) else False
                    if not is_dc:
                        non_dc_steps_from_last_known_to_end += 1
                
                steps_from_end_to_v = (v - last_known_v) - non_dc_steps_from_last_known_to_end
                return actual_last_candle_ts + timedelta(minutes=48 * steps_from_end_to_v)
        
        # Aksi halde dizinin başından hesapla
        delta_steps = max(0, v - first)
        base_ts = alignment.target_ts if use_target else alignment.start_ref_ts
        return base_ts + timedelta(minutes=48 * delta_steps)

    for v, hit in zip(seq_values, hits):
        idx = hit.idx
        ts = hit.ts
        if idx is None or ts is None or not (0 <= idx < len(candles)):
            use_target = alignment.missing_steps and v <= alignment.missing_steps
            pred_ts = predicted_ts_for(v, use_target=bool(use_target))
            print(f"{v} -> predicted_ts={fmt_ts(pred_ts)} (pred) OC=- PrevOC=-")
            continue
        syn_tag = " (syn)" if hit.synthetic else ""
        pip_val = candles[idx].close - candles[idx].open
        prev_pip = candles[idx - 1].close - candles[idx - 1].open if idx - 1 >= 0 else None
        base_line = f"{v} -> idx={idx} ts={fmt_ts(ts)} OC={fmt_pip(pip_val)} PrevOC={fmt_pip(prev_pip)}{syn_tag}"
        if args.show_dc:
            dc_flag = dc_flags[idx] if 0 <= idx < len(dc_flags) else None
            base_line += f" DC={dc_flag} used_dc={hit.used_dc}"
        print(base_line)

    return 0


@dataclass
class IOUResult:
    """Result of IOU (Inverse OC - Uniform sign) analysis."""
    seq_value: int
    index: int
    timestamp: datetime
    oc: float
    prev_oc: float
    prev_index: int
    prev_timestamp: datetime


def analyze_iou(
    candles: List[Candle],
    sequence: str,
    limit: float,
) -> Dict[int, List[IOUResult]]:
    """
    Analyze IOU candles for all offsets (-3 to +3).
    
    IOU Criteria:
        1. |OC| >= limit
        2. |PrevOC| >= limit
        3. OC and PrevOC have SAME signs (++ or --)
    
    Returns: Dict[offset] -> List[IOUResult]
    """
    results: Dict[int, List[IOUResult]] = {}
    
    base_idx, _ = find_start_index(candles, DEFAULT_START_TOD)
    dc_flags = compute_dc_flags(candles)
    
    # Use FULL sequence for allocation, FILTERED for IOU check
    seq_values_full = SEQUENCES[sequence]
    seq_values_filtered = SEQUENCES_FILTERED[sequence]
    
    for offset in range(-3, 4):
        iou_list: List[IOUResult] = []
        
        start_idx, target_ts, offset_status = determine_offset_start(candles, base_idx, offset, MINUTES_PER_STEP)
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
                # No data to work with
                results[offset] = iou_list
                continue
        
        # Build compute sequence
        actual_start_count = missing_steps + 1
        seq_compute: List[int] = [actual_start_count]
        for v in seq_values_full:
            if v > missing_steps:
                if v != actual_start_count:
                    seq_compute.append(v)
        
        # Compute allocations for synthetic sequence
        allocations = compute_sequence_allocations(candles, dc_flags, start_idx, seq_compute)
        
        # Build mapping: seq_value -> allocation
        seq_map: Dict[int, SequenceAllocation] = {}
        for idx, val in enumerate(seq_compute):
            seq_map[val] = allocations[idx]
        
        # For values <= missing_steps, mark as None
        for v in seq_values_full:
            if v <= missing_steps:
                seq_map[v] = SequenceAllocation(None, None, False, False)
        
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
            if abs(oc) < limit or abs(prev_oc) < limit:
                continue
            
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


if __name__ == "__main__":
    raise SystemExit(main())
