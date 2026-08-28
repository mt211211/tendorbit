#!/usr/bin/env python3
"""
run_pipeline.py -- read the glyphs out of a frame folder and report what is known.

    python3 run_pipeline.py --frames f1/ --templates hexlib.json --out out/p1

Each run writes annotated debug crops to --out so the windows can be refined by
looking at what the pipeline actually saw:

    <out>/activity.txt        per-frame ink, and the windows derived from it
    <out>/w<N>_overview.png   the stretched residual, every component boxed
                              (green trusted / orange low-confidence / red CUT)
    <out>/w<N>_sheet.png      every crop in reading order, labelled
    <out>/w<N>_orient.png     one glyph in all 8 dihedral views
    <out>/read.json           the machine-readable read

The pipeline reports what it can support and marks the rest '?'. It does not
produce a 64-character string by filling gaps with its best guess.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import glyphlib as gl      # noqa: E402
import templates as tpl    # noqa: E402
import match as mt         # noqa: E402
import debugview as dv     # noqa: E402


def _jsonable(o):
    """numpy scalars leak in through split-piece box coordinates."""
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.bool_,)):
        return bool(o)
    raise TypeError(f"not JSON serializable: {type(o).__name__}")


def analyse_window(folder, background, window, lib, out_dir, tag,
                   lo_pct, hi_pct, signed=False):
    lo, hi = window
    proj = gl.max_projection(folder, background, frames=range(lo, hi), signed=signed)
    st = gl.stretch(proj, lo_pct, hi_pct)
    glyphs = gl.segment(st)
    if not glyphs:
        return {"window": [lo, hi], "blocks": [], "note": "no components found"}

    res = mt.read_blocks(glyphs, lib, st)
    for b in res["blocks"]:
        dv.save_overview(st, b["glyphs"], os.path.join(out_dir, f"{tag}_b{b['index']}_overview.png"),
                         b["readings"], f"{tag} block{b['index']} {res['orientation']}")
        dv.save_contact_sheet(b["glyphs"], os.path.join(out_dir, f"{tag}_b{b['index']}_sheet.png"),
                              b["readings"])
        first = next((g for g in b["glyphs"] if g is not None), None)
        if first is not None:
            dv.save_orientations(first, os.path.join(out_dir, f"{tag}_b{b['index']}_orient.png"))
    dv.save_overview(st, glyphs, os.path.join(out_dir, f"{tag}_overview.png"), None,
                     f"{tag} all components")

    return {
        "window": [lo, hi],
        "orientation": res["orientation"],
        "orientation_scores": res["orientation_scores"],
        "blocks": [{
            "index": b["index"], "n": b["n"], "text": b["text"],
            "trusted_text": b["trusted_text"], "mean_score": b["mean_score"],
            "n_trusted": b["n_trusted"], "n_cut": b["n_cut"],
            "readings": [{k: v for k, v in r.items() if k != "alternatives"} |
                         {"alternatives": [{"char": a["char"], "score": a["score"]}
                                           for a in r["alternatives"]]}
                         for r in b["readings"]],
        } for b in res["blocks"]],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", required=True, help="folder of PNG frames")
    ap.add_argument("--templates", required=True, help="hex library JSON")
    ap.add_argument("--out", default="out")
    ap.add_argument("--bg-sample", type=int, default=240)
    ap.add_argument("--bg-mode", choices=("median", "percentile", "mean"),
                    default="median",
                    help="percentile survives a payload held over much of the clip")
    ap.add_argument("--bg-pct", type=float, default=20.0)
    ap.add_argument("--lo-pct", type=float, default=50.0)
    ap.add_argument("--hi-pct", type=float, default=99.9)
    ap.add_argument("--activity-step", type=int, default=2)
    ap.add_argument("--signed", action="store_true",
                    help="glyphs may be darker than the background")
    ap.add_argument("--window", action="append", default=None,
                    metavar="LO:HI", help="force a frame window (repeatable)")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    lib = tpl.load(args.templates)["templates"]

    print(f"[1/4] temporal background from {args.frames} ({args.bg_mode})", flush=True)
    bg = gl.temporal_background(args.frames, sample=args.bg_sample,
                                mode=args.bg_mode, pct=args.bg_pct)

    if args.window:
        windows = [tuple(int(v) for v in w.split(":")) for w in args.window]
        print(f"[2/4] using forced windows {windows}", flush=True)
    else:
        print("[2/4] locating payload windows", flush=True)
        idx, counts = gl.activity_profile(args.frames, bg, step=args.activity_step,
                                          signed=args.signed)
        windows = gl.find_windows(idx, counts)
        if not windows and args.bg_mode == "median":
            # A median background absorbs a payload that is on screen for a
            # large share of the clip, and then subtracts it away to nothing --
            # which looks identical to "this video has no payload". Retry with a
            # low-percentile background before believing that.
            print("      no windows under a median background; "
                  "retrying with a percentile background", flush=True)
            bg = gl.temporal_background(args.frames, sample=args.bg_sample,
                                        mode="percentile", pct=args.bg_pct)
            idx, counts = gl.activity_profile(args.frames, bg,
                                              step=args.activity_step,
                                              signed=args.signed)
            windows = gl.find_windows(idx, counts)
        with open(os.path.join(args.out, "activity.txt"), "w") as fh:
            fh.write(f"# windows: {windows}\n# frame\tink\n")
            for i, c in zip(idx, counts):
                fh.write(f"{i}\t{c}\n")
        print(f"      windows: {windows}", flush=True)

    print("[3/4] reading each window", flush=True)
    result = {"frames": args.frames, "windows": []}
    for n, w in enumerate(windows):
        r = analyse_window(args.frames, bg, w, lib, args.out, f"w{n}",
                           args.lo_pct, args.hi_pct, signed=args.signed)
        result["windows"].append(r)
        print(f"      window {w} orientation={r.get('orientation')}", flush=True)
        for b in r["blocks"]:
            flag = " <-- TRUNCATED" if b["n_cut"] else ""
            print(f"        block{b['index']}: n={b['n']:3d} mean={b['mean_score']:.3f} "
                  f"trusted={b['n_trusted']:3d} cut={b['n_cut']:3d}  "
                  f"{b['trusted_text']}{flag}", flush=True)

    path = os.path.join(args.out, "read.json")
    with open(path, "w") as fh:
        json.dump(result, fh, indent=2, default=_jsonable)
    print(f"[4/4] wrote {path} and debug crops to {args.out}/", flush=True)

    total = sum(b["n_trusted"] for w in result["windows"] for b in w["blocks"])
    cut = sum(b["n_cut"] for w in result["windows"] for b in w["blocks"])
    print(f"\nSUMMARY: {total} characters read with confidence, {cut} components truncated.")
    if cut:
        print("Truncated components are NOT readable: part of the character was never "
              "in these pixels. Correlating them against complete templates produces a "
              "ranking, but not a character.")


if __name__ == "__main__":
    main()
