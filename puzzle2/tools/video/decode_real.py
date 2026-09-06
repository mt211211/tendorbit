#!/usr/bin/env python3
"""
decode_real.py -- reproduce the three real reads from the 720p60 footage.

Three payload carriers exist in the published Puzzle #2 footage, and one
reference carrier in Puzzle #1 that is used to calibrate what a carrier looks
like.  Each is a *split* rendering: the glyph is cut and its two halves are
shown in different places (part 1) or at different times (part 2), so a single
frame never contains a whole character.

  seam A  (part 1, frames 1220-1260)  glyphs cut by the LEFT and RIGHT frame
          edges.  The right-edge stream leads the left-edge stream by exactly
          19 frames.  hstack(right_band(f), left_band(f+19)) rejoins them; the
          result is rotated 90 degrees clockwise.        -> 6A6B0860B4
  seam B  (part 1, frames 1455-1496)  the same ten characters again, this time
          cut by the TOP and BOTTOM edges, same 19-frame lead.
          vstack(bottom_band(f), top_band(f+19)) rejoins them, upright.
                                                          -> 6A6B0860B4
  column  (part 2, frames 1551-1619)  a vertical stack of six characters that
          alternates between two still images, A and C, about every eight
          frames (a third state, the union of the two, appears on the
          crossfade frames).  A carries each glyph's right part, cut at
          x=622; C carries the left part, cut at x=663.  Both cuts fall at the
          same point *within* the glyph, which is why the two cut columns
          agree to a Jaccard of 0.93; hstack(C, A) rejoins them.
                                                          -> 723504

Usage:
    python3 decode_real.py --frames1 f1/ --frames2 f2/ --out out/

`--frames1` and `--frames2` are directories of PNG frames named in sorted
order (f_00001.png ...), 1800 each at 1280x720.
"""
import argparse
import glob
import os

import numpy as np
from PIL import Image

SEAM_OFFSET = 19          # frames the leading edge stream runs ahead by
SEAM_A_STARTS = [1220, 1222, 1225, 1227, 1230, 1232, 1235, 1237, 1240, 1242]
SEAM_B_STARTS = [1455, 1457, 1460, 1462, 1465, 1467, 1470, 1472, 1475, 1477]
COLUMN_A_FRAMES = (1551, 1559)   # state A: right halves, cut at x=622
COLUMN_C_FRAMES = (1566, 1573)   # state C: left halves,  cut at x=663
COLUMN_BLANK = (1541, 1550)      # the same shot with the column absent
COLUMN_CUT_A = (622, 658)
COLUMN_CUT_C = (617, 664)
COLUMN_ROWS = (100, 620)
COLUMN_CELLS = 6


def load(path):
    return np.asarray(Image.open(path).convert("L"), dtype=np.float32)


def frames(folder):
    fs = sorted(glob.glob(os.path.join(folder, "*.png")))
    if not fs:
        raise SystemExit("no PNG frames in %s" % folder)
    return fs


def low_background(fs, step=20, pct=20):
    """A low-percentile background: bright payload never votes itself away."""
    stack = np.stack([load(f) for f in fs[::step]])
    return np.percentile(stack, pct, axis=0)


def residual(fs, bg, index):
    return np.clip(load(fs[index - 1]) - bg, 0, None)


def save_strip(cells, path, pad=6, scale=1):
    strip = np.hstack([np.pad(c, ((0, 0), (pad, pad))) for c in cells])
    lo, hi = np.percentile(strip, 1), np.percentile(strip, 99.5)
    view = np.clip((strip - lo) / (hi - lo + 1e-9), 0, 1)
    im = Image.fromarray((view * 255).astype(np.uint8))
    if scale != 1:
        im = im.resize((im.width * scale, im.height * scale), Image.LANCZOS)
    im.save(path)


def seam_a(fs, bg, out):
    cells = []
    for f in SEAM_A_STARTS:
        right = residual(fs, bg, f)[:, 1120:1280]
        left = residual(fs, bg, f + SEAM_OFFSET)[:, 0:160]
        joined = np.hstack([right, left])
        cells.append(np.rot90(joined[295:440, 85:225], 3))
    save_strip(cells, os.path.join(out, "seamA.png"))
    return cells


def seam_b(fs, bg, out):
    cells = []
    for f in SEAM_B_STARTS:
        top = residual(fs, bg, f)[0:160, :]
        bottom = residual(fs, bg, f + SEAM_OFFSET)[560:720, :]
        joined = np.vstack([bottom, top])
        cells.append(joined[105:230, 570:725])
    save_strip(cells, os.path.join(out, "seamB.png"))
    return cells


def _mean(fs, lo, hi):
    return np.mean([load(f) for f in fs[lo - 1:hi]], axis=0)


def column(fs, out):
    blank = _mean(fs, *COLUMN_BLANK)
    state_a = np.clip(_mean(fs, *COLUMN_A_FRAMES) - blank, 0, None)
    state_c = np.clip(_mean(fs, *COLUMN_C_FRAMES) - blank, 0, None)

    # The two cuts land at the same point within the glyph, so the two cut
    # columns are the same cross-section.  Measure the vertical offset rather
    # than assuming zero, and report the agreement -- a low score here means
    # the join below is not the right one.
    ca = state_a[:, COLUMN_CUT_A[0]] > 40
    cc = state_c[:, COLUMN_CUT_C[1] - 1] > 40
    best = max(
        (((ca & np.roll(cc, s)).sum() / max(1, (ca | np.roll(cc, s)).sum()), s)
         for s in range(-40, 41)),
        key=lambda t: t[0],
    )
    agreement, shift = best

    r0, r1 = COLUMN_ROWS
    right = np.roll(state_a, shift, axis=0)[r0:r1, COLUMN_CUT_A[0]:COLUMN_CUT_A[1]]
    left = state_c[r0:r1, COLUMN_CUT_C[0]:COLUMN_CUT_C[1]]
    joined = np.hstack([left, right])

    ink = np.nonzero((joined > 40).sum(1))[0]
    top, bottom = int(ink.min()), int(ink.max()) + 1
    pitch = (bottom - top) / COLUMN_CELLS
    cells = [joined[int(top + i * pitch):int(top + (i + 1) * pitch)]
             for i in range(COLUMN_CELLS)]
    save_strip(cells, os.path.join(out, "column.png"), scale=4)
    return cells, agreement, shift, pitch


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames1", required=True)
    ap.add_argument("--frames2", required=True)
    ap.add_argument("--out", default="out")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    f1 = frames(args.frames1)
    bg1 = low_background(f1)
    seam_a(f1, bg1, args.out)
    seam_b(f1, bg1, args.out)
    print("part 1: seamA.png and seamB.png written -- ten characters each")

    f2 = frames(args.frames2)
    _, agreement, shift, pitch = column(f2, args.out)
    print("part 2: column.png written -- %d cells, pitch %.1f px" % (COLUMN_CELLS, pitch))
    print("        cut-column agreement %.3f at vertical offset %d px" % (agreement, shift))
    if agreement < 0.8:
        print("        WARNING: the two halves do not meet; do not read this strip")


if __name__ == "__main__":
    main()
