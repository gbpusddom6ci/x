import argparse
from typing import List

from app48.main import (
    Candle,
    load_candles,
    compute_dc_flags,
    adjust_to_output_tz,
    insert_synthetic_48m,
    fmt_ts,
)
from datetime import time as dtime


def main(argv: List[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="app48-dc-list", description="List Distorted Candles for 48m with synthetic gap candles")
    p.add_argument("--csv", required=True, help="CSV dosya yolu")
    p.add_argument("--input-tz", choices=["UTC-4", "UTC-5"], default="UTC-5", help="Girdi TZ; çıktı UTC-4")
    p.add_argument("--show-non-synthetic", action="store_true", help="Sadece gerçek (non-synthetic) DC'leri göster")
    p.add_argument("--show-synthetic", action="store_true", help="Sadece sentetik DC'leri göster")

    args = p.parse_args(argv)

    candles = load_candles(args.csv)
    if not candles:
        print("Uyarı: veri bulunamadı")
        return 1

    # Normalize to UTC-4 if necessary
    candles, tz_label = adjust_to_output_tz(candles, args.input_tz)

    # Synthetic insertion (skip start day)
    start_tod = dtime(hour=18, minute=0)
    # Determine start day by finding first 18:00
    base_idx = next((i for i, c in enumerate(candles) if c.ts.time() == start_tod), 0)
    start_day = candles[base_idx].ts.date() if candles else None
    candles, added = insert_synthetic_48m(candles, start_day)

    flags = compute_dc_flags(candles)

    print(f"TZ: {tz_label}")
    print(f"Synthetic inserted: {added}")
    total = 0
    for i, (c, f) in enumerate(zip(candles, flags)):
        if not f:
            continue
        if args.show_synthetic and not c.synthetic:
            continue
        if args.show_non_synthetic and c.synthetic:
            continue
        tag = "syn" if c.synthetic else "real"
        print(f"idx={i} ts={fmt_ts(c.ts)} tag={tag} O={c.open} H={c.high} L={c.low} C={c.close}")
        total += 1
    print(f"DC count: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
