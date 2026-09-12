"""Model selection: which matplotlib text anchor convention was used?

Each (ha,va) choice predicts a different anchor point per glyph, and the
glyphs differ in width (a narrow "1" vs a wide "12"), so the choices are
distinguishable.  The true convention should fit an exact-30-degree ellipse
far better than the wrong ones.  If none fits well, the numerals were not
placed by clock geometry at all -- which is itself a finding.
"""
import json, itertools
import numpy as np
from scipy.optimize import least_squares

NUM = json.load(open('numerals.json'))
hours = list(range(1, 13))


def anchors(ha, va):
    pts = []
    for h in hours:
        d = NUM[str(h)]
        x = {'left': d['x0'], 'center': (d['x0'] + d['x1']) / 2, 'right': d['x1']}[ha]
        y = {'top': d['y0'], 'center': (d['y0'] + d['y1']) / 2, 'bottom': d['y1']}[va]
        pts.append([x, y])
    return np.array(pts, float)


def model(p, hrs):
    cx, cy, rx, ry, phi = p
    th = np.deg2rad(90 - 30 * np.array(hrs)) + phi
    return np.stack([cx + rx * np.cos(th), cy - ry * np.sin(th)], axis=1)


def score(pts):
    r = least_squares(lambda p: (model(p, hours) - pts).ravel(),
                      [1000, 1005, 860, 840, 0.0])
    d = np.linalg.norm(model(r.x, hours) - pts, axis=1)
    return np.sqrt((d ** 2).mean()), d.max(), r.x


rows = []
for ha, va in itertools.product(['left', 'center', 'right'],
                                ['top', 'center', 'bottom']):
    rms, mx, p = score(anchors(ha, va))
    rows.append((rms, mx, ha, va, p))
rows.sort()
print(f"{'ha':>7} {'va':>7} {'rms':>7} {'max':>7}   center / rx,ry / phi")
for rms, mx, ha, va, p in rows:
    print(f'{ha:>7} {va:>7} {rms:>7.1f} {mx:>7.1f}   '
          f'({p[0]:.0f},{p[1]:.0f}) r=({p[2]:.0f},{p[3]:.0f}) '
          f'phi={np.rad2deg(p[4]):+.2f}')

print()
print('per-hour polar position of bbox centre '
      '(centre=(1000,1006), y scaled to circularise):')
cx, cy = 1000.0, 1006.0
s = 865.5 / 839.8
print(f"{'h':>3} {'radius':>8} {'angle':>8} {'ideal':>7} {'d_ang':>7}")
for h in hours:
    d = NUM[str(h)]
    x, y = (d['x0'] + d['x1']) / 2, (d['y0'] + d['y1']) / 2
    dx, dy = x - cx, (y - cy) * s
    r = np.hypot(dx, dy)
    ang = np.rad2deg(np.arctan2(-dy, dx)) % 360
    ideal = (90 - 30 * h) % 360
    da = (ang - ideal + 180) % 360 - 180
    print(f'{h:>3} {r:>8.1f} {ang:>8.2f} {ideal:>7.0f} {da:>+7.2f}')
