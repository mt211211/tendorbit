"""Measure the 24 sunburst rays' angular WIDTH.

The published lead 3 tested ray LENGTH and found it uniform (980-989 px, a 1%
spread), concluding there is no per-ray signal.  Width was never measured.  A
sunburst drawn as 24 wedges can encode 24 values in wedge angle just as easily
as in radius, so this closes the remaining degree of freedom.
"""
import numpy as np
from PIL import Image

a = np.array(Image.open('ocp/2-mid-prizes/logicbeach-powerful-moss-0-54eth/'
                        'clues/powerfulmoss-poap.png').convert('RGB')).astype(np.int16)
R, G, B = a[:, :, 0], a[:, :, 1], a[:, :, 2]
# "red layer": G and B knocked out, R preserved (117 bg, 177 text, 83 numeral)
red = (G <= 20) & (B <= 20) & (R > 40)
H, Wd = red.shape
yy, xx = np.mgrid[0:H, 0:Wd]

# refine the sunburst centre: the red pixels' own centroid near the middle
cy0, cx0 = 1005.0, 1002.0
rr = np.hypot(xx - cx0, yy - cy0)
core = red & (rr < 60)
cy, cx = yy[core].mean(), xx[core].mean()
print(f'sunburst centre = ({cx:.1f}, {cy:.1f})')

ang = (np.degrees(np.arctan2(-(yy - cy), xx - cx))) % 360
rad = np.hypot(xx - cx, yy - cy)

print()
print(f"{'ray':>4} {'nominal':>8} {'measured':>9} {'width_deg':>10} "
      f"{'r_in':>6} {'r_out':>7} {'px':>8}")
res = []
for k in range(24):
    nom = k * 15.0
    # pixels within +/-7 deg of this spoke, outside the hub, inside the disc
    d = (ang - nom + 180) % 360 - 180
    m = red & (np.abs(d) < 7.0) & (rad > 120) & (rad < 960)
    n = int(m.sum())
    if n < 50:
        print(f'{k:>4} {nom:>8.0f}      (no ray)')
        continue
    # width: at each radius shell, angular extent; average over shells
    ws = []
    for r0 in range(200, 900, 50):
        sh = m & (rad >= r0) & (rad < r0 + 50)
        if sh.sum() < 20:
            continue
        ws.append(d[sh].max() - d[sh].min())
    w = float(np.mean(ws)) if ws else float('nan')
    res.append((k, nom, float(d[m].mean() + nom), w,
                float(rad[m].min()), float(rad[m].max()), n))
    print(f'{k:>4} {nom:>8.0f} {res[-1][2]:>9.2f} {w:>10.3f} '
          f'{res[-1][4]:>6.0f} {res[-1][5]:>7.0f} {n:>8}')

w = np.array([r[3] for r in res])
px = np.array([float(r[6]) for r in res])
print()
print(f'width  : mean={w.mean():.3f} sd={w.std():.3f} '
      f'min={w.min():.3f} max={w.max():.3f}  spread={(w.max()-w.min())/w.mean()*100:.1f}%')
print(f'pixels : mean={px.mean():.0f} sd={px.std():.0f} '
      f'spread={(px.max()-px.min())/px.mean()*100:.1f}%')
hours = [r for r in res if r[0] % 2 == 0]
between = [r for r in res if r[0] % 2 == 1]
print(f'even spokes (hour-aligned, n={len(hours)}): '
      f'mean width {np.mean([r[3] for r in hours]):.3f}')
print(f'odd spokes (between hours, n={len(between)}): '
      f'mean width {np.mean([r[3] for r in between]):.3f}')
