"""Horizontal x vertical cross, from MEASURED word boxes.

Measuring word boxes straight from the pixels (wordboxes.py) shows the numeral
centre sits at 93% of "vintage" (h6) and 99% of "tuition" (h7) -- right on the
boundary -- and squarely in a word GAP at h10 and h11.  So the same-row right/
left neighbours are live candidates at several hours, but every sweep so far
(the ranked one included, which cut at top-3) has left them out.

Candidates per hour, from the measured boxes:
    the word containing the numeral centre in row c, plus its immediate left
    and right neighbours in row c, plus the word containing the centre in rows
    c-1 and c+1.
Anchors h4/h8/h12 are fixed -- their centres land solidly inside the word
(82%, 61%, 48%), not near a boundary.
"""
import itertools, json, os, time
from multiprocessing import Pool
import numpy as np
from PIL import Image
from mnemonic import Mnemonic
import moss_oracle as O
import pathcross as P
from rankcand import CENTER, spans

W = Mnemonic('english').wordlist
a = np.array(Image.open('ocp/2-mid-prizes/logicbeach-powerful-moss-0-54eth/'
                        'clues/powerfulmoss-poap.png').convert('RGB')).astype(np.int16)
mx = a.max(axis=2)
TEXT = (np.abs(mx - 177) <= 14) | (np.abs(mx - 133) <= 12) | \
       ((a[:, :, 0] >= 250) & (a[:, :, 1] >= 250) & (np.abs(a[:, :, 2] - 177) <= 14))
ROWS = json.load(open('rows.json'))
NUM = json.load(open('numerals.json'))
CONF = {4: 'strategy', 8: 'stick', 12: 'leisure'}

# reduce to the standard chain, indices 0..4
P.PATHS = [p for p in P.PATHS if p[0].startswith("m/44'/60'/0'/0/")]
P.TREE = P._build_tree(P.PATHS)
TARGET = P.TARGET


def labelled(ri):
    """measured ink runs on row ri, each labelled with the model's word"""
    if ri < 0 or ri >= len(ROWS):
        return []
    y0, y1 = ROWS[ri]
    col = TEXT[y0:y1 + 1, :].sum(axis=0)
    on = col > 0
    runs = []; i = 0
    while i < len(on):
        if on[i]:
            j = i
            while j + 1 < len(on) and on[j + 1]:
                j += 1
            runs.append([i, j]); i = j + 1
        else:
            i += 1
    merged = []
    for r in runs:
        if merged and r[0] - merged[-1][1] <= 12:
            merged[-1][1] = r[1]
        else:
            merged.append(r)
    model = [(w, x0, x1) for w, x0, x1 in spans(ri) if x1 > 0 and x0 < 2004]
    if not model:
        return []
    out = []
    for a0, a1 in merged:
        c = (a0 + a1) / 2
        best = min(model, key=lambda t: abs((t[1] + t[2]) / 2 - c))
        out.append((best[0], a0, a1))
    return out


def cands(h):
    d = NUM[str(h)]
    cx = (d['x0'] + d['x1']) / 2
    c0 = CENTER[h]
    out = []
    for ri in (c0, c0 - 1, c0 + 1):
        lab = labelled(ri)
        if not lab:
            continue
        inside = [t for t in lab if t[1] <= cx <= t[2]]
        if inside:
            k = lab.index(inside[0])
            picks = [k]
            if ri == c0:                      # neighbours only on the home row
                picks += [k - 1, k + 1]
        else:
            left = [i for i, t in enumerate(lab) if t[2] < cx]
            right = [i for i, t in enumerate(lab) if t[1] > cx]
            picks = ([max(left)] if left else []) + ([min(right)] if right else [])
        for k in picks:
            if 0 <= k < len(lab) and lab[k][0] not in out:
                out.append(lab[k][0])
    return out


CAND = {h: ([CONF[h]] if h in CONF else cands(h)) for h in range(1, 13)}
PROG = 'hcross_progress.txt'


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
        vals = [d[h] for h in range(1, 13)]
        seqs = [[d[h] for h in o] for o in P.ORD] + \
               [sorted(vals), sorted(vals, reverse=True)]
        for words in seqs:
            if not O.valid_checksum(words):
                continue
            n += 1
            lab = test(words)
            if lab:
                hits.append((words, lab))
                print('!!!! MATCH', ' '.join(words), lab, flush=True)
                open('MOSS_HIT_HX.txt', 'w').write(
                    json.dumps({'words': words, 'path': lab}))
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
    print(f'{tot} sets x {len(P.ORD)+2} orderings = {tot*(len(P.ORD)+2)} phrases, '
          f'~1/16 checksum-valid, x {len(P.PATHS)} paths', flush=True)
    todo = [f for f in CAND[1] if f not in done]
    t0 = time.time(); g = 0
    with Pool(4) as p:
        for first, n, hits in p.imap_unordered(work, todo):
            g += n
            with open(PROG, 'a') as fh:
                fh.write(f'DONE {first} checked={n} cum={g} '
                         f't={time.time()-t0:.0f}\n')
            print(f'{first} done n={n} cum={g} t={time.time()-t0:.0f}', flush=True)
            if hits:
                print('SOLVED', hits, flush=True); break
    print('tested', g, 'valid phrases x', len(P.PATHS), 'paths; elapsed',
          time.time() - t0, flush=True)
