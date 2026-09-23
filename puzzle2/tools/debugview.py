"""debugview.py -- annotated crops written every iteration, so the window can be
refined by looking at what the pipeline actually saw."""
from __future__ import annotations

import os

import numpy as np
from PIL import Image, ImageDraw

import glyphlib as gl


def _rgb(gray):
    g = np.clip(gray, 0, 255).astype(np.uint8)
    return Image.fromarray(np.dstack([g, g, g]))


def save_overview(stretched, glyphs, path, readings=None, title=""):
    """The full stretched residual with every detected component boxed. Boxes are
    colour-coded: green trusted, orange low-confidence, red truncated."""
    im = _rgb(stretched)
    d = ImageDraw.Draw(im)
    for i, g in enumerate(glyphs):
        if g is None:                     # an empty slot has nothing to box
            continue
        y0, y1, x0, x1 = g.box
        r = readings[i] if readings and i < len(readings) else None
        if r is None:
            colour, label = (0, 160, 255), str(i)
        elif r["cut"]:
            colour, label = (255, 40, 40), f"{i}:{r['char']}?CUT"
        elif r["trusted"]:
            colour, label = (40, 220, 40), f"{i}:{r['char']} {r['score']:.2f}"
        else:
            colour, label = (255, 170, 0), f"{i}:{r['char']} {r['score']:.2f}"
        d.rectangle([x0 - 1, y0 - 1, x1, y1], outline=colour)
        d.text((x0, max(0, y0 - 10)), label, fill=colour)
    if title:
        d.text((4, 4), title, fill=(255, 255, 0))
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    im.save(path)
    return path


def save_contact_sheet(glyphs, path, readings=None, cell=48, cols=16):
    """Every glyph crop, upscaled, in reading order -- the sheet to eyeball when
    deciding whether a box is really a character."""
    n = len(glyphs)
    if n == 0 or all(g is None for g in glyphs):
        return None
    rows = (n + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell, rows * (cell + 12)), (16, 16, 16))
    d = ImageDraw.Draw(sheet)
    for i, g in enumerate(glyphs):
        if g is None:
            continue
        p = g.patch
        if p.size == 0:
            continue
        im = _rgb(p).resize((cell - 4, cell - 4), Image.NEAREST)
        cx, cy = (i % cols) * cell, (i // cols) * (cell + 12)
        sheet.paste(im, (cx + 2, cy + 2))
        if readings and i < len(readings):
            r = readings[i]
            colour = (255, 40, 40) if r["cut"] else (
                (40, 220, 40) if r["trusted"] else (255, 170, 0))
            d.text((cx + 2, cy + cell - 2), f"{r['char']}{'!' if r['cut'] else ''}",
                   fill=colour)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    sheet.save(path)
    return path


def save_orientations(glyph, path, cell=64):
    """One glyph in all 8 dihedral views, for checking the mirror/rotation call."""
    sheet = Image.new("RGB", (8 * cell, cell + 12), (16, 16, 16))
    d = ImageDraw.Draw(sheet)
    for i, (rot, mirror) in enumerate(gl.ORIENTATIONS):
        v = gl.orient(glyph.patch, rot, mirror)
        if v.size == 0:
            continue
        sheet.paste(_rgb(v).resize((cell - 4, cell - 4), Image.NEAREST),
                    (i * cell + 2, 2))
        d.text((i * cell + 2, cell), gl.orientation_name(rot, mirror)[:9],
               fill=(200, 200, 200))
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    sheet.save(path)
    return path
