"""Measure word boxes directly from the pixels, not from the fitted model.

The fitted row origins carry ~2.5px of error, which is the same order as the
h10/h11 ambiguity, so the model cannot settle them.  Segmenting each row's text
mask by its column projection gives the real ink extents of each word, and the
inter-word gaps, with no model in the loop.

For each hour: report which measured word box the numeral centre lands in, or
which gap, and how far it is from each neighbour.
"""
import json
import numpy as np
from PIL import Image
from rankcand import ROW, CENTER, spans
from mnemonic import Mnemonic

W = Mnemonic('english').wordlist
a = np.array(Image.open('ocp/2-mid-prizes/logicbeach-powerful-moss-0-54eth/'
                        'clues/powerfulmoss-poap.png').convert('RGB')).astype(np.int16)
mx = a.max(axis=2)
text = (np.abs(mx - 177) <= 14) | (np.abs(mx - 133) <= 12) | \
       ((a[:, :, 0] >= 250) & (a[:, :, 1] >= 250) & (np.abs(a[:, :, 2] - 177) <= 14))
ROWS = json.load(open('rows.json'))
NUM = json.load(open('numerals.json'))


def boxes(ri, min_gap=12):
    """measured (x0,x1) ink runs on row ri, merged across intra-word gaps"""
    y0, y1 = ROWS[ri]
    col = text[y0:y1 + 1, :].sum(axis=0)
    on = col > 0
    runs = []
    i = 0
    while i < len(on):
        if on[i]:
            j = i
            while j + 1 < len(on) and on[j + 1]:
                j += 1
            runs.append([i, j])
            i = j + 1
        else:
            i += 1
    merged = []
    for r in runs:
        if merged and r[0] - merged[-1][1] <= min_gap:
            merged[-1][1] = r[1]
        else:
            merged.append(r)
    return [tuple(m) for m in merged]


print('hour  numeral_cx   verdict')
out = {}
for h in range(1, 13):
    d = NUM[str(h)]
    cx = (d['x0'] + d['x1']) / 2
    ri = CENTER[h]
    bx = boxes(ri)
    # label each measured box using the model's word order for this row
    model = [(w, x0, x1) for w, x0, x1 in spans(ri) if x1 > 0 and x0 < 2004]
    lab = []
    for (a0, a1) in bx:
        c = (a0 + a1) / 2
        best = min(model, key=lambda t: abs((t[1] + t[2]) / 2 - c))
        lab.append((best[0], a0, a1))
    inside = [t for t in lab if t[1] <= cx <= t[2]]
    if inside:
        w, x0, x1 = inside[0]
        frac = (cx - x0) / (x1 - x0)
        verdict = f'INSIDE "{w}" [{x0}-{x1}] at {frac*100:.0f}% of the word'
        out[h] = {'word': w, 'inside': True, 'frac': frac}
    else:
        left = [t for t in lab if t[2] < cx]
        right = [t for t in lab if t[1] > cx]
        lw = max(left, key=lambda t: t[2]) if left else None
        rw = min(right, key=lambda t: t[1]) if right else None
        gapc = (lw[2] + rw[1]) / 2 if lw and rw else None
        verdict = (f'IN GAP between "{lw[0]}"(ends {lw[2]}) and '
                   f'"{rw[0]}"(starts {rw[1]}); gap centre {gapc:.1f}, '
                   f'numeral is {cx-gapc:+.1f} from it')
        out[h] = {'left': lw[0], 'right': rw[0], 'inside': False,
                  'off_gap_centre': cx - gapc}
    print(f'{h:>4} {cx:>11.1f}   {verdict}')

json.dump(out, open('wordboxes.json', 'w'), indent=1)
print('\nwrote wordboxes.json')
