"""Fit the 12 numerals to an ellipse at exact 30-degree intervals.

The POAP is a matplotlib figure (visible grid + axis labels), so each numeral
was placed at an exact data coordinate.  The glyph bbox / ink centroid are
noisy renders of that point.  Fitting cx,cy,rx,ry,phi to all 12 at once
recovers the INTENDED anchor to sub-pixel accuracy, and the systematic
bbox-minus-anchor offset reveals matplotlib's ha/va convention.
"""
import json
import numpy as np
from scipy.optimize import least_squares

NUM = json.load(open('numerals.json'))
PCX = json.load(open('numcentroid.json'))
ROWS = json.load(open('rows.json'))

hours = list(range(1, 13))
bb = np.array([[NUM[str(h)]['cx'], NUM[str(h)]['cy']] for h in hours])
ink = np.array([[PCX[str(h)]['pcx'], PCX[str(h)]['pcy']] for h in hours])


def model(p, hrs):
    cx, cy, rx, ry, phi = p
    th = np.deg2rad(90 - 30 * np.array(hrs)) + phi
    return np.stack([cx + rx * np.cos(th), cy - ry * np.sin(th)], axis=1)


def fit(pts, label):
    def res(p):
        return (model(p, hours) - pts).ravel()
    p0 = [1000, 1007, 865, 840, 0.0]
    r = least_squares(res, p0)
    cx, cy, rx, ry, phi = r.x
    pred = model(r.x, hours)
    d = np.linalg.norm(pred - pts, axis=1)
    print(f'--- fit to {label} ---')
    print(f'  center=({cx:.1f},{cy:.1f})  rx={rx:.1f} ry={ry:.1f} '
          f'phi={np.rad2deg(phi):+.2f}deg')
    print(f'  residual: rms={np.sqrt((d**2).mean()):.1f}px max={d.max():.1f}px')
    return r.x, pred, d


pb, predb, db = fit(bb, 'glyph bbox centres')
pi, predi, di = fit(ink, 'ink centroids')

print()
print('per-hour residual (bbox fit) and bbox-minus-ink offset:')
print(f"{'h':>3} {'bbox_res':>9} {'ink_res':>8} {'ink-bbox dx':>12} {'dy':>7}")
for i, h in enumerate(hours):
    print(f'{h:>3} {db[i]:>9.1f} {di[i]:>8.1f} '
          f'{ink[i,0]-bb[i,0]:>12.1f} {ink[i,1]-bb[i,1]:>7.1f}')

# Which text row does each fitted anchor land in?
centres = [(a + b) / 2 for a, b in ROWS]


def row_of(y):
    """row index (1-based as used throughout) whose band contains y,
    else nearest band centre."""
    for i, (a, b) in enumerate(ROWS):
        if a <= y <= b:
            return i + 1, 0.0
    i = int(np.argmin([abs(y - c) for c in centres]))
    return i + 1, y - centres[i]


print()
print('FITTED ANCHOR -> ROW')
print(f"{'h':>3} {'anchor_x':>9} {'anchor_y':>9} {'row':>4} {'gap':>7} "
      f"{'bbox_row':>9} {'ink_row':>8}")
out = {}
for i, h in enumerate(hours):
    ax, ay = predb[i]
    r, g = row_of(ay)
    rb, _ = row_of(bb[i, 1])
    ri, _ = row_of(ink[i, 1])
    out[h] = {'ax': float(ax), 'ay': float(ay), 'row': r,
              'row_bbox': rb, 'row_ink': ri}
    print(f'{h:>3} {ax:>9.1f} {ay:>9.1f} {r:>4} {g:>7.1f} {rb:>9} {ri:>8}')
json.dump(out, open('anchorfit.json', 'w'), indent=1)
print('\nwrote anchorfit.json')
