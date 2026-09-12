"""Full 12! permutation search over the visually-read words, checksum-filtered.

State of play: the words are visually certain at ten hours and the two
ambiguous ones are binary; the whole word NEIGHBOURHOOD (ranked, measured-box,
+/-rows, +/-columns, one-word-free-anywhere) is now exhausted under the
checksum prior, as are 125 derivation mechanisms, 18 paths and 29 passphrases.
The one large space left with a real prior is the ORDER: the ledger's 12!
sweep was run for a single reading variant, unfiltered, at one path.

The checksum makes the rest affordable: only 1 permutation in 16 is valid, so
479,001,600 orderings cost ~29.9M derivations instead.  Enumerating and
filtering is cheap (~3us each); only survivors pay the PBKDF2.

Checkpointed per (variant, first word) so it resumes after a restart.
"""
import itertools, json, os, sys, time, hashlib
from multiprocessing import Pool
from mnemonic import Mnemonic
import moss_oracle as O
import pathcross as P

W = Mnemonic('english').wordlist
IDX = {w: i for i, w in enumerate(W)}

BASE = {1:'mandate', 2:'oyster', 3:'romance', 4:'strategy', 5:'turtle',
        6:'vintage', 7:'tuition', 8:'stick', 9:'riot', 12:'leisure'}
# (outer, main) is the ledger's already-exhausted variant; the other three
# were never run at 12!
VARIANTS = [('outer', 'major'), ('outdoor', 'main'), ('outdoor', 'major'),
            ('outer', 'main')]

P.PATHS = [p for p in P.PATHS if p[0].startswith("m/44'/60'/0'/0/")]
P.TREE = P._build_tree(P.PATHS)
TARGET = P.TARGET
PROG = 'perm12_progress.txt'


def valid_idx(perm):
    """BIP39 checksum test straight from an 11-bit index tuple"""
    b = 0
    for i in perm:
        b = (b << 11) | i
    ent = b >> 4
    return (hashlib.sha256(ent.to_bytes(16, 'big')).digest()[0] >> 4) == (b & 0xF)


def work(task):
    vi, first = task
    w10, w11 = VARIANTS[vi]
    d = dict(BASE); d[10] = w10; d[11] = w11
    words = [d[h] for h in range(1, 13)]
    ids = [IDX[w] for w in words]
    rest = [i for i in ids if i != ids[first]] if False else None
    # permutations whose first element is ids[first]
    head = ids[first]
    tail = ids[:first] + ids[first + 1:]
    n = 0; nv = 0; hits = []
    for p in itertools.permutations(tail):
        perm = (head,) + p
        n += 1
        if not valid_idx(perm):
            continue
        nv += 1
        ph = " ".join(W[i] for i in perm)
        seed = O.mnemonic_to_seed(ph)
        for lab, priv in P.addrs_for_seed(seed):
            if O.eth_address(priv).lower() == TARGET:
                hits.append((ph, lab))
                print('!!!! MATCH', ph, lab, flush=True)
                open('MOSS_HIT_PERM.txt', 'w').write(
                    json.dumps({'phrase': ph, 'path': lab}))
    return task, n, nv, hits


if __name__ == '__main__':
    done = set()
    if os.path.exists(PROG):
        for ln in open(PROG):
            if ln.startswith('DONE '):
                done.add(ln.split()[1])
    tasks = [(vi, f) for vi in range(len(VARIANTS)) for f in range(12)]
    tasks = [t for t in tasks if f'{t[0]}|{t[1]}' not in done]
    print(f'{len(VARIANTS)} readings x 12! = {len(VARIANTS)*479001600} orderings')
    print(f'  ~1/16 checksum-valid -> ~{len(VARIANTS)*29937600} derivation groups '
          f'x {len(P.PATHS)} paths')
    print(f'{len(tasks)} tasks remaining ({len(done)} done)', flush=True)
    t0 = time.time(); g = 0; gv = 0
    with Pool(4) as p:
        for task, n, nv, hits in p.imap_unordered(work, tasks):
            g += n; gv += nv
            with open(PROG, 'a') as fh:
                fh.write(f'DONE {task[0]}|{task[1]} perms={n} valid={nv} '
                         f'cum={g} cumvalid={gv} t={time.time()-t0:.0f}\n')
            print(f'variant {VARIANTS[task[0]]} head{task[1]}: perms={n} '
                  f'valid={nv} cumvalid={gv} t={time.time()-t0:.0f}', flush=True)
            if hits:
                print('SOLVED', hits, flush=True); break
    print('enumerated', g, 'orderings;', gv, 'checksum-valid x',
          len(P.PATHS), 'paths; elapsed', time.time() - t0, flush=True)
