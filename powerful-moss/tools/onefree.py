"""One-word-free search with the checksum as a solver.

The visual reading pins 10 of 12 hours with high confidence.  If exactly one
of the 12 words is wrong, the BIP39 checksum reduces the 2048 possible
replacements to ~128 valid ones -- so "one word misread, and it could be ANY
word in the list" is searchable in minutes, and is far broader than the
+/-2-row windows every previous sweep used.

Also tries the checksum-repair mechanism on the unmodified reading.
"""
import itertools, json, sys, time
from multiprocessing import Pool
from mnemonic import Mnemonic
import moss_oracle as O
import pathcross as P

W = Mnemonic('english').wordlist
BASE = {1:'mandate', 2:'oyster', 3:'romance', 4:'strategy', 5:'turtle',
        6:'vintage', 7:'tuition', 8:'stick', 9:'riot', 12:'leisure'}
H10 = ['outer', 'outdoor', 'okay', 'old']
H11 = ['main', 'maze', 'meadow', 'major', 'mind']
TARGET = P.TARGET


def test(words):
    seed = O.mnemonic_to_seed(" ".join(words))
    for lab, priv in P.addrs_for_seed(seed):
        if O.eth_address(priv).lower() == TARGET:
            return lab
    return None


def work(task):
    w10, w11 = task
    d = dict(BASE); d[10] = w10; d[11] = w11
    vals = [d[h] for h in range(1, 13)]
    seqs = [[d[h] for h in o] for o in P.ORD] + \
           [sorted(vals), sorted(vals, reverse=True)]
    n = 0; hits = []
    for words in seqs:
        for p in range(12):
            orig = words[p]
            for rep in W:
                cand = list(words)
                cand[p] = rep
                if not O.valid_checksum(cand):
                    continue
                n += 1
                lab = test(cand)
                if lab:
                    hits.append((cand, lab, p, orig))
                    print('!!!! MATCH', ' '.join(cand), lab,
                          f'(position {p+1}, was {orig})', flush=True)
                    open('MOSS_HIT_ONEFREE.txt', 'w').write(
                        json.dumps({'words': cand, 'path': lab,
                                    'pos': p, 'was': orig}))
    return task, n, hits


if __name__ == '__main__':
    tasks = [(a, b) for a in H10 for b in H11]
    print(f'{len(tasks)} readings x {len(P.ORD)+2} orderings x 12 positions '
          f'x 2048 words = {len(tasks)*(len(P.ORD)+2)*12*2048} phrases')
    print(f'  ~1/16 checksum-valid, each x {len(P.PATHS)} paths', flush=True)
    t0 = time.time(); g = 0; H = []
    with Pool(2) as p:
        for task, n, hits in p.imap_unordered(work, tasks):
            g += n; H += hits
            print(f'{task} valid={n} cum={g} t={time.time()-t0:.0f}', flush=True)
    print('tested', g, 'checksum-valid phrases x', len(P.PATHS), 'paths')
    print('hits:', H, flush=True)
