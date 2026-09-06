#!/usr/bin/env python3
"""
verify_column.py -- machine-checkable verification of part 2's column read.

The column's six characters are read by joining two half-streams (see
decode_real.py).  This script checks that read two independent ways, so the
result does not rest on anyone's eyes:

1. **Against part 1's own glyphs.** Part 1's seam yields ten complete
   characters whose labels are fixed by `6A6B0860B4`, giving in-footage
   templates for 0, 4, 6, 8, A and B at the same scale and face as the column.
   Cells 5 and 6 must come back `0` and `4` with a clear margin; cells 1-4 must
   match *nothing* in that set, because 7, 2, 3 and 5 are not in it.
2. **Against the full 16-digit library** built from Puzzle #1's solution
   screen, on tightly cropped cells and at three normalisation sizes, which
   must agree with each other.

Usage:
    python3 verify_column.py --join join.npy --templates timg.pkl

`--join` is the joined column written by decode_real.py (saved with
`numpy.save`); `--templates` is the pickled 16-digit library.  `--part1` is an
optional .npy of the ten seam-A composites, used for check 1.
"""
import argparse
import pickle

import numpy as np
from PIL import Image

PART1_LABELS = "6A6B0860B4"
CELLS = 6
INK = 40


def tight(a, thr=INK):
    mask = a > thr
    ys, xs = np.nonzero(mask)
    if not len(ys):
        return a
    return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def norm(a, shape):
    im = Image.fromarray(np.asarray(a, dtype=np.float32)).resize((shape[1], shape[0]), Image.LANCZOS)
    v = np.asarray(im, dtype=np.float32).ravel()
    v = v - v.mean()
    n = np.linalg.norm(v)
    return v / n if n else v


def cells(join):
    ink = np.nonzero((join > INK).sum(1))[0]
    top, bottom = int(ink.min()), int(ink.max()) + 1
    pitch = (bottom - top) / CELLS
    return [join[int(top + i * pitch):int(top + (i + 1) * pitch)] for i in range(CELLS)]


def rank(cell, library, shape):
    v = norm(tight(cell), shape)
    scored = sorted(((float(v @ u), k) for k, u in library.items()), reverse=True)
    return scored


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--join", required=True)
    ap.add_argument("--templates", required=True)
    ap.add_argument("--part1")
    args = ap.parse_args()

    join = np.load(args.join)
    cs = cells(join)

    if args.part1:
        comps = np.load(args.part1)
        by_label = {}
        for label, comp in zip(PART1_LABELS, comps):
            g = tight(np.rot90(comp[295:440, 85:225], 3))
            by_label.setdefault(label, []).append(g)
        shape = (48, 34)
        lib = {k: norm(np.mean([np.asarray(Image.fromarray(x).resize((shape[1], shape[0]))) for x in v], 0), shape)
               for k, v in by_label.items()}
        print("[1] against part 1's own glyphs (%s)" % ", ".join(sorted(lib)))
        for i, c in enumerate(cs):
            top = rank(c, lib, shape)[:2]
            print("    cell %d -> %s %.3f (next %s %.3f)" % (i + 1, top[0][1], top[0][0], top[1][1], top[1][0]))

    T = pickle.load(open(args.templates, "rb"))
    print("[2] against the 16-digit library, three normalisations")
    for shape in ((32, 22), (40, 28), (24, 17)):
        lib = {k: norm(tight(np.asarray(v, dtype=np.float32), thr=np.asarray(v).max() * 0.3), shape)
               for k, v in T.items()}
        read = []
        detail = []
        for c in cs:
            top = rank(c, lib, shape)[:2]
            read.append(top[0][1])
            detail.append("%s%.2f/%s%.2f" % (top[0][1], top[0][0], top[1][1], top[1][0]))
        print("    %-8s %s   %s" % (str(shape), "".join(read), " ".join(detail)))


if __name__ == "__main__":
    main()
