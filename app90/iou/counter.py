# app90/iou/counter.py - Simplified version
# Full implementation to be added later
# For now, import from parent counter module and extend

from ..counter import (
    Candle,
    SEQUENCES,
    normalize_key,
    parse_float,
    parse_time_value,
    load_candles,
    find_start_index,
    compute_dc_flags,
    compute_sequence_allocations,
    SequenceAllocation,
    determine_offset_start,
    fmt_ts,
    fmt_pip,
    MINUTES_PER_STEP,
    DEFAULT_START_TOD,
)

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

# Filtered sequences (exclude early values for IOU)
SEQUENCES_FILTERED: Dict[str, List[int]] = {
    "S1": [7, 13, 21, 31, 43, 57, 73, 91, 111, 133, 157],  # excludes 1, 3
    "S2": [9, 17, 25, 37, 49, 65, 81, 101, 121, 145, 169],  # excludes 1, 5
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
    
    seq_values_full = SEQUENCES[sequence]
    seq_values_filtered = SEQUENCES_FILTERED[sequence]
    
    for offset in range(-3, 4):
        iou_list: List[IOUResult] = []
        
        start_idx, target_ts, offset_status = determine_offset_start(candles, base_idx, offset, dc_flags, MINUTES_PER_STEP)
        base_ts = candles[base_idx].ts.replace(second=0, microsecond=0)
        if target_ts is None:
            target_ts = base_ts + timedelta(minutes=MINUTES_PER_STEP * offset)
        
        missing_steps = 0
        
        if start_idx is None or start_idx < 0 or start_idx >= len(candles):
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
                results[offset] = iou_list
                continue
        
        actual_start_count = missing_steps + 1
        seq_compute: List[int] = [actual_start_count]
        for v in seq_values_full:
            if v > missing_steps:
                if v != actual_start_count:
                    seq_compute.append(v)
        
        allocations = compute_sequence_allocations(candles, dc_flags, start_idx, seq_compute)
        
        seq_map: Dict[int, SequenceAllocation] = {}
        for idx, val in enumerate(seq_compute):
            seq_map[val] = allocations[idx]
        
        for v in seq_values_full:
            if v <= missing_steps:
                seq_map[v] = SequenceAllocation(None, None, False)
        
        for seq_val in seq_values_filtered:
            alloc = seq_map.get(seq_val)
            if alloc is None or alloc.idx is None:
                continue
            
            idx = alloc.idx
            if idx <= 0 or idx >= len(candles):
                continue
            
            candle = candles[idx]
            prev_candle = candles[idx - 1]
            
            ts = candle.ts
            # 18:00 mumları asla IOU olamaz
            if ts.hour == 18 and ts.minute == 0:
                continue
            
            # 19:30 mumları Pazar günleri hariç asla IOU olamaz
            if ts.hour == 19 and ts.minute == 30:
                if ts.weekday() != 6:  # 6 = Pazar
                    continue
            
            # Cuma günündeki 16:30 mumları asla IOU olamaz
            if ts.hour == 16 and ts.minute == 30:
                if ts.weekday() == 4:  # 4 = Cuma
                    continue
            
            oc = candle.close - candle.open
            prev_oc = prev_candle.close - prev_candle.open
            
            if abs(oc) < limit or abs(prev_oc) < limit:
                continue
            
            if abs(abs(oc) - limit) < tolerance or abs(abs(prev_oc) - limit) < tolerance:
                continue
            
            if not ((oc > 0 and prev_oc > 0) or (oc < 0 and prev_oc < 0)):
                continue
            
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


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    p = argparse.ArgumentParser(
        prog="app90.iou.counter",
        description="90m IOU Analysis",
    )
    p.add_argument("--csv", required=True, help="CSV file (90m candles)")
    p.add_argument("--sequence", choices=["S1", "S2"], default="S1", help="Sequence")
    p.add_argument("--limit", type=float, default=0.75, help="IOU limit (default: 0.75)")
    args = p.parse_args(argv)

    candles = load_candles(args.csv)
    if not candles:
        print("Warning: no data")
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
    
    for offset in range(-3, 4):
        iou_list = results[offset]
        if iou_list:
            print(f"Offset: {offset:+d}")
            for iou in iou_list:
                print(f"  Seq={iou.seq_value}, Index={iou.index}, Time={fmt_ts(iou.timestamp)}")
                print(f"    OC: {fmt_pip(iou.oc)}, PrevOC: {fmt_pip(iou.prev_oc)}")
            print()
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
