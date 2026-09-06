"""
synth.py -- generate synthetic puzzle footage with a KNOWN answer.

The real frames are not in this checkout, so the pipeline is validated against
footage this module fabricates to match the mechanics tested.md describes:
faint serif glyphs a few levels above a busy moving background, revealed through
a travelling seam window (part 1, rotated) and a mirrored static block (part 2).

This proves the CODE works. It proves nothing about the real videos.
"""
from __future__ import annotations

import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

SERIF = "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"
W, H = 1280, 720


def _font(size):
    return ImageFont.truetype(SERIF, size)


def solution_screen(answer, path, size=44, contrast=70, bg=30, cols=23):
    """A Puzzle-#1-style 'THE SOLUTION' screen: the answer across 3 lines,
    rendered at low contrast, which is what the template library is built from."""
    im = Image.new("L", (W, H), bg)
    d = ImageDraw.Draw(im)
    f = _font(size)
    lines = [answer[i:i + cols] for i in range(0, len(answer), cols)]
    y = 200
    for line in lines:
        x = 120
        for ch in line:
            d.text((x, y), ch, font=f, fill=bg + contrast)
            x += 46
        y += 90
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    im.save(path)
    return path


def _busy_background(n, seed=0):
    """A moving background that is bright, structured and noisy -- so that a
    naive fixed threshold fails and the temporal median is what saves the read."""
    rng = np.random.default_rng(seed)
    base = rng.integers(40, 90, size=(H, W)).astype(np.float32)
    base = np.clip(base + 30 * np.sin(np.linspace(0, 12, W))[None, :], 0, 255)
    # Modest global drift only. The point the synthetic must preserve is that
    # the background LEVELS (40-120) dwarf the glyph increment (~14), so no
    # threshold on raw pixels can isolate the payload -- you have to subtract
    # the background first. Heavy per-frame drift would instead test a
    # different thing (temporal filtering) that real footage does not exhibit.
    out = []
    for i in range(n):
        f = base + 1.5 * np.sin(np.linspace(0, 8, H) + i * 0.25)[:, None]
        out.append(np.clip(f + rng.normal(0, 2.0, (H, W)), 0, 255).astype(np.float32))
    return out


def _fit_layer(text, size, rot, mirror, max_h, max_w, spacing=None):
    """Render `text`, shrinking the face until the transformed block fits the
    frame. A 32-character line rotated 90 degrees is taller than 720px at any
    readable size, so the layout has to adapt rather than overflow."""
    for _ in range(24):
        layer = _render_text_layer(text, size, rot=rot, mirror=mirror, spacing=spacing)
        if layer.shape[0] <= max_h and layer.shape[1] <= max_w:
            return layer, size
        size = int(size * 0.9)
        if size < 8:
            break
    return layer, size


def _render_text_layer(text, size, rot=0, mirror=False, spacing=None):
    """A tight float32 layer holding `text`, transformed as requested."""
    f = _font(size)
    pad = size
    tmp = Image.new("L", (len(text) * size + 2 * pad, size * 2 + 2 * pad), 0)
    d = ImageDraw.Draw(tmp)
    x = pad
    step = spacing or int(size * 0.72)
    for ch in text:
        d.text((x, pad), ch, font=f, fill=255)
        x += step
    a = np.asarray(tmp, np.float32)
    ys, xs = np.nonzero(a)
    a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    if mirror:
        a = np.fliplr(a)
    return np.rot90(a, k=(rot // 90) % 4)


def make_part1(folder, payload, n=200, reveal=(60, 140), amp=14, rot=90,
               seed=1, glyph_size=40):
    """Part 1: glyphs sit at a fixed spot but are only lit inside a travelling
    seam window, so no single frame shows them all -- max-projection does."""
    os.makedirs(folder, exist_ok=True)
    frames = _busy_background(n, seed)
    oy, ox = 60, 300
    layer, _ = _fit_layer(payload, glyph_size, rot, False, H - oy - 20, W - ox - 20)
    lh, lw = layer.shape
    lo, hi = reveal
    for i, fr in enumerate(frames):
        if lo <= i < hi:
            # a vertical seam sweeping left to right across the text block
            frac = (i - lo) / max(hi - lo - 1, 1)
            cx = int(frac * lw)
            win = np.zeros((lh, lw), np.float32)
            win[:, max(0, cx - 14):cx + 14] = 1.0
            fr = fr.copy()
            fr[oy:oy + lh, ox:ox + lw] += amp * (layer / 255.0) * win
        Image.fromarray(np.clip(fr, 0, 255).astype(np.uint8)).save(
            os.path.join(folder, f"frame_{i:05d}.png"))
    return {"folder": folder, "payload": payload, "rot": rot,
            "origin": (oy, ox), "reveal": reveal}


def make_part2(folder, payload, n=200, block=(60, 160), amp=15, seed=2,
               glyph_size=40, decoy="MIRROR"):
    """Part 2: a static block rendered MIRRORED, held over a range of frames,
    with the word MIRROR alongside it as the video's own instruction."""
    os.makedirs(folder, exist_ok=True)
    frames = _busy_background(n, seed)
    oy, ox = 150, 60
    layer, used = _fit_layer(payload, glyph_size, 0, True, 200, W - ox - 20)
    hint = _render_text_layer(decoy, used)
    lh, lw = layer.shape
    hh, hw = hint.shape
    lo, hi = block
    for i, fr in enumerate(frames):
        if lo <= i < hi:
            fr = fr.copy()
            fr[oy:oy + lh, ox:ox + lw] += amp * (layer / 255.0)
            hy = oy + lh + 120
            fr[hy:hy + hh, ox:ox + hw] += amp * (hint / 255.0)
        Image.fromarray(np.clip(fr, 0, 255).astype(np.uint8)).save(
            os.path.join(folder, f"frame_{i:05d}.png"))
    return {"folder": folder, "payload": payload, "mirror": True,
            "origin": (oy, ox), "block": block}


def make_part1_truncated(folder, payload, n=120, reveal=(40, 100), amp=14,
                         rot=90, seed=3, glyph_size=40):
    """The failure mode tested.md rows 8 and 12 report: glyphs running off the
    right frame edge, so a real slice of every character was never published.
    The pipeline must DETECT this rather than produce a confident wrong read."""
    os.makedirs(folder, exist_ok=True)
    frames = _busy_background(n, seed)
    oy = 60
    layer, _ = _fit_layer(payload, glyph_size, rot, False, H - oy - 20, W)
    lh, lw = layer.shape
    ox = W - lw // 2          # half the block hangs off the right edge
    lo, hi = reveal
    for i, fr in enumerate(frames):
        if lo <= i < hi:
            frac = (i - lo) / max(hi - lo - 1, 1)
            cx = int(frac * lh)
            win = np.zeros((lh, lw), np.float32)
            win[max(0, cx - 16):cx + 16, :] = 1.0
            vis_w = min(lw, W - ox)
            fr = fr.copy()
            fr[oy:oy + lh, ox:ox + vis_w] += amp * (layer[:, :vis_w] / 255.0) * win[:, :vis_w]
        Image.fromarray(np.clip(fr, 0, 255).astype(np.uint8)).save(
            os.path.join(folder, f"frame_{i:05d}.png"))
    return {"folder": folder, "payload": payload, "truncated": True}
