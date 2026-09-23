"""Ranked candidate words per hour, by 2D distance to the numeral centre.

Every previous sweep took nearest-word-in-row and varied only the ROW, so the
horizontal alternates at the ambiguous hours (outdoor vs outer, major vs main)
were never in any candidate list.  This ranks ALL words in the rows spanned by
the numeral by true 2D distance, so horizontal and vertical ambiguity are
handled by one metric.

Distance: dx to the word box (0 if inside), dy to the row centre.  Combined as
hypot(dx, dy * ASPECT) with ASPECT<1 because a row step (48px) is a smaller
semantic jump than the same distance horizontally (a 25.46px cell).
"""
import json
import numpy as np
from mnemonic import Mnemonic

W = Mnemonic('english').wordlist
idx = {w: i for i, w in enumerate(W)}
CW = 25.46
ROW = {2:('knife',437.2),3:('left',361.1),4:('live',361.7),5:('maid',256.8),
       6:('maximum',307.3),7:('million',256.3),10:('noodle',-354.0),11:('oil',127.0),
       12:('other',-20.7),13:('pass',152.0),14:('phrase',-46.2),19:('recipe',-357.0),
       20:('report',-51.5),21:('ring',-46.1),22:('saddle',52.0),23:('science',-306.0),
       28:('spoil',177.5),29:('stereo',4.8),30:('suffer',33.8),31:('swim',106.7),
       33:('tobacco',81.3),34:('track',208.2),35:('tube',284.7),36:('unhappy',183.3),
       37:('vacuum',256.8),38:('video',358.2),39:('warrior',409.3),40:('when',-411.0)}
CENTER = {1:5, 2:12, 3:21, 4:29, 5:35, 6:38, 7:35, 8:29, 9:21, 10:12, 11:5, 12:3}
ROWS = json.load(open('rows.json'))
NUM = json.load(open('numerals.json'))
ASPECT = 0.55


def spans(ri):
    if ri not in ROW:
        return []
    sw, X0 = ROW[ri]
    s = idx[sw]; out = []; c = 0
    for k in range(80):
        i = s + k
        if i >= len(W):
            break
        x0 = X0 + CW * c
        x1 = x0 + CW * len(W[i])
        if x0 > 2150:
            break
        out.append((W[i], x0, x1)); c += len(W[i]) + 1
    return out


def rowcentre(ri):
    a, b = ROWS[ri]
    return (a + b) / 2


def ranked(h, span=2):
    """(word, dist, row) sorted by distance to hour h's numeral centre."""
    d = NUM[str(h)]
    cx, cy = (d['x0'] + d['x1']) / 2, (d['y0'] + d['y1']) / 2
    c0 = CENTER[h]
    out = []
    for ri in range(c0 - span, c0 + span + 1):
        yc = rowcentre(ri) if 0 <= ri < len(ROWS) else None
        if yc is None:
            continue
        dy = (yc - cy) * ASPECT
        for w, x0, x1 in spans(ri):
            if x1 < 0 or x0 > 2004:
                continue
            dx = 0.0 if x0 <= cx <= x1 else (x0 - cx if x0 > cx else cx - x1)
            out.append((w, float(np.hypot(dx, dy)), ri))
    out.sort(key=lambda t: t[1])
    return out


if __name__ == '__main__':
    for h in range(1, 13):
        r = ranked(h)[:8]
        print(f'h{h:>2}: ' + '  '.join(f'{w}({d:.0f})' for w, d, _ in r))
