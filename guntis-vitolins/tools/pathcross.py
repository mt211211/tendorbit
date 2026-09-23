"""Path x reading cross-sweep.

Gap in the record: 62 derivation paths were tested against ONE reading
(the best reading), and ~700M readings were tested against ONE path
(m/44'/60'/0'/0/0).  Neither sweep covers "reading slightly off AND path
not the MetaMask default".

Efficient because the PBKDF2 seed is shared: one seed -> a prefix tree of
paths, so shared prefixes cost one CKD each, not one per path.

Candidate cube: the +/-1 row set (3 words per hour, 531441 sets).
Orderings: all 24 rotations + READ/COL/sorted (30).
Checkpointed by (ordering-group, hour-1 word).
"""
import itertools, json, os, sys, time
from multiprocessing import Pool
from mnemonic import Mnemonic
import moss_oracle as O

W = Mnemonic('english').wordlist
idx = {w: i for i, w in enumerate(W)}
CW = 25.46
ROW = {2:('knife',437.2),3:('left',361.1),4:('live',361.7),5:('maid',256.8),6:('maximum',307.3),
       11:('oil',127.0),12:('other',-20.7),13:('pass',152.0),20:('report',-51.5),21:('ring',-46.1),
       22:('saddle',52.0),28:('spoil',177.5),29:('stereo',4.8),30:('suffer',33.8),34:('track',208.2),
       35:('tube',284.7),36:('unhappy',183.3),37:('vacuum',256.8),38:('video',358.2),39:('warrior',409.3)}
TRI = {1:(4,5,6),2:(11,12,13),3:(20,21,22),4:(28,29,30),5:(34,35,36),6:(37,38,39),
       7:(34,35,36),8:(28,29,30),9:(20,21,22),10:(11,12,13),11:(4,5,6),12:(2,3,4)}
PCX = json.load(open('numcentroid.json'))


def spans(ri):
    sw, X0 = ROW[ri]
    s = idx[sw]; out = []; c = 0
    for k in range(70):
        i = s + k
        if i >= len(W): break
        x0 = X0 + CW * c; x1 = x0 + CW * len(W[i])
        if x0 > 2150: break
        out.append((W[i], x0, x1)); c += len(W[i]) + 1
    return out


def nearest(ri, cx):
    sp = spans(ri)
    def d(t):
        w, a, b = t
        return 0 if a <= cx <= b else (a - cx if a > cx else cx - b)
    return sorted(sp, key=d)[0][0]


CAND = {}
for h in range(1, 13):
    cx = PCX[str(h)]['pcx']; c = []
    for ri in TRI[h]:
        w = nearest(ri, cx)
        if w not in c: c.append(w)
    CAND[h] = c

READ = [12, 11, 1, 10, 2, 9, 3, 8, 4, 7, 5, 6]
COL = [9, 8, 10, 7, 11, 6, 12, 1, 5, 2, 4, 3]
ORD = []
for st in range(1, 13):
    ORD.append([((st - 1 + k) % 12) + 1 for k in range(12)])
    ORD.append([((st - 1 - k) % 12) + 1 for k in range(12)])
ORD += [READ, READ[::-1], COL, COL[::-1]]

H = 0x80000000
# (label, path) -- grouped so the prefix tree collapses shared work
PATHS = []
for i in range(5):                       # MetaMask/standard, address index 0..4
    PATHS.append((f"m/44'/60'/0'/0/{i}", [44+H, 60+H, 0+H, 0, i]))
for i in range(2):                       # change chain
    PATHS.append((f"m/44'/60'/0'/1/{i}", [44+H, 60+H, 0+H, 1, i]))
for a in range(1, 4):                    # extra BIP44 accounts
    PATHS.append((f"m/44'/60'/{a}'/0/0", [44+H, 60+H, a+H, 0, 0]))
for i in range(3):                       # Ledger legacy / MEW 4-level
    PATHS.append((f"m/44'/60'/0'/{i}", [44+H, 60+H, 0+H, i]))
PATHS.append(("m/44'/60'/0'", [44+H, 60+H, 0+H]))
for i in range(3):                       # bare non-hardened
    PATHS.append((f"m/{i}", [i]))
PATHS.append(("m", []))

TARGET = O.WINNER.lower()


def _build_tree(paths):
    """nested dict: index -> (subtree, [labels terminating here])"""
    root = [{}, []]
    for label, p in paths:
        node = root
        for step in p:
            node = node[0].setdefault(step, [{}, []])
        node[1].append(label)
    return root


TREE = _build_tree(PATHS)


def _walk(node, k, c, out):
    for lab in node[1]:
        out.append((lab, k))
    for step, child in node[0].items():
        k2, c2 = O._ckd_priv(k, c, step)
        _walk(child, k2, c2, out)


def addrs_for_seed(seed):
    I = O.hmac.new(b"Bitcoin seed", seed, O.hashlib.sha512).digest()
    out = []
    _walk(TREE, I[:32], I[32:], out)
    return out


def check_phrase(words):
    seed = O.mnemonic_to_seed(" ".join(words))
    for lab, priv in addrs_for_seed(seed):
        if O.eth_address(priv).lower() == TARGET:
            return lab
    return None


PROG = 'pathcross_progress.txt'


def work(task):
    oi, first = task
    order = ORD[oi]
    others = [CAND[h] for h in range(2, 13)]
    n = 0; hits = []
    for rest in itertools.product(*others):
        d = {1: first}
        for i, h in enumerate(range(2, 13)):
            d[h] = rest[i]
        words = [d[h] for h in order]
        n += 1
        lab = check_phrase(words)
        if lab:
            hits.append((words, lab))
            print('!!!! MATCH', words, lab, flush=True)
            open('MOSS_HIT_PATH.txt', 'w').write(json.dumps({'words': words, 'path': lab}))
    return task, n, hits


if __name__ == '__main__':
    if '--bench' in sys.argv:
        t0 = time.time(); n = 300
        ws = [CAND[h][0] for h in range(1, 13)]
        for _ in range(n):
            check_phrase(ws)
        dt = time.time() - t0
        print(f'{len(PATHS)} paths; {n/dt:.1f} phrases/s/core -> {n/dt*4:.0f}/s on 4 cores')
        tot = 531441 * len(ORD)
        print(f'full job {tot} phrases = {tot/(n/dt*4)/3600:.1f} h')
        sys.exit()
    done = set()
    if os.path.exists(PROG):
        for ln in open(PROG):
            if ln.startswith('DONE '): done.add(ln.split()[1])
    for h in range(1, 13): print(h, CAND[h])
    print('paths', len(PATHS), 'orderings', len(ORD), flush=True)
    # run the most plausible clock readings first: 1->12 and 12->1, both
    # directions, then the two reading-order variants, then the rotations.
    PRIO = [0, 1, 22, 23, 24, 25, 26, 27]
    tasks = [(oi, f) for oi in range(len(ORD)) for f in CAND[1]]
    tasks.sort(key=lambda t: (PRIO.index(t[0]) if t[0] in PRIO else 99, t[0]))
    tasks = [t for t in tasks if f'{t[0]}|{t[1]}' not in done]
    print('tasks', len(tasks), '(%d already done)' % len(done), flush=True)
    t0 = time.time(); g = 0
    with Pool(4) as p:
        for key, n, hits in p.imap_unordered(work, tasks):
            g += n
            with open(PROG, 'a') as fh:
                fh.write(f'DONE {key[0]}|{key[1]} checked={n} cum={g} t={time.time()-t0:.0f}\n')
            if hits:
                print('SOLVED', hits, flush=True); break
    print('tested', g, 'phrases x', len(PATHS), 'paths; elapsed', time.time() - t0, flush=True)
