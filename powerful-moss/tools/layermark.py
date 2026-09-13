"""Which words does each overlay layer actually cover?

The POAP separates into four overlays on three base values.  Only ONE of them
(gray-83 numerals) has ever been used as a word selector.  This measures, for
every word box in every reconstructed row, what fraction of that word's text
pixels are covered by each of the other layers -- so a second marking layer, if
one exists, shows up as a small set of words with anomalously high coverage.
"""
import json
import numpy as np
from PIL import Image
from rankcand import spans, ROW

a = np.array(Image.open('ocp/2-mid-prizes/logicbeach-powerful-moss-0-54eth/'
                        'clues/powerfulmoss-poap.png').convert('RGB')).astype(np.int16)
R, G, B = a[:, :, 0], a[:, :, 1], a[:, :, 2]
ROWS = json.load(open('rows.json'))

# every pixel that is wordlist TEXT, however it has been overlaid
plain   = (R == 177) & (G == 177) & (B == 177)
undernum= (R == 133) & (G == 133) & (B == 133)
underred= (R == 177) & (G <= 12) & (B <= 12)
undergrid=(R == 177) & (G == 177) & (B <= 12)
undertitle=(R >= 250) & (G >= 250) & (np.abs(B - 177) <= 6)
TEXT = plain | undernum | underred | undergrid | undertitle

LAYERS = {'numeral': undernum, 'red_ray': underred,
          'grid': undergrid, 'title': undertitle}

rows = []
for ri in sorted(ROW):
    y0, y1 = ROWS[ri]
    for w, x0, x1 in spans(ri):
        ix0, ix1 = int(round(x0)), int(round(x1))
        if ix0 < 2 or ix1 > a.shape[1] - 2:
            continue
        box = TEXT[y0:y1+1, ix0:ix1]
        n = int(box.sum())
        if n < 40:
            continue
        cov = {k: float(v[y0:y1+1, ix0:ix1].sum()) / n for k, v in LAYERS.items()}
        rows.append((w, ri, n, cov))

print(f'{len(rows)} word boxes measured\n')
for k in LAYERS:
    vals = np.array([r[3][k] for r in rows])
    nz = (vals > 0.05).sum()
    print(f'--- {k}: {nz} words with >5% coverage '
          f'(mean {vals.mean():.3f}, max {vals.max():.3f}) ---')
    top = sorted(rows, key=lambda r: -r[3][k])[:14]
    for w, ri, n, cov in top:
        if cov[k] <= 0.02:
            break
        print(f'    {w:<10} row{ri:<3} {cov[k]*100:5.1f}%  ({n} px)')
    print()
