"""Ranked-candidate sweep with the checksum used as a PRIOR, not a blind spot.

Reasoning: the author funded a real wallet, so they started from a valid BIP39
mnemonic and then placed those 12 words on the clock -- they did not mark 12
words and hope for a 1-in-16 checksum.  So among candidate readings the true
one should be checksum-VALID (mechanism A), or the marked phrase was passed
through a checksum repairer, which changes only the last word (mechanism B).

Candidates come from rankcand (2D distance), so the horizontal alternates
(outdoor, major) are finally included.  Each phrase is tested against all 18
derivation paths via the shared-seed prefix tree.
"""
import itertools, json, os, sys, time
from multiprocessing import Pool
import moss_oracle as O
import csrepair as C
import pathcross as P          # ORD, PATHS, addrs_for_seed, TARGET
from rankcand import ranked

MODE = sys.argv[1] if len(sys.argv) > 1 else 'A'      # A=valid-only, B=repair
K = {h: 3 for h in range(1, 13)}
K[10] = 4      # outer / outdoor / okay / old
K[11] = 5      # main / maze / meadow / major / mind
CAND = {h: [w for w, d, r in ranked(h)[:K[h]]] for h in range(1, 13)}
TARGET = P.TARGET
PROG = f'csweep_{MODE}_progress.txt'


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
            if MODE == 'A':
                if not O.valid_checksum(words):
                    continue
                cand = words
            else:
                cand = C.repair(words)
            n += 1
            lab = test(cand)
            if lab:
                hits.append((cand, lab))
                print('!!!! MATCH', ' '.join(cand), lab, flush=True)
                open(f'MOSS_HIT_CS{MODE}.txt', 'w').write(
                    json.dumps({'words': cand, 'path': lab}))
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
    npr = tot * (len(P.ORD) + 2)
    print(f'mode {MODE}: {tot} sets x {len(P.ORD)+2} orderings = {npr} phrases')
    print(f'  -> {"~1/16 checksum-valid = %d" % (npr//16) if MODE=="A" else npr} '
          f'derivation groups x {len(P.PATHS)} paths', flush=True)
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
          time.time() - t0, flush=True)
