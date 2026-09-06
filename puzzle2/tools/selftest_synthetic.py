#!/usr/bin/env python3
"""
selftest_synthetic.py -- end-to-end proof that the pipeline works.

Plants a known 64-hex key in synthetic footage built to the mechanics described
in tested.md, runs the whole chain (background subtraction -> contrast stretch ->
auto-located boxes -> orientation -> template match -> constraint assembly ->
oracle sweep), and requires the oracle to report MATCH on the planted key.

It also runs the negative case: footage whose glyphs are clipped by the frame
edge must yield NO trusted characters and a refused sweep. A pipeline that
"reads" truncated glyphs is worse than one that reads nothing, because it
produces confident wrong answers.

    python3 selftest_synthetic.py

This validates the CODE. It says nothing about the real videos.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import glyphlib as gl        # noqa: E402
import templates as tpl      # noqa: E402
import match as mt           # noqa: E402
import assemble as asm       # noqa: E402
import synth                 # noqa: E402
from oracle import eth_address, KNOWN_ANSWER  # noqa: E402

# The key the synthetic footage hides. Arbitrary, but a valid secp256k1 scalar.
PLANTED = "6A6B0860B4C83F17A2D95E0417BC6D3820FA5719CE84B60D2F3197A5C6E80B41"


def _read(folder, lib, window=None, bg_mode="median"):
    bg = gl.temporal_background(folder, sample=200, mode=bg_mode)
    if window is None:
        idx, counts = gl.activity_profile(folder, bg, step=2)
        wins = gl.find_windows(idx, counts)
        if not wins:
            return None
        window = (wins[0][0], wins[-1][1])
    proj = gl.max_projection(folder, bg, frames=range(*window))
    st = gl.stretch(proj, 50, 99.9)
    glyphs = gl.segment(st)
    return mt.read_blocks(glyphs, lib, st), st


def main():
    tmp = tempfile.mkdtemp(prefix="p2selftest_")
    failures = []
    try:
        # ---- 1. template library from a known solution screen -------------
        screen = synth.solution_screen(KNOWN_ANSWER, os.path.join(tmp, "screen.png"))
        libinfo = tpl.build(screen, KNOWN_ANSWER, out_path=os.path.join(tmp, "lib.json"))
        lib = {c: np.asarray(v, np.float32) for c, v in libinfo["templates"].items()}
        acc = libinfo["self_classification"]["accuracy"]
        print(f"[1] template library: {libinfo['n_components']} glyphs, "
              f"all 16 digits={not libinfo['missing_digits']}, "
              f"self-classification={acc:.1%}")
        if libinfo["missing_digits"] or acc < 0.90:
            failures.append("template library incomplete or inaccurate")

        # ---- 2. part 1: rotated, revealed through a moving seam -----------
        half1, half2 = PLANTED[:32], PLANTED[32:]
        synth.make_part1(os.path.join(tmp, "f1"), half1, n=300, reveal=(100, 200))
        r1, _ = _read(os.path.join(tmp, "f1"), lib)
        b1 = max(r1["blocks"], key=lambda b: b["mean_score"])
        print(f"[2] part 1 ({r1['orientation']}): {b1['trusted_text']}")
        print(f"    planted             : {half1}")
        # A '?' is the pipeline behaving correctly -- it declined a position it
        # could not support. What must never happen is a CONFIDENT WRONG
        # character, so that is what is checked.
        bad1 = [(i, a, b) for i, (a, b) in enumerate(zip(half1, b1["trusted_text"]))
                if b != "?" and b != a]
        if len(b1["trusted_text"]) != len(half1):
            failures.append(f"part 1 length {len(b1['trusted_text'])} != {len(half1)} "
                            "(a dropped or inserted glyph shifts every later position)")
        if bad1:
            failures.append(f"part 1 confident errors: {bad1}")

        # ---- 3. part 2: mirrored static block, MIRROR hint alongside ------
        synth.make_part2(os.path.join(tmp, "f2"), half2, n=300, block=(100, 190))
        r2, _ = _read(os.path.join(tmp, "f2"), lib)
        b2 = max(r2["blocks"], key=lambda b: b["mean_score"])
        hint = min(r2["blocks"], key=lambda b: b["mean_score"])
        bad2 = [(i, a, b) for i, (a, b) in enumerate(zip(half2, b2["trusted_text"]))
                if b != "?" and b != a]
        if len(b2["trusted_text"]) != len(half2):
            failures.append(f"part 2 length {len(b2['trusted_text'])} != {len(half2)}")
        if bad2:
            failures.append(f"part 2 confident errors: {bad2}")
        print(f"[3] part 2 ({r2['orientation']}): {b2['trusted_text']}")
        print(f"    planted             : {half2}")
        print(f"    hint block rejected : mean={hint['mean_score']:.3f} "
              f"vs payload {b2['mean_score']:.3f}")
        if hint["mean_score"] >= b2["mean_score"]:
            failures.append("the MIRROR hint block was not separated from the payload")

        # ---- 4. assemble under the fragment constraint --------------------
        readings = b1["readings"] + b2["readings"]
        slots = asm.constraints_from_readings(readings, length=64)
        placements = asm.apply_fragment(slots, "6A6B0860B4")
        print(f"[4] fragment 6A6B0860B4 fits at offsets {[p[0] for p in placements]}")
        if not placements:
            failures.append("known fragment is inconsistent with the read")
            slots_final = slots
        else:
            slots_final = placements[0][1]
        p = asm.plan(slots_final)
        print(f"    pinned={p['pinned']}/64 open={p['open']} "
              f"candidates={p['candidates']:.3e} feasible={p['feasible']}")

        # ---- 5. sweep against the planted key's own address ---------------
        target = eth_address(PLANTED)
        print("[5] oracle sweep:")
        res = asm.sweep_ladder(readings, fragment="6A6B0860B4", target=target)
        print(f"    {res['status']} after {res.get('tested_total', res.get('tested', 0))} "
              f"candidate(s)" + (f" on rung '{res['rung']}'" if "rung" in res else ""))
        if res["status"] != "MATCH" or res["candidate"] != PLANTED:
            failures.append(f"sweep did not recover the planted key: {res['status']}")
        else:
            print(f"    recovered: {res['candidate']}")
            print(f"    address  : {target}")

        # ---- 6. negative case: truncated glyphs must NOT be read ----------
        synth.make_part1_truncated(os.path.join(tmp, "fcut"), half1[:12], n=240,
                                   reveal=(150, 190))
        rc, _ = _read(os.path.join(tmp, "fcut"), lib, window=(148, 195))
        bc = rc["blocks"][0]
        print(f"[6] truncated clip: trusted={bc['n_trusted']} cut={bc['n_cut']} "
              f"mean={bc['mean_score']:.3f} -> {bc['trusted_text']}")
        if bc["n_trusted"] != 0 or bc["n_cut"] == 0:
            failures.append("truncated glyphs were not rejected")
        slots_cut = asm.constraints_from_readings(bc["readings"], length=64)
        rcut = asm.sweep(slots_cut, target=target)
        print(f"    sweep on truncated read: {rcut['status']}")
        if rcut["status"] != "REFUSED":
            failures.append("an infeasible sweep was not refused")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if failures:
        print("SELFTEST FAILED")
        for f in failures:
            print("  -", f)
        return 1
    print("SELFTEST OK -- pipeline recovers a planted key end to end, "
          "and refuses to read truncated glyphs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
