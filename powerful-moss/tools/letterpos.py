"""Use the numeral's position WITHIN its word as data, not as a selector.

Each numeral centre sits at some fraction through the word it covers.  Twelve
words with twelve positions is twelve letter indices, which could spell a
passphrase or a key.  Never tested.

Boxes are re-measured per word (not by merging ink runs, which fused
"stove"+"strategy" at h4) by locating each word's span from the layout model
and clipping to its actual ink.
"""
import json
import numpy as np
from PIL import Image
from rankcand import CENTER, spans

a = np.array(Image.open('ocp/2-mid-prizes/logicbeach-powerful-moss-0-54eth/'
                        'clues/powerfulmoss-poap.png').convert('RGB')).astype(np.int16)
mx = a.max(axis=2)
TEXT = (np.abs(mx - 177) <= 14) | (np.abs(mx - 133) <= 12) | \
       ((a[:, :, 0] >= 250) & (a[:, :, 1] >= 250) & (np.abs(a[:, :, 2] - 177) <= 14))
ROWS = json.load(open('rows.json'))
NUM = json.load(open('numerals.json'))

READING = {1:'mandate', 2:'oyster', 3:'romance', 4:'strategy', 5:'turtle',
           6:'vintage', 7:'tuition', 8:'stick', 9:'riot', 12:'leisure'}
GAPS = {10: ('outdoor', 'outer'), 11: ('main', 'major')}


def ink_box(ri, x0m, x1m):
    """tighten a model span to the actual ink inside it"""
    y0, y1 = ROWS[ri]
    lo, hi = max(0, int(x0m) - 6), min(TEXT.shape[1], int(x1m) + 6)
    col = TEXT[y0:y1 + 1, lo:hi].sum(axis=0)
    nz = np.nonzero(col)[0]
    if len(nz) == 0:
        return x0m, x1m
    return lo + nz[0], lo + nz[-1] + 1


print(f"{'h':>3} {'word':<9} {'len':>3} {'box':>14} {'cx':>8} {'frac':>7} "
      f"{'floor':>5} {'round':>5} {'idx*':>5}")
rows = {}
for h in range(1, 13):
    d = NUM[str(h)]
    cx = (d['x0'] + d['x1']) / 2
    ri = CENTER[h]
    words = [(w, x0, x1) for w, x0, x1 in spans(ri)]
    targets = [READING[h]] if h in READING else list(GAPS[h])
    for tw in targets:
        m = [t for t in words if t[0] == tw]
        if not m:
            continue
        _, x0m, x1m = m[0]
        bx0, bx1 = ink_box(ri, x0m, x1m)
        L = len(tw)
        frac = (cx - bx0) / (bx1 - bx0)
        fl = min(L - 1, max(0, int(np.floor(frac * L))))
        rd = min(L - 1, max(0, int(round(frac * (L - 1)))))
        star = min(L - 1, max(0, int(np.floor(frac * (L - 1) + 0.5))))
        rows[(h, tw)] = (frac, tw[fl], tw[rd], tw[star])
        print(f'{h:>3} {tw:<9} {L:>3} [{bx0:>5}-{bx1:>5}] {cx:>8.1f} '
              f'{frac:>7.3f} {tw[fl]:>5} {tw[rd]:>5} {tw[star]:>5}')

json.dump({f'{h}|{w}': v for (h, w), v in rows.items()},
          open('letterpos.json', 'w'), indent=1)
print('\nletter strings (hours 1..12, gap hours take each alternate):')
for conv, i in (('floor', 1), ('round', 2), ('idx*', 3)):
    for g10 in GAPS[10]:
        for g11 in GAPS[11]:
            s = ''
            for h in range(1, 13):
                key = (h, READING[h] if h in READING else
                       (g10 if h == 10 else g11))
                s += rows[key][i] if key in rows else '?'
            print(f'  {conv:<6} h10={g10:<8} h11={g11:<6} -> {s}')
