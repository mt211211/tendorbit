#!/usr/bin/env python3
"""
solve.py -- assemble 64-hex candidates from one or more reads and sweep them.

    python3 solve.py --read out/p1/read.json out/p2/read.json --fragment 6A6B0860B4

Prints a feasibility plan before doing anything. If the read leaves more than
about 8 positions open the sweep is refused, because it could not finish -- see
the table in the project README. The fix in that case is a better source, not a
bigger machine.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import assemble as asm            # noqa: E402
from oracle import TARGET         # noqa: E402


def load_readings(paths, block_policy="best"):
    """Collect per-glyph readings from run_pipeline outputs, in file order."""
    readings = []
    for p in paths:
        with open(p) as fh:
            doc = json.load(fh)
        for w in doc.get("windows", []):
            blocks = w.get("blocks", [])
            if not blocks:
                continue
            if block_policy == "best":
                # The payload block is the one that correlates well against hex
                # templates; instruction text ('MIRROR') scores markedly lower.
                blocks = [max(blocks, key=lambda b: b["mean_score"])]
            for b in blocks:
                readings.extend(b["readings"])
    return readings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--read", nargs="+", required=True, help="read.json file(s)")
    ap.add_argument("--fragment", default=None,
                    help="a known substring; every consistent placement is tried")
    ap.add_argument("--fragment-at", type=int, default=None,
                    help="pin the fragment at this offset instead of searching")
    ap.add_argument("--target", default=TARGET)
    ap.add_argument("--budget", type=float, default=asm.DEFAULT_BUDGET)
    ap.add_argument("--all-blocks", action="store_true",
                    help="use every block, not just the best-scoring one per window")
    ap.add_argument("--widen", action="store_true",
                    help="open every untrusted position to all 16 digits")
    ap.add_argument("--force", action="store_true",
                    help="run a sweep the plan says cannot finish")
    args = ap.parse_args()

    readings = load_readings(args.read, "all" if args.all_blocks else "best")
    trusted = sum(1 for r in readings if r.get("trusted"))
    cut = sum(1 for r in readings if r.get("cut"))
    print(f"glyphs read : {len(readings)}  trusted={trusted}  truncated={cut}")
    if len(readings) != 64:
        print(f"NOTE: {len(readings)} glyph positions, but the key is 64 characters. "
              "Positions with no glyph are treated as fully unknown.")

    if args.fragment:
        probe = asm.constraints_from_readings(readings, length=64, widen=args.widen)
        placements = asm.apply_fragment(probe, args.fragment, args.fragment_at)
        if not placements:
            print(f"\nThe fragment {args.fragment!r} is NOT consistent with this read "
                  "at any offset.")
            print("Either the read is wrong, or the fragment is. Note that the "
                  "upstream analysis/ ledger withdraws the 10-character seam-1 "
                  "reading (row 9: 'No reading is claimed'), so the fragment is a "
                  "hypothesis to test, not a constraint to assume. Re-run without "
                  "--fragment to drop that assumption.")
            return 1
        print(f"fragment {args.fragment} fits at offsets: "
              f"{[p[0] for p in placements]}")

    print("\nsweeping (widest rung reached is reported):")
    res = asm.sweep_ladder(readings, fragment=args.fragment,
                           fragment_at=args.fragment_at, target=args.target,
                           budget=int(args.budget), progress=1_000_000)

    if res["status"] == "MATCH":
        print(f"\n  MATCH {res['candidate']}")
        print(f"  found on rung: {res['rung']}")
        print(f"  verify: python3 oracle.py \"{res['candidate']}\"")
        return 0

    tested = res.get("tested_total", res.get("tested", 0))
    if res["status"] == "BUDGET":
        p = res["plan"]
        print(f"\nSTOPPED: {tested:,} candidates tested; the next rung needs "
              f"{p['candidates']:.3e}, over the {float(args.budget):.3e} budget, "
              f"with {p['fully_unknown']} positions carrying no evidence at all.")
        print("A sweep that cannot finish yields no information. The gap has to be "
              "closed by reading more glyphs -- which needs a source showing the "
              "complete characters -- not by more compute.")
    else:
        print(f"\nEXHAUSTED after {tested:,} candidates without a match.")
        print("Every rung the budget allowed was tried. If the read is right, the "
              "escrow address or the fragment is not.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
