import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, time as dtime, timedelta
from typing import List, Optional, Tuple, Dict


MINUTES_PER_STEP = 90
DEFAULT_START_TOD = dtime(hour=18, minute=0)


@dataclass
class Candle:
    ts: datetime
    open: float
    high: float
    low: float
    close: float


SEQUENCES: Dict[str, List[int]] = {
    "S1": [1, 3, 7, 13, 21, 31, 43, 57, 73, 91, 111, 133, 157],
    "S2": [1, 5, 9, 17, 25, 37, 49, 65, 81, 101, 121, 145, 169],
}


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
    # ISO with timezone: treat as local wall time, drop tzinfo
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt
    except Exception:
        pass
    # Common patterns
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
    # Simple CSV reader with flexible header matching
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
        
        # 18:00 mumu ASLA DC olamaz
        if cur.ts.hour == DEFAULT_START_TOD.hour and cur.ts.minute == DEFAULT_START_TOD.minute:
            cond = False
        else:
            # Hafta kapanış mumu (16:00) DC olamaz
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


def compute_sequence_indices_with_dc_exception(
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
    dc_flags: Optional[List[Optional[bool]]] = None,
    minutes_per_step: int = MINUTES_PER_STEP,
) -> Tuple[Optional[int], Optional[datetime], str]:
    """
    NEW LOGIC (2025-10-07): Offset = Non-DC candle count
    
    Determines the offset start index by counting non-DC candles from base.
    - Offset +1: 1st non-DC candle after base
    - Offset +2: 2nd non-DC candle after base
    - Offset -1: 1st non-DC candle before base
    - DC candles are skipped in counting
    
    Returns:
        (start_idx, target_ts, status)
        - start_idx: Index of the non-DC candle at offset position
        - target_ts: Timestamp of that candle (for reference)
        - status: "aligned" if found, "before-data"/"after-data" if out of bounds
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
) -> OffsetComputation:
    start_idx, target_ts, offset_status = determine_offset_start(candles, base_idx, offset, dc_flags)
    base_ts = candles[base_idx].ts.replace(second=0, microsecond=0)
    if target_ts is None:
        target_ts = base_ts + timedelta(minutes=MINUTES_PER_STEP * offset)
    start_ref_ts = target_ts
    hits: List[SequenceAllocation] = [SequenceAllocation(None, None, False) for _ in seq_values]
    actual_ts: Optional[datetime] = None
    missing_steps = 0

    if start_idx is not None and 0 <= start_idx < len(candles):
        actual_ts = candles[start_idx].ts
        start_ref_ts = actual_ts.replace(second=0, microsecond=0)
        
        # NEW LOGIC: No DC adjustment needed - determine_offset_start already returns non-DC candle
        # Offset counting skips DC candles, so start_idx is guaranteed to be non-DC
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
        missing_steps = max(0, delta_minutes // MINUTES_PER_STEP)
        
        # NEW LOGIC: No DC adjustment - use original dc_flags
        # This branch is rarely hit with new offset logic (only for time-based edge cases)
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
                hits.append(SequenceAllocation(None, None, False))
            else:
                hits.append(value_to_alloc.get(v, SequenceAllocation(None, None, False)))

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


def fmt_ts(dt: Optional[datetime]) -> str:
    if dt is None:
        return "-"
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def predict_next_candle_time(current_ts: datetime, minutes_per_step: int = MINUTES_PER_STEP) -> datetime:
    """
    Haftasonu boşluğunu dikkate alarak bir sonraki mum zamanını hesaplar.
    Piyasa: Cuma 16:00'da kapanır, Pazar 18:00'da açılır.
    """
    next_ts = current_ts + timedelta(minutes=minutes_per_step)
    
    # Cuma 16:00 sonrası kontrolü - hafta kapanışı
    weekday = current_ts.weekday()  # 0=Pazartesi, 4=Cuma, 5=Cumartesi, 6=Pazar
    
    # Eğer mevcut mum Cuma 16:00 ise, sonraki mum Pazar 18:00 olmalı
    if weekday == 4 and current_ts.hour == 16 and current_ts.minute == 0:
        # Cuma 16:00'dan sonra Pazar 18:00'a geç
        days_to_sunday = 2  # Cuma'dan Pazar'a
        next_ts = datetime.combine(current_ts.date() + timedelta(days=days_to_sunday), dtime(hour=18, minute=0))
        return next_ts
    
    # Eğer mevcut mum Cuma 14:24 ise ve bir sonraki mum 16:00'ı geçiyorsa
    if weekday == 4 and current_ts.hour == 14 and current_ts.minute == 24:
        # Bu durumda sonraki mum Cuma 16:00 (son mum)
        return datetime.combine(current_ts.date(), dtime(hour=16, minute=0))
    
    # Normal durum: basitçe dakika ekle
    return next_ts


def predict_time_after_n_steps(base_ts: datetime, n_steps: int, minutes_per_step: int = MINUTES_PER_STEP) -> datetime:
    """
    Verilen zamandan n adım sonrasını hesaplar, haftasonu boşluğunu dikkate alır.
    """
    current_ts = base_ts
    for _ in range(n_steps):
        current_ts = predict_next_candle_time(current_ts, minutes_per_step)
    return current_ts


def fmt_pip(delta: Optional[float]) -> str:
    if delta is None:
        return "-"
    return f"{delta:+.5f}"


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(
        prog="app90.counter",
        description="90m sayımı, DC ve offset desteği",
    )
    p.add_argument("--csv", required=True, help="CSV dosya yolu")
    p.add_argument("--sequence", choices=list(SEQUENCES.keys()), default="S2", help="Kullanılacak dizi: S1 veya S2")
    p.add_argument("--offset", type=int, choices=[-3, -2, -1, 0, 1, 2, 3], default=0, help="Başlangıç ofseti (-3..+3)")
    p.add_argument("--show-dc", action="store_true", help="Çıktıda DC bilgisini göster")
    p.add_argument("--predict", type=int, default=None, help="Belirli dizi değerinin (örn. 37) tahmini zamanı")
    p.add_argument("--predict-next", action="store_true", help="Veriye göre bir sonraki dizi değerinin tahmini zamanı")

    args = p.parse_args(argv)

    candles = load_candles(args.csv)
    if not candles:
        print("Uyarı: veri yüklenemedi ya da boş")
        return 1

    print(f"Data: {len(candles)} candles")
    print(f"Range: {fmt_ts(candles[0].ts)} -> {fmt_ts(candles[-1].ts)}")

    # Start fixed 18:00; offset relative to base 18:00 candle
    start_tod = DEFAULT_START_TOD
    base_idx, align_status = find_start_index(candles, start_tod)
    dc_flags = compute_dc_flags(candles)
    seq_values = SEQUENCES[args.sequence][:]
    alignment = compute_offset_alignment(candles, dc_flags, base_idx, seq_values, args.offset)
    start_idx = alignment.start_idx
    target_ts = alignment.target_ts
    offset_status = alignment.offset_status
    actual_ts = alignment.actual_ts
    start_ref_ts = alignment.start_ref_ts
    print(
        f"Start: base_idx={base_idx} ts={fmt_ts(candles[base_idx].ts)} ({align_status}); "
        f"offset={args.offset} -> target_ts={fmt_ts(target_ts)} ({offset_status}) "
        f"idx={start_idx if start_idx is not None else '-'} actual_ts={fmt_ts(actual_ts)} "
        f"missing_steps={alignment.missing_steps}"
    )

    print(f"Sequence: {args.sequence} {seq_values}")

    hits = alignment.hits

    def predicted_ts_for(v: int, use_target: bool = False) -> datetime:
        # Haftasonu boşluğunu dikkate alarak prediction yap
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
                # Son gerçek mumdan başla (verinin en sonundan)
                actual_last_candle_ts = candles[-1].ts
                actual_last_idx = len(candles) - 1
                
                # Son dizideki değerden son gerçek muma kadar kaç NON-DC adım var?
                # DC'ler sayımda atlanıyor, bu yüzden DC olmayan mumları saymalıyız
                non_dc_steps_from_last_known_to_end = 0
                for i in range(last_known_idx + 1, actual_last_idx + 1):
                    is_dc = dc_flags[i] if i < len(dc_flags) else False
                    if not is_dc:
                        non_dc_steps_from_last_known_to_end += 1
                
                # v'ye ulaşmak için toplam adım sayısı (DC'siz)
                # v - last_known_v = gereken toplam adım
                # non_dc_steps_from_last_known_to_end = zaten geçilmiş adımlar
                steps_from_end_to_v = (v - last_known_v) - non_dc_steps_from_last_known_to_end
                
                return predict_time_after_n_steps(actual_last_candle_ts, steps_from_end_to_v)
        
        # Aksi halde dizinin başından hesapla (eski mantık)
        delta_steps = max(0, v - first)
        base_ts = alignment.target_ts if use_target else start_ref_ts
        return predict_time_after_n_steps(base_ts, delta_steps)

    # Prediction branch
    if args.predict is not None or args.predict_next:
        target_v: Optional[int] = None
        if args.predict is not None:
            target_v = int(args.predict)
            if target_v not in seq_values:
                print(f"Uyarı: hedef {target_v} seçili dizide yok")
        else:
            # pick first seq value that is out-of-range
            for v, hit in zip(seq_values, hits):
                idx = hit.idx
                if idx is None or not (0 <= idx < len(candles)):
                    target_v = v
                    break
            if target_v is None:
                print("Uyarı: tüm dizi değerleri veri aralığında; tahmin edilecek bir sonraki değer yok")
        if target_v is not None:
            pred = predicted_ts_for(target_v)
            # If we already have actual in range, show both
            actual_idx = None
            actual_ts_val = None
            for v, hit in zip(seq_values, hits):
                if v == target_v:
                    actual_idx = hit.idx
                    actual_ts_val = hit.ts
                    break
            if actual_idx is not None and 0 <= actual_idx < len(candles):
                actual_ts_fmt = fmt_ts(actual_ts_val if actual_ts_val else candles[actual_idx].ts)
                pip_val = candles[actual_idx].close - candles[actual_idx].open
                prev_pip = candles[actual_idx - 1].close - candles[actual_idx - 1].open if actual_idx - 1 >= 0 else None
                print(
                    f"Prediction: v={target_v} predicted_ts={fmt_ts(pred)} actual_idx={actual_idx} "
                    f"actual_ts={actual_ts_fmt} OC={fmt_pip(pip_val)} PrevOC={fmt_pip(prev_pip)}"
                )
            else:
                print(f"Prediction: v={target_v} predicted_ts={fmt_ts(pred)} (beyond data) OC=- PrevOC=-")
        return 0

    # Default listing branch
    for v, hit in zip(seq_values, hits):
        idx = hit.idx
        ts = hit.ts
        if idx is None or ts is None or not (0 <= idx < len(candles)):
            use_target = v <= alignment.missing_steps if alignment.missing_steps else False
            pred_ts = predicted_ts_for(v, use_target=use_target)
            print(f"{v} -> predicted_ts={fmt_ts(pred_ts)} (pred) OC=- PrevOC=-")
            continue
        ts_display = ts
        pip_val = candles[idx].close - candles[idx].open
        prev_pip = candles[idx - 1].close - candles[idx - 1].open if idx - 1 >= 0 else None
        if args.show_dc:
            dc_flag = dc_flags[idx] if 0 <= idx < len(dc_flags) else None
            print(
                f"{v} -> idx={idx} ts={fmt_ts(ts_display)} OC={fmt_pip(pip_val)} PrevOC={fmt_pip(prev_pip)} "
                f"DC={dc_flag} used_dc={hit.used_dc}"
            )
        else:
            print(f"{v} -> idx={idx} ts={fmt_ts(ts_display)} OC={fmt_pip(pip_val)} PrevOC={fmt_pip(prev_pip)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
