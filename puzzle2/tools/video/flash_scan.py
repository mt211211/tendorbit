#!/usr/bin/env python3
"""
flash_scan.py -- find single-frame flashes, the carrier that defeats averaging.

Puzzle #1 hides part of its key in frames that are on screen for **one frame at
60fps**. Frame 1181 of statement A jumps a region from 53 to 241 and back; frame
1054 of statement B does the same for a 6x5 grid. Temporal medians, means, max
projections and background subtraction all destroy or bury such a frame, which
is why a whole pass over these videos can miss it.

The detector: a frame's *novelty* is how far it departs from the average of its
two neighbours, measured only over pixels that are not routinely bright (so
ordinary animation does not drown the signal), and scored by how many
**glyph-shaped** components that novelty contains.

Calibration on Puzzle #1, which is ground truth:

    statement A   frame 1181   18 glyph components, amplitude 182
    statement B   frame 1054   21 glyph components, amplitude 200
    statement B   frame 1040    9 glyph components, amplitude 199
    statement B   frame 1025             amplitude 190

Statement A's flash, rotated and read bottom-up, gives `482BE6FB9C2...` --
positions 37-47 of the published answer, the span its static line omits.

Usage:
    python3 flash_scan.py --frames f1/ [--min-glyphs 3] [--dump out/]
"""
import argparse
import glob
import os

import numpy as np
from PIL import Image
from scipy.ndimage import label, find_objects

BRIGHT = 110          # a pixel routinely above this is "normally active"
ROUTINE = 2           # ... in more than this many sampled frames
AMPLITUDE = 8.0       # a flash pixel must exceed its neighbours by this much


def load(p):
    return np.asarray(Image.open(p).convert("L"), dtype=np.float32)


def quiet_mask(files, step=6):
    stack = np.stack([load(f) for f in files[::step]])
    return ~((stack > BRIGHT).sum(0) > ROUTINE)


def glyph_components(novelty):
    lb, _ = label(novelty > AMPLITUDE)
    n = 0
    for i, sl in enumerate(find_objects(lb)):
        h = sl[0].stop - sl[0].start
        w = sl[1].stop - sl[1].start
        if 12 <= h <= 70 and 6 <= w <= 70 and (lb[sl] == i + 1).sum() >= 50:
            n += 1
    return n


def scan(folder, min_glyphs, dump=None):
    files = sorted(glob.glob(os.path.join(folder, "*.png")))
    if not files:
        raise SystemExit("no PNG frames in %s" % folder)
    mask = quiet_mask(files)
    print("frames %d, quiet mask covers %.1f%% of the frame" % (len(files), 100 * mask.mean()))
    hits = []
    prev2 = prev = None
    for i, f in enumerate(files):
        cur = load(f)
        if prev2 is not None:
            novelty = (prev - (prev2 + cur) / 2) * mask
            n = glyph_components(novelty)
            if n >= min_glyphs:
                hits.append((i, n, float(novelty.max())))
                if dump:
                    lo, hi = np.percentile(novelty, 1), np.percentile(novelty, 99.8)
                    v = np.clip((novelty - lo) / (hi - lo + 1e-9), 0, 1)
                    Image.fromarray((v * 255).astype(np.uint8)).save(
                        os.path.join(dump, "flash_%05d.png" % i))
        prev2, prev = prev, cur
    hits.sort(key=lambda h: -h[1])
    if not hits:
        print("no single-frame flash found")
    for i, n, amp in hits[:20]:
        print("  frame %5d  %3d glyph components  amplitude %.1f" % (i, n, amp))
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", required=True)
    ap.add_argument("--min-glyphs", type=int, default=3)
    ap.add_argument("--dump")
    args = ap.parse_args()
    if args.dump:
        os.makedirs(args.dump, exist_ok=True)
    scan(args.frames, args.min_glyphs, args.dump)


if __name__ == "__main__":
    main()
