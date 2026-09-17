"""
glyphlib.py -- core imaging for the Crypto Puzzles 2018 Puzzle #2 read.

Design rules this module enforces, in order of importance:

1. NEVER hard-threshold the payload. The glyphs are faint gray serif strokes a
   few levels above a busy background. A fixed cutoff destroys the anti-aliased
   stroke edges that template correlation depends on. Everything downstream
   consumes a contrast-stretched GRAYSCALE residual. A binary mask is derived
   only to find *where* things are (segmentation); it is never what gets matched.

2. Background is removed temporally, not spatially. The background is whatever
   is stable across the clip (per-pixel median); the payload is what deviates.

3. Truncation is measured, never assumed away. A glyph clipped by a frame edge
   or a window edge cannot be matched against a complete template, and the
   correlation it produces is a fiction. `edge_report` measures it explicitly.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

import numpy as np
from PIL import Image
from scipy import ndimage

HEXDIGITS = "0123456789ABCDEF"


# ---------------------------------------------------------------- frame I/O

def frame_paths(folder):
    """Every PNG in `folder`, ordered by the natural number in the filename."""
    names = [n for n in os.listdir(folder) if n.lower().endswith(".png")]

    def key(name):
        digits = re.findall(r"\d+", name)
        return (int(digits[-1]) if digits else 0, name)

    return [os.path.join(folder, n) for n in sorted(names, key=key)]


def load_gray(path):
    """One frame as float32 luminance in [0, 255]."""
    return np.asarray(Image.open(path).convert("L"), dtype=np.float32)


def load_stack(folder, start=0, stop=None, step=1):
    """A (frames, H, W) float32 stack. Kept in RAM: 1800x720x1280 f32 is ~6.6 GB,
    so callers reading a whole clip should pass a `step` or a frame window."""
    paths = frame_paths(folder)[start:stop:step]
    if not paths:
        raise FileNotFoundError(f"no PNG frames under {folder!r}")
    first = load_gray(paths[0])
    stack = np.empty((len(paths), *first.shape), dtype=np.float32)
    stack[0] = first
    for i, p in enumerate(paths[1:], 1):
        stack[i] = load_gray(p)
    return stack


# -------------------------------------------------- background + stretching

def temporal_background(folder, sample=240, mode="median", pct=20.0):
    """Per-pixel background from `sample` frames spread across the whole clip.

    `mode="median"` outvotes anything transient and is right when the payload
    appears in a minority of frames.

    `mode="percentile"` (a low percentile, default 20th) is the escape hatch for
    a payload HELD across a large fraction of the clip -- part 2's static block
    is on screen for a fifth of its video, and a block held for half of it would
    be voted INTO a median background and then subtracted away to nothing. Since
    the glyphs are brighter than what they sit on, a low percentile still tracks
    the background even when the payload is present most of the time.
    """
    paths = frame_paths(folder)
    if not paths:
        raise FileNotFoundError(f"no PNG frames under {folder!r}")
    idx = np.unique(np.linspace(0, len(paths) - 1, min(sample, len(paths))).astype(int))
    stack = np.stack([load_gray(paths[i]) for i in idx])
    if mode == "percentile":
        return np.percentile(stack, pct, axis=0)
    if mode == "mean":
        return stack.mean(axis=0)
    return np.median(stack, axis=0)


def residual(frame, background, signed=False):
    """Frame minus background. Default keeps only positive deviation (ink that is
    BRIGHTER than background). `signed=True` keeps absolute deviation, for clips
    where the glyphs are darker than what sits behind them."""
    diff = frame - background
    return np.abs(diff) if signed else np.clip(diff, 0, None)


def stretch(img, lo_pct=50.0, hi_pct=99.9, out_max=255.0):
    """Percentile contrast stretch. NOT a threshold: the output is continuous and
    every intermediate gray level survives, which is exactly what the faint
    anti-aliased serif strokes need. Values below `lo_pct` clamp to 0 only
    because they are, by construction, background."""
    lo = np.percentile(img, lo_pct)
    hi = np.percentile(img, hi_pct)
    if hi - lo < 1e-6:
        return np.zeros_like(img)
    return np.clip((img - lo) / (hi - lo), 0, 1) * out_max


def normalized_residual(frame, background, signed=False):
    """Residual expressed in units of the frame's own noise sigma.

    The scale MUST be estimated from the signed difference, before any clipping.
    Clipping negatives to zero leaves a half-normal whose MAD is a small
    fraction of the true sigma, so a z-score computed after the clip is inflated
    several-fold and ordinary noise sails past any sensible cutoff -- which
    makes every frame look like it contains a payload.
    """
    d = frame - background
    med = float(np.median(d))
    mad = float(np.median(np.abs(d - med)))
    scale = 1.4826 * mad if mad > 1e-6 else float(d.std() or 1.0)
    z = (d - med) / scale
    return np.abs(z) if signed else np.clip(z, 0, None)


def max_projection(folder, background, frames=None, signed=False, normalize=True):
    """Temporal maximum of the residual. This is the technique row 1/row 3 of
    tested.md certified against Puzzle #1: a glyph visible in ANY frame of the
    window survives into the projection at its strongest.

    With `normalize`, each frame's residual is put in noise-floor units first
    (see `normalized_residual`), which keeps a faint glyph above the projected
    noise instead of level with it."""
    paths = frame_paths(folder)
    sel = range(len(paths)) if frames is None else frames
    acc = None
    for i in sel:
        f = load_gray(paths[i])
        r = (normalized_residual(f, background, signed=signed) if normalize
             else residual(f, background, signed=signed))
        acc = r if acc is None else np.maximum(acc, r)
    return acc


# ------------------------------------------------------------- segmentation

@dataclass
class Glyph:
    """One candidate character. `patch` is contrast-stretched grayscale."""
    box: tuple            # (y0, y1, x0, x1) half-open
    patch: np.ndarray
    mask: np.ndarray
    ink: int
    touches: tuple = ()   # which frame/window edges this component runs into
    meta: dict = field(default_factory=dict)

    @property
    def height(self):
        return self.box[1] - self.box[0]

    @property
    def width(self):
        return self.box[3] - self.box[2]


def soft_mask(stretched, k=3.5, bg_pct=95.0):
    """Locate ink WITHOUT committing to a threshold on the payload itself.

    The cutoff adapts to each image's own noise floor instead of being a magic
    constant, and it decides only which pixels belong to which component -- the
    grayscale values matched later are never quantised by this step.

    The floor is estimated from the BACKGROUND POPULATION (pixels below
    `bg_pct`), not the whole image, for two reasons: bright ink otherwise
    inflates the spread and hides itself, and a stretch that clamps everything
    below its low percentile to zero drives a whole-image MAD to zero, which
    would pass every pixel in the frame as ink.
    """
    finite = stretched[np.isfinite(stretched)]
    if finite.size == 0:
        return np.zeros_like(stretched, dtype=bool)
    bgpop = finite[finite <= np.percentile(finite, bg_pct)]
    if bgpop.size == 0:
        bgpop = finite
    med = float(np.median(bgpop))
    scale = 1.4826 * float(np.median(np.abs(bgpop - med)))
    if scale < 1e-3:
        scale = float(bgpop.std())
    if scale < 1e-3:
        # Degenerate: the stretch hard-clamped the background flat. Fall back to
        # a fraction of the dynamic range rather than declaring the frame ink.
        return stretched > float(finite.max()) * 0.25
    return stretched > med + k * scale


def auto_min_ink(sizes, floor=20):
    """Pick the ink cutoff separating noise specks from real glyphs.

    Component sizes in a background-subtracted projection are strongly bimodal:
    noise survives as a few pixels, a character as a few hundred. Rather than
    hard-code a constant that is wrong for the next clip, find the widest gap in
    the log-size distribution and cut there. Falls back to `floor` when the
    distribution has no clear gap (which itself is a signal that the window is
    wrong).
    """
    sizes = np.sort(np.asarray([s for s in sizes if s > 0], dtype=float))
    if sizes.size < 4:
        return floor
    logs = np.log10(sizes)
    gaps = np.diff(logs)
    i = int(np.argmax(gaps))
    if gaps[i] < 0.5:            # less than a half-decade jump: no real split
        return floor
    return max(floor, float(10 ** ((logs[i] + logs[i + 1]) / 2)))


K_SWEEP = (4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 12.0, 14.0)


def auto_k(stretched, close=1, sweep=K_SWEEP):
    """Choose the mask sensitivity that most cleanly splits noise from glyphs.

    There is no universally right value: too low and the noise population runs
    continuously into the glyph population, too high and strokes erode. The
    right one is the value whose component-size distribution shows the widest
    log-scale gap -- i.e. where "specks" and "characters" are two populations
    rather than one. Returns (k, gap, min_ink).
    """
    best = (sweep[0], -1.0, 20.0)
    for k in sweep:
        mask = soft_mask(stretched, k=k)
        if close:
            mask = ndimage.binary_closing(mask, np.ones((close * 2 + 1,) * 2))
        lab, n = ndimage.label(mask)
        if n < 4:
            continue
        sizes = np.sort(np.asarray(ndimage.sum(mask, lab, range(1, n + 1)), float))
        sizes = sizes[sizes > 0]
        if sizes.size < 4:
            continue
        logs = np.log10(sizes)
        gaps = np.diff(logs)
        i = int(np.argmax(gaps))
        gap = float(gaps[i])
        # require the split to leave a plausible number of characters above it
        n_above = int((sizes > 10 ** ((logs[i] + logs[i + 1]) / 2)).sum())
        if gap > best[1] and 1 <= n_above <= 200:
            best = (k, gap, max(20.0, float(10 ** ((logs[i] + logs[i + 1]) / 2))))
    return best


def segment(stretched, min_ink="auto", min_h=4, min_w=3, close=1, k="auto",
            split=False, edge_tol=2):
    """Connected components of the soft mask -> Glyph objects carrying the
    grayscale patch. `close` dilates before labelling so that the disconnected
    pieces of a serif letterform (a dotted stem, a thin hairline) join up."""
    auto_ink = None
    if k == "auto":
        k, _gap, auto_ink = auto_k(stretched, close=close)
    mask = soft_mask(stretched, k=k)
    if close:
        mask = ndimage.binary_closing(mask, np.ones((close * 2 + 1,) * 2))
    lab, n = ndimage.label(mask)
    H, W = stretched.shape
    if min_ink == "auto":
        if auto_ink is not None:
            min_ink = auto_ink
        else:
            sizes = ndimage.sum(mask, lab, range(1, n + 1)) if n else []
            min_ink = auto_min_ink(sizes)
    glyphs = []
    for sl in ndimage.find_objects(lab):
        if sl is None:
            continue
        ys, xs = sl
        sub = lab[sl]
        comp = sub == (lab[sl][sub > 0][0] if (sub > 0).any() else 0)
        comp = sub > 0
        ink = int(comp.sum())
        h, w = ys.stop - ys.start, xs.stop - xs.start
        if ink < min_ink or h < min_h or w < min_w:
            continue
        # A tolerance, not an exact boundary test. The outermost column of a
        # glyph sliced by the frame edge is anti-aliased and often falls below
        # the ink mask, so a component genuinely cut at x=W-1 can end at W-2.
        # Requiring exact contact silently reclassifies truncated glyphs as
        # complete -- the one failure this pipeline must never make.
        touches = tuple(
            name for name, hit in (
                ("top", ys.start <= edge_tol), ("bottom", ys.stop >= H - edge_tol),
                ("left", xs.start <= edge_tol), ("right", xs.stop >= W - edge_tol),
            ) if hit
        )
        glyphs.append(Glyph(
            box=(ys.start, ys.stop, xs.start, xs.stop),
            patch=stretched[sl] * comp,
            mask=comp,
            ink=ink,
            touches=touches,
        ))
    # Splitting is deliberately NOT done here: deciding whether a component
    # is two touching characters needs the template library, so it happens in
    # match.refine_splits where a proposed split can be checked against what
    # it actually classifies as.
    return split_merged(glyphs) if split else glyphs


def reading_order(glyphs, row_tol=0.6):
    """Sort into human reading order: group into rows by vertical overlap, then
    left-to-right within a row."""
    if not glyphs:
        return []
    heights = np.array([g.height for g in glyphs])
    tol = max(3.0, float(np.median(heights)) * row_tol)
    rows, remaining = [], sorted(glyphs, key=lambda g: g.box[0])
    for g in remaining:
        centre = (g.box[0] + g.box[1]) / 2
        for row in rows:
            if abs(centre - row[0]) <= tol:
                row[1].append(g)
                break
        else:
            rows.append((centre, [g]))
    out = []
    for _, row in sorted(rows, key=lambda r: r[0]):
        out.extend(sorted(row, key=lambda g: g.box[2]))
    return out


# --------------------------------------------------------- truncation check

def edge_report(glyph, stretched, boundary=None):
    """Is this glyph cut off, or does it end in a real stroke terminal?

    This reproduces tested.md row 8's measurement. A complete serif character
    tapers at its extremes: the outermost columns carry markedly less ink than
    the character's interior. A character sliced by a boundary carries
    full-strength ink right up to the cut. `ratio` near or above 1.0 means CUT.
    """
    m = glyph.mask
    cols = m.sum(axis=0)
    rows = m.sum(axis=1)
    interior_c = cols[1:-1].max() if len(cols) > 2 else cols.max()
    interior_r = rows[1:-1].max() if len(rows) > 2 else rows.max()
    out = {
        "touches": glyph.touches,
        "left_ratio": float(cols[0] / max(interior_c, 1)),
        "right_ratio": float(cols[-1] / max(interior_c, 1)),
        "top_ratio": float(rows[0] / max(interior_r, 1)),
        "bottom_ratio": float(rows[-1] / max(interior_r, 1)),
    }
    out["cut"] = bool(
        glyph.touches and max(
            out["left_ratio"], out["right_ratio"],
            out["top_ratio"], out["bottom_ratio"],
        ) >= 0.8
    )
    if boundary is not None:
        out["boundary_x"] = boundary
    return out


# ------------------------------------------------------------- orientations

def orient(patch, rot=0, mirror=False):
    """One of the 8 dihedral views. `rot` is counter-clockwise degrees."""
    p = np.fliplr(patch) if mirror else patch
    return np.rot90(p, k=(rot // 90) % 4)


ORIENTATIONS = [(r, m) for m in (False, True) for r in (0, 90, 180, 270)]


def orientation_name(rot, mirror):
    return f"rot{rot}{'-mirror' if mirror else ''}"


# ------------------------------------------- geometry under a global transform

def transform_point(y, x, H, W, rot=0, mirror=False):
    """Map a pixel coordinate through the same transform `orient` applies to a
    patch, so glyph POSITIONS can be sorted in the corrected frame.

    Reading order has to be computed after the transform, not before: a block
    rotated 90 degrees reads bottom-to-top in raw frame coordinates, and sorting
    the raw boxes silently reverses the string.
    """
    if mirror:
        x = W - 1 - x
    for _ in range((rot // 90) % 4):          # each np.rot90 is one CCW quarter
        y, x, H, W = W - 1 - x, y, W, H
    return y, x, H, W


def reading_order_oriented(glyphs, shape, rot=0, mirror=False, row_tol=0.6):
    """Reading order in the corrected frame."""
    if not glyphs:
        return []
    H, W = shape
    keyed = []
    for g in glyphs:
        cy = (g.box[0] + g.box[1]) / 2.0
        cx = (g.box[2] + g.box[3]) / 2.0
        ty, tx, _, _ = transform_point(cy, cx, H, W, rot, mirror)
        keyed.append((ty, tx, g))
    spans = [max(g.height, g.width) for g in glyphs]
    tol = max(3.0, float(np.median(spans)) * row_tol)
    rows = []
    for ty, tx, g in sorted(keyed, key=lambda t: t[0]):
        for row in rows:
            if abs(ty - row[0]) <= tol:
                row[1].append((tx, g))
                break
        else:
            rows.append((ty, [(tx, g)]))
    out = []
    for _, row in sorted(rows, key=lambda r: r[0]):
        out.extend(g for _, g in sorted(row, key=lambda t: t[0]))
    return out


# ------------------------------------------------------ merged-glyph splitting

def _split_axis(mask, patch, k, axis):
    """Cut a component into k pieces at the k-1 deepest minima of its ink
    profile along `axis`, keeping cuts away from the piece edges."""
    prof = mask.sum(axis=0 if axis == 1 else 1).astype(float)
    n = prof.size
    if k < 2 or n < 2 * k:
        return None
    step = n / k
    cuts = []
    for i in range(1, k):
        centre = i * step
        lo = int(max(1, centre - step * 0.35))
        hi = int(min(n - 1, centre + step * 0.35))
        if hi <= lo:
            return None
        cuts.append(lo + int(np.argmin(prof[lo:hi])))
    bounds = [0] + sorted(set(cuts)) + [n]
    if len(bounds) != k + 1:
        return None
    return [(bounds[i], bounds[i + 1]) for i in range(k)]


def _valley_depth(mask, axis):
    """How deep the deepest interior dip in the ink profile is, relative to the
    profile's typical level. Two touching characters leave a real notch; one
    naturally wide character does not."""
    prof = mask.sum(axis=0 if axis == 1 else 1).astype(float)
    n = prof.size
    if n < 7:
        return 1.0
    inner = prof[int(n * 0.25):int(n * 0.75)]
    if inner.size == 0:
        return 1.0
    return float(inner.min() / max(np.median(prof), 1.0))


def split_candidates(g, mw, mh, max_ratio=1.35, max_valley=0.60):
    """The pieces `g` would break into, or None if it does not look merged.

    Geometry alone cannot settle this: hex glyphs differ in extent by nearly 2x
    ('1' vs 'D'), and at small sizes a patchy mask puts a false notch inside a
    perfectly good 'A'. This returns a PROPOSAL; `match.refine_splits` accepts it
    only if classifying the pieces actually beats classifying the whole.
    """
    kx = int(round(g.width / mw)) if mw > 0 else 1
    ky = int(round(g.height / mh)) if mh > 0 else 1
    axis, k = (1, kx) if (g.width / max(mw, 1) >= g.height / max(mh, 1)) else (0, ky)
    ratio = (g.width / mw) if axis == 1 else (g.height / mh)
    if k < 2 or ratio < max_ratio or _valley_depth(g.mask, axis) > max_valley:
        return None
    pieces = _split_axis(g.mask, g.patch, k, axis)
    if not pieces:
        return None
    y0, y1, x0, x1 = g.box
    out = []
    for a, b in pieces:
        if axis == 1:
            sub_m, sub_p = g.mask[:, a:b], g.patch[:, a:b]
            oy, ox = y0, x0 + a
        else:
            sub_m, sub_p = g.mask[a:b, :], g.patch[a:b, :]
            oy, ox = y0 + a, x0
        if sub_m.sum() < 8:
            return None
        ys, xs = np.nonzero(sub_m)
        yy0, yy1 = ys.min(), ys.max() + 1
        xx0, xx1 = xs.min(), xs.max() + 1
        out.append(Glyph(
            box=(oy + yy0, oy + yy1, ox + xx0, ox + xx1),
            patch=sub_p[yy0:yy1, xx0:xx1],
            mask=sub_m[yy0:yy1, xx0:xx1],
            ink=int(sub_m[yy0:yy1, xx0:xx1].sum()),
            touches=g.touches,
            meta={"split_from": g.box},
        ))
    return out


def median_extents(glyphs):
    if not glyphs:
        return 1.0, 1.0
    return (float(np.median([g.width for g in glyphs])),
            float(np.median([g.height for g in glyphs])))


def split_merged(glyphs, max_ratio=1.35, max_valley=0.60):
    """Split components that are a whole multiple wider (or taller) than typical.

    Tightly-set serif text merges adjacent characters wherever their ink
    actually touches, and no threshold separates them because there is no gap to
    find. The give-away is geometric: one component two characters wide. Left
    unsplit it classifies as a single wrong character and silently shortens the
    string, which is worse than an obvious failure.
    """
    if len(glyphs) < 3:
        return glyphs
    widths = np.array([g.width for g in glyphs], float)
    heights = np.array([g.height for g in glyphs], float)
    mw, mh = float(np.median(widths)), float(np.median(heights))
    out = []
    for g in glyphs:
        kx = int(round(g.width / mw)) if mw > 0 else 1
        ky = int(round(g.height / mh)) if mh > 0 else 1
        axis, k = (1, kx) if (g.width / max(mw, 1) >= g.height / max(mh, 1)) else (0, ky)
        ratio = (g.width / mw) if axis == 1 else (g.height / mh)
        # Two independent conditions must both hold. Size alone is not enough:
        # hex glyphs legitimately differ in extent by nearly 2x ('1' vs 'D'), so
        # splitting on width would carve real characters in half. The notch is
        # what distinguishes a merged pair from a wide character.
        if k < 2 or ratio < max_ratio or _valley_depth(g.mask, axis) > max_valley:
            out.append(g)
            continue
        pieces = _split_axis(g.mask, g.patch, k, axis)
        if not pieces:
            out.append(g)
            continue
        y0, y1, x0, x1 = g.box
        for a, b in pieces:
            if axis == 1:
                sub_m, sub_p = g.mask[:, a:b], g.patch[:, a:b]
                box = (y0, y1, x0 + a, x0 + b)
            else:
                sub_m, sub_p = g.mask[a:b, :], g.patch[a:b, :]
                box = (y0 + a, y0 + b, x0, x1)
            if sub_m.sum() < 8:
                continue
            ys, xs = np.nonzero(sub_m)          # tighten to the piece's own ink
            yy0, yy1 = ys.min(), ys.max() + 1
            xx0, xx1 = xs.min(), xs.max() + 1
            out.append(Glyph(
                box=(box[0] + yy0, box[0] + yy1, box[2] + xx0, box[2] + xx1),
                patch=sub_p[yy0:yy1, xx0:xx1],
                mask=sub_m[yy0:yy1, xx0:xx1],
                ink=int(sub_m[yy0:yy1, xx0:xx1].sum()),
                touches=g.touches,
                meta={"split_from": g.box},
            ))
    return out


# ------------------------------------------------------- payload window search

def activity_profile(folder, background, k=6.0, step=1, signed=False):
    """Per-frame count of pixels standing clearly above the noise floor.

    This is how the payload windows are located rather than guessed (tested.md
    row 5): frames carrying glyphs show a step change in ink, and the windows
    fall out as contiguous runs above the clip's own baseline.
    """
    paths = frame_paths(folder)
    idx = list(range(0, len(paths), step))
    counts = []
    for i in idx:
        z = normalized_residual(load_gray(paths[i]), background, signed=signed)
        counts.append(int((z > k).sum()))
    return np.asarray(idx), np.asarray(counts)


def find_windows(idx, counts, min_len=3, pad=2, factor=2.0, merge_gap=12):
    """Contiguous frame runs whose activity exceeds `factor` x the clip median.

    Runs separated by less than `merge_gap` frames are merged: a statically held
    block sits near the threshold and dips below it whenever the scene's own
    lighting breathes, which would otherwise shatter one window into several and
    make a single held block look like an animation.
    """
    if counts.size == 0:
        return []
    # Threshold from the spread of the counts, not a fixed multiple of their
    # median. A faint payload revealed a sliver at a time lifts the ink count
    # well clear of the noise band while never reaching 2x the baseline, and a
    # fixed factor misses it entirely.
    base = float(np.median(counts))
    mad = float(np.median(np.abs(counts - base)))
    spread = 1.4826 * mad if mad > 0 else float(counts.std() or 1.0)
    thresh = min(base * factor, base + 4.0 * spread)
    thresh = max(thresh, base + 5.0)
    hot = counts > thresh
    runs, start = [], None
    for i, h in enumerate(hot):
        if h and start is None:
            start = i
        elif not h and start is not None:
            runs.append((start, i))
            start = None
    if start is not None:
        runs.append((start, len(hot)))
    spans = []
    for a, b in runs:
        if b - a < min_len:
            continue
        spans.append([max(0, int(idx[a]) - pad), int(idx[min(b, len(idx) - 1)]) + pad])
    merged = []
    for sp in spans:
        if merged and sp[0] - merged[-1][1] <= merge_gap:
            merged[-1][1] = sp[1]
        else:
            merged.append(sp)
    return [tuple(m) for m in merged]
