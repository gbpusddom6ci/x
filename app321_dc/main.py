import argparse
from typing import List

from app321.main import (
    load_candles,
    compute_dc_flags,
    fmt_ts,
)


def main(argv: List[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="app321-dc-list", description="List Distorted Candles for 60m (app321)")
    p.add_argument("--csv", required=True, help="CSV dosya yolu")
    args = p.parse_args(argv)

    candles = load_candles(args.csv)
    if not candles:
        print("Uyarı: veri bulunamadı")
        return 1
    flags = compute_dc_flags(candles)
    total = 0
    for i, (c, f) in enumerate(zip(candles, flags)):
        if not f:
            continue
        print(f"idx={i} ts={fmt_ts(c.ts)} O={c.open} H={c.high} L={c.low} C={c.close}")
        total += 1
    print(f"DC count: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

