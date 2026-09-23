#!/usr/bin/env python3
"""
templates_cli.py -- build the hex template library from Puzzle #1's solution screen.

    python3 templates_cli.py --screen solution.png \\
        --answer 4487FC620AD0C4C67E80BE342B2EA1F5A3DC482BE6FB9C2451007322EA8BE35F \\
        --out hexlib.json

The screen must segment into exactly as many components as the answer has
characters, or the positional labels are misaligned and every template is
contaminated. That is checked, and it is fatal by default -- use --loose to
inspect a screen that will not segment cleanly, but do not build a library
with it.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import templates as tpl   # noqa: E402

PUZZLE1_ANSWER = "4487FC620AD0C4C67E80BE342B2EA1F5A3DC482BE6FB9C2451007322EA8BE35F"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--screen", required=True, help="still of the solution screen")
    ap.add_argument("--answer", default=PUZZLE1_ANSWER)
    ap.add_argument("--out", default="hexlib.json")
    ap.add_argument("--lo-pct", type=float, default=50.0)
    ap.add_argument("--hi-pct", type=float, default=99.9)
    ap.add_argument("--min-ink", default="12")
    ap.add_argument("--close", type=int, default=1)
    ap.add_argument("--loose", action="store_true",
                    help="do not abort on a component-count mismatch (inspection only)")
    args = ap.parse_args()

    min_ink = args.min_ink if args.min_ink == "auto" else int(args.min_ink)
    try:
        r = tpl.build(args.screen, args.answer, out_path=args.out,
                      lo_pct=args.lo_pct, hi_pct=args.hi_pct,
                      min_ink=min_ink, close=args.close, strict=not args.loose)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    acc = r["self_classification"]
    print(f"components   : {r['n_components']} (answer has {len(args.answer)})")
    if r.get("tuned"):
        print(f"autotuned    : {r['tuned']}")
    print(f"digits covered: {16 - len(r['missing_digits'])}/16"
          + (f"  MISSING {r['missing_digits']}" if r["missing_digits"] else ""))
    print(f"self-classify : {acc['correct']}/{acc['total']} = {acc['accuracy']:.1%}")
    print(f"wrote {args.out}")
    if r["missing_digits"]:
        print("\nWARNING: a library missing digits cannot read those characters "
              "anywhere. Every glyph of a missing class will be forced onto some "
              "other class, confidently and wrongly.")
    if acc["accuracy"] < 0.90:
        print("\nWARNING: this library cannot reliably re-read the screen it was "
              "built from. It will not read anything harder.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
