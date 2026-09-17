"""Sweep the COVERAGE readout rule.

Every previous sweep on this puzzle read each numeral by the word containing its
centroid.  A different and equally natural rule is "the numeral marks the word it
covers most", measured from the gray-133 layer (wordlist text seen through a
numeral).  The two rules disagree at several hours, and the coverage ranking has
never been in any candidate list.

Candidates = top-3 words per numeral by covered fraction, unioned with the top
word by absolute covered pixels.
"""
import itertools, json, os, time
from multiprocessing import Pool
import numpy as np
from PIL import Image
import moss_oracle as O
import pathcross as P
import csrepair as C
from orderlib import ORDERS
from rankcand import spans, ROW

a = np.array(Image.open('ocp/2-mid-prizes/logicbeach-powerful-moss-0-54eth/'
                        'clues/powerfulmoss-poap.png').convert('RGB')).astype(np.int16)
R, G, B = a[:, :, 0], a[:, :, 1], a[:, :, 2]
undernum = (R == 133) & (G == 133) & (B == 133)
TEXT = (((R == 177) & (G == 177) & (B == 177)) | undernum |
        ((R == 177) & (G <= 12) & (B <= 12)) |
        ((R == 177) & (G == 177) & (B <= 12)) |
        ((R >= 250) & (G >= 250) & (np.abs(B - 177) <= 6)))
ROWS = json.load(open('rows.json'))
NUM = json.load(open('numerals.json'))

P.PATHS = [p for p in P.PATHS if p[0].startswith("m/44'/60'/0'/0/")]
P.TREE = P._build_tree(P.PATHS)
TARGET = P.TARGET

CAND = {}
for h in range(1, 13):
    d = NUM[str(h)]
    scored = []
    for ri in sorted(ROW):
        y0, y1 = ROWS[ri]
        if y1 < d['y0'] or y0 > d['y1']:
            continue
        for w, x0, x1 in spans(ri):
            ix0, ix1 = int(round(x0)), int(round(x1))
            if ix1 < d['x0'] or ix0 > d['x1'] or ix0 < 2 or ix1 > a.shape[1]-2:
                continue
            tot = int(TEXT[y0:y1+1, ix0:ix1].sum())
            if tot < 40:
                continue
            cov = int(undernum[y0:y1+1, ix0:ix1].sum())
            scored.append((cov/tot, cov, w))
    byfrac = [w for _, _, w in sorted(scored, reverse=True)[:3]]
    byabs = sorted(scored, key=lambda t: -t[1])[0][2]
    lst = byfrac + ([byabs] if byabs not in byfrac else [])
    CAND[h] = lst[:4]

PROG = 'covsweep_progress.txt'


def test(words):
    seed = O.mnemonic_to_seed(" ".join(words))
    for lab, priv in P.addrs_for_seed(seed):
        if O.eth_address(priv).lower() == TARGET:
            return lab
    return None


def work(first):
    others = [CAND[h] for h in range(2, 13)]
    n = 0; hits = []
    for rest in itertools.product(*others):
        d = {1: first}
        for i, h in enumerate(range(2, 13)):
            d[h] = rest[i]
        for oname, o in ORDERS.items():
            seq = [d[h] for h in o]
            for tag, cand in (('raw', seq), ('repair', C.repair(seq))):
                if tag == 'raw' and not O.valid_checksum(cand):
                    continue
                n += 1
                lab = test(cand)
                if lab:
                    hits.append((cand, lab, oname, tag))
                    print('!!!! MATCH', ' '.join(cand), lab, oname, tag, flush=True)
                    open('MOSS_HIT_COV.txt', 'w').write(json.dumps(
                        {'words': cand, 'path': lab, 'order': oname, 'mode': tag}))
    return first, n, hits


if __name__ == '__main__':
    done = set()
    if os.path.exists(PROG):
        for ln in open(PROG):
            if ln.startswith('DONE '):
                done.add(ln.split()[1])
    tot = 1
    for h in range(1, 13):
        print(h, CAND[h]); tot *= len(CAND[h])
    print(f'{tot} sets x {len(ORDERS)} orderings x (valid-raw + repaired) '
          f'x {len(P.PATHS)} paths', flush=True)
    todo = [f for f in CAND[1] if f not in done]
    t0 = time.time(); g = 0
    with Pool(4) as p:
        for first, n, hits in p.imap_unordered(work, todo):
            g += n
            with open(PROG, 'a') as fh:
                fh.write(f'DONE {first} checked={n} cum={g} t={time.time()-t0:.0f}\n')
            print(f'{first} done n={n} cum={g} t={time.time()-t0:.0f}', flush=True)
            if hits:
                print('SOLVED', hits, flush=True); break
    print('tested', g, 'phrases x', len(P.PATHS), 'paths; elapsed',
          time.time()-t0, flush=True)
