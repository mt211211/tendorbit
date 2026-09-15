"""Global layer-offset hypothesis.

The PNG says "Created with GIMP", so the artwork was composited: a wordlist
text layer plus a clock-numeral layer.  If those two layers were shifted
relative to each other before flattening, every numeral points at the wrong
word BY THE SAME OFFSET -- and that is invisible from the image, because the
three "confirmed anchors" come from the same centroid rule and are shifted
along with everything else.  Nothing in the analysis so far can detect this:
the reading is internally consistent at any offset.

So sweep a global (dx, dy) applied to all 12 numeral centres, read the 12
words at each offset, and test every distinct 12-word tuple that falls out.
dx steps finely (word boundaries are ~25px apart), dy by fractions of the
48px row pitch.
"""
import itertools, json, time
import numpy as np
from mnemonic import Mnemonic
import moss_oracle as O
import csrepair as C
import pathcross as P
from orderlib import ORDERS
from rankcand import CENTER, spans, rowcentre, ROW

W = Mnemonic('english').wordlist
NUM = json.load(open('numerals.json'))
ROWS = json.load(open('rows.json'))
TARGET = P.TARGET

CENTRES = {}
for h in range(1, 13):
    d = NUM[str(h)]
    CENTRES[h] = ((d['x0'] + d['x1']) / 2, (d['y0'] + d['y1']) / 2)

ROWC = np.array([ (a + b) / 2 for a, b in ROWS ])


def read_at(dx, dy):
    """the 12 words under the numerals when the numeral layer is moved by
    (dx,dy); None if any hour lands off the reconstructed grid."""
    out = {}
    for h in range(1, 13):
        cx, cy = CENTRES[h]
        cx += dx; cy += dy
        ri = int(np.argmin(np.abs(ROWC - cy)))
        if ri not in ROW:
            return None
        sp = [t for t in spans(ri) if t[2] > 0 and t[1] < 2004]
        if not sp:
            return None
        hit = [w for w, x0, x1 in sp if x0 <= cx <= x1]
        if hit:
            out[h] = hit[0]
        else:
            # numeral centre lands in a word gap (h10/h11 do at zero offset):
            # take the nearest word box
            out[h] = min(sp, key=lambda t: min(abs(t[1] - cx),
                                               abs(t[2] - cx)))[0]
    return tuple(out[h] for h in range(1, 13))


def test(words):
    seed = O.mnemonic_to_seed(" ".join(words))
    for lab, priv in P.addrs_for_seed(seed):
        if O.eth_address(priv).lower() == TARGET:
            return lab
    return None


if __name__ == '__main__':
    t0 = time.time()
    seen = {}
    for dx in range(-260, 261, 4):
        for dy in range(-192, 193, 8):
            r = read_at(dx, dy)
            if r and r not in seen:
                seen[r] = (dx, dy)
    print(f'{len(seen)} distinct 12-word readings over the offset grid '
          f'(dx -260..260 step 4, dy -192..192 step 8)')
    n = 0; hits = []
    for words, (dx, dy) in seen.items():
        ws = list(words)
        d = {h: ws[h - 1] for h in range(1, 13)}
        for oname, o in ORDERS.items():
            seq = [d[h] for h in o]
            for tag, cand in (('raw', seq), ('repair', C.repair(seq))):
                n += 1
                lab = test(cand)
                if lab:
                    hits.append((cand, lab, oname, tag, dx, dy))
                    print('!!!! MATCH', ' '.join(cand), lab, oname, tag,
                          f'offset=({dx},{dy})', flush=True)
                    open('MOSS_HIT_OFFSET.txt', 'w').write(json.dumps(
                        {'words': cand, 'path': lab, 'order': oname,
                         'mode': tag, 'dx': dx, 'dy': dy}))
    print(f'tested {n} phrases x {len(P.PATHS)} paths = {n*len(P.PATHS)} '
          f'derivations in {time.time()-t0:.0f}s')
    print('hits:', hits)
    # show a few sample readings so the sweep is auditable
    print('\nsample readings:')
    for i, (words, off) in enumerate(list(seen.items())[:6]):
        print(f'  offset {off}: {" ".join(words)}')
