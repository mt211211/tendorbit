"""Per-word ink-density scan.

The dossier's "established fact 4" rules out a distinctly marked word overlay
on the basis of a histogram that found only one text-gray population -- but
the real image has at least three (177 plain, 133 under-numeral, plus text
under the red/yellow/title layers).  So the question is still open, and it is
directly measurable: a bolded or recoloured word has anomalous ink density.

For every word box in every reconstructed row, count text pixels and normalise
by box area.  Outliers are candidates for a deliberate mark.
"""
import json
import numpy as np
from PIL import Image
from mnemonic import Mnemonic
from rankcand import spans, ROW, ROWS

W = Mnemonic('english').wordlist
a = np.array(Image.open('ocp/2-mid-prizes/logicbeach-powerful-moss-0-54eth/'
                        'clues/powerfulmoss-poap.png').convert('RGB')).astype(np.int16)
mx = a.max(axis=2)
# every way the wordlist text appears anywhere in the image
text = (np.abs(mx - 177) <= 14) | (np.abs(mx - 133) <= 12) | \
       ((a[:, :, 0] >= 250) & (a[:, :, 1] >= 250) & (np.abs(a[:, :, 2] - 177) <= 14))
H, Wd = text.shape

rows = []
for ri in sorted(ROW):
    y0, y1 = ROWS[ri]
    for w, x0, x1 in spans(ri):
        ix0, ix1 = int(round(x0)), int(round(x1))
        if ix0 < 4 or ix1 > Wd - 4:      # skip words clipped by the disc/frame
            continue
        box = text[y0:y1 + 1, ix0:ix1]
        if box.size == 0:
            continue
        dens = box.sum() / box.size
        rows.append((dens, w, ri, ix0, ix1, int(box.sum())))

d = np.array([r[0] for r in rows])
print(f'{len(rows)} complete word boxes across {len(ROW)} reconstructed rows')
print(f'ink density: mean={d.mean():.4f} sd={d.std():.4f} '
      f'min={d.min():.4f} max={d.max():.4f}')
z = (d - d.mean()) / d.std()
order = np.argsort(-z)
print('\nHIGHEST density (would be bold / filled):')
for i in order[:15]:
    dn, w, ri, x0, x1, n = rows[i]
    print(f'  {w:<10} row{ri:<3} z={z[i]:+.2f} dens={dn:.4f} px={n}')
print('\nLOWEST density (would be faint / hollow):')
for i in order[-15:]:
    dn, w, ri, x0, x1, n = rows[i]
    print(f'  {w:<10} row{ri:<3} z={z[i]:+.2f} dens={dn:.4f} px={n}')

# density depends on letter shapes, so also normalise per word LENGTH
print('\nper-length z-scores (controls for which letters a word contains):')
bylen = {}
for i, (dn, w, ri, x0, x1, n) in enumerate(rows):
    bylen.setdefault(len(w), []).append(i)
best = []
for L, ids in bylen.items():
    v = np.array([rows[i][0] for i in ids])
    if len(v) < 8:
        continue
    zz = (v - v.mean()) / v.std()
    for j, i in enumerate(ids):
        best.append((abs(zz[j]), zz[j], rows[i][1], rows[i][2]))
best.sort(reverse=True)
for az, zz, w, ri in best[:20]:
    print(f'  {w:<10} row{ri:<3} z={zz:+.2f}')
