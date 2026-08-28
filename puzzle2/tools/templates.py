"""
templates.py -- build a labelled hex glyph library from Puzzle #1's solution screen.

Puzzle #1 published its own answer, and its solution video shows that answer as a
stable 64-character screen. Segmenting that screen and labelling each component
positionally from the published string gives ground-truth letterforms for all 16
hex digits, in the author's own serif face -- which is exactly what Puzzle #2's
glyphs should be matched against.

The labelling is only as good as the segmentation: if the screen segments into
anything other than 64 components, the positional labels are misaligned and the
whole library is garbage. `build` refuses to produce a library in that case
rather than silently mislabelling.
"""
from __future__ import annotations

import json
import os

import numpy as np
from scipy import ndimage

import glyphlib as gl

NORM = 32  # every glyph and template is resampled to NORM x NORM before matching


def normalize_patch(patch, size=NORM):
    """Resample to a fixed square and convert to a zero-mean unit-norm vector, so
    a dot product between two of these IS the normalized cross-correlation.
    Aspect ratio is deliberately NOT preserved: hex glyphs differ in width
    ('1' vs 'D') and stretching each to the same box makes shape, not width,
    carry the decision."""
    if patch.size == 0 or patch.shape[0] < 2 or patch.shape[1] < 2:
        return None
    zoom = (size / patch.shape[0], size / patch.shape[1])
    r = ndimage.zoom(patch.astype(np.float32), zoom, order=1)
    r = r[:size, :size]
    if r.shape != (size, size):
        pad = np.zeros((size, size), np.float32)
        pad[:r.shape[0], :r.shape[1]] = r
        r = pad
    v = (r - r.mean()).ravel()          # flat: a dot product is then the NCC
    n = np.linalg.norm(v)
    return None if n < 1e-6 else v / n


SEGMENT_GRID = [
    {"min_ink": 12, "close": 1, "k": "auto"},
    {"min_ink": 12, "close": 0, "k": "auto"},
    {"min_ink": 12, "close": 2, "k": "auto"},
    {"min_ink": 20, "close": 1, "k": "auto"},
    {"min_ink": 12, "close": 1, "k": 3.5},
    {"min_ink": 12, "close": 1, "k": 5.0},
    {"min_ink": 12, "close": 1, "k": 7.0},
    {"min_ink": 8, "close": 1, "k": 3.5},
    {"min_ink": "auto", "close": 1, "k": "auto"},
]


def build(image_path, answer, out_path=None, lo_pct=50.0, hi_pct=99.9,
          min_ink=12, close=1, strict=True, autotune=True):
    """Segment `image_path` (a still of the solution screen) and label its
    components positionally from `answer`.

    With `autotune`, segmentation parameters are swept until the screen splits
    into exactly as many components as the answer has characters. That is a safe
    thing to tune against precisely because the count is ground truth here: the
    answer is published, so "64 components" is a fact to hit, not a target to
    overfit. Any other count guarantees misaligned labels.
    """
    answer = answer.strip().upper()
    img = gl.load_gray(image_path)
    # A still screen has no temporal background to subtract, so the "background"
    # is the page itself: flatten it with a large-kernel median before stretching.
    bg = ndimage.median_filter(img, size=31)
    res = np.abs(img - bg)
    st = gl.stretch(res, lo_pct, hi_pct)

    def seg(mi, cl, kk):
        # Geometric splitting is used here, unlike the reading path: building
        # the library is the one place with no library to validate a split
        # against. The component-count check is what catches it going wrong.
        return gl.reading_order(
            gl.segment(st, min_ink=mi, close=cl, k=kk, split=True))

    glyphs = seg(min_ink, close, "auto")
    tuned = None
    if autotune and len(glyphs) != len(answer):
        for cfg in SEGMENT_GRID:
            cand = seg(cfg["min_ink"], cfg["close"], cfg["k"])
            if len(cand) == len(answer):
                glyphs, tuned = cand, cfg
                break

    if strict and len(glyphs) != len(answer):
        raise ValueError(
            f"segmented {len(glyphs)} components but the answer has {len(answer)} "
            f"characters -- positional labels would be misaligned. Re-tune "
            f"min_ink/close/percentiles, or pass strict=False to inspect."
        )

    buckets = {}
    for g, ch in zip(glyphs, answer):
        v = normalize_patch(g.patch)
        if v is not None:
            buckets.setdefault(ch, []).append(v)

    lib = {}
    for ch, vs in buckets.items():
        m = np.mean(vs, axis=0)
        n = np.linalg.norm(m)
        if n > 1e-6:
            lib[ch] = (m / n)

    missing = [c for c in gl.HEXDIGITS if c not in lib]
    result = {
        "templates": {c: v.tolist() for c, v in lib.items()},
        "size": NORM,
        "source": os.path.basename(image_path),
        "n_components": len(glyphs),
        "missing_digits": missing,
        "counts": {c: len(v) for c, v in buckets.items()},
        "tuned": tuned,
    }
    result["self_classification"] = _self_check(glyphs, answer, lib)
    if out_path:
        with open(out_path, "w") as fh:
            json.dump(result, fh)
    return result


def _self_check(glyphs, answer, lib):
    """Classify the library's own training glyphs. This is the honesty check
    from tested.md row 4 -- a library that cannot re-read the screen it was
    built from will not read anything else either."""
    if not lib:
        return {"accuracy": 0.0, "correct": 0, "total": 0}
    chars = sorted(lib)
    M = np.stack([lib[c] for c in chars])
    ok = 0
    total = 0
    for g, truth in zip(glyphs, answer):
        v = normalize_patch(g.patch)
        if v is None:
            continue
        total += 1
        if chars[int(np.argmax(M @ v))] == truth:
            ok += 1
    return {"accuracy": ok / max(total, 1), "correct": ok, "total": total}


def load(path):
    with open(path) as fh:
        d = json.load(fh)
    d["templates"] = {c: np.asarray(v, np.float32) for c, v in d["templates"].items()}
    return d
