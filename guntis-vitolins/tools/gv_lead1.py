"""Guntis Vitolins -- lead 1: the RO1 model extended with on-screen video words.

Lead 1 of that folder found the real blocking gap: 122 BIP-0039 words are legible
on screen in the challenge video and 109 of them appear in NO written surface, so
the word pool every sweep drew from was incomplete. The five that match the
portfolio-table prediction are atom, link, basic, token, dash. The folder calls
"the RO1 model extended with the five coin words as free video words" the natural
next sweep.

MODEL
  Exactly one of the four free VIDEO slots is filled by a coin word, at any of
  the four positions; the remaining video slots are filled from the written pool
  in reading order, exactly as RO1 does. On-screen text has no reading-order
  position, so a coin word is free to sit anywhere -- that is what "free video
  word" means and it is why this is not simply RO1 with a longer list.

  Everything else is the folder's own: anchors dutch@1 fog@5 parrot@12, the
  layout/fork-slot logic, the post-side reading order, the BIP39 checksum filter,
  and scan_unit itself. Only `vsets` is replaced.

SIZE (closed form, checked by --selftest)
  shape (2,2): coin in a pre slot  C(2,1)*5*C(25,1)*C(2,2) =    250
               coin in a mid slot  C(2,1)*5*C(25,2)*C(2,1) =  6,000   -> 6,250
  shape (3,1): coin in a pre slot  C(3,1)*5*C(25,2)*C(2,1) =  9,000
               coin in a mid slot  C(1,1)*5*C(25,3)*C(2,0) = 11,500   -> 20,500
  video pairs  = 6,250*45 + 20,500*6                       = 404,250
  arrangements = 404,250 * C(18,3) * 5                     = 1,649,340,000
  derivations at 1 in 16                                   ~ 103,083,750
"""
import itertools, math, os, sys, time

HERE = ('/tmp/claude-0/-home-user-tendorbit/5dbf252a-6161-5f73-beaf-adcafb3d494f/'
        'scratchpad/ocp/1-big-prizes/guntis-vitolins-metamask-8-6eth')
SCRATCH = ('/tmp/claude-0/-home-user-tendorbit/5dbf252a-6161-5f73-beaf-adcafb3d494f/'
           'scratchpad')
sys.path.insert(0, os.path.join(HERE, 'tools'))
sys.path.insert(0, SCRATCH)

from multiprocessing import Pool
import sweep_reading_order as SRT
import moss_oracle as O
import pathcross as P
import gv_multipath as MP          # reuses the certified derive + recheck

COINS = ['atom', 'link', 'basic', 'token', 'dash']
LOG = os.path.join(SCRATCH, 'gv_lead1.tsv')
HIT = os.path.join(SCRATCH, 'GV_LEAD1_HIT.txt')
TARGET = SRT.TARGET_ADDRESS


def coin_vsets(pre, mid, index_of):
    """RO1's video rows, but with exactly one coin word at a free position."""
    coin_i = [index_of[c] for c in COINS if c in index_of]
    out = {}
    for (k, m) in SRT.shapes():
        rows = []
        for ci in coin_i:
            # coin occupies one of the k pre slots
            for p in range(k):
                for a in itertools.combinations(pre, k - 1):
                    ai = [index_of[w] for w in a]
                    head = ai[:p] + [ci] + ai[p:]
                    for b in itertools.combinations(mid, m):
                        rows.append(tuple(head + [index_of[w] for w in b]))
            # coin occupies one of the m mid slots
            for p in range(m):
                for a in itertools.combinations(pre, k):
                    ai = [index_of[w] for w in a]
                    for b in itertools.combinations(mid, m - 1):
                        bi = [index_of[w] for w in b]
                        tail = bi[:p] + [ci] + bi[p:]
                        rows.append(tuple(ai + tail))
        out[(k, m)] = rows
    return out


def setup():
    words, index_of = SRT.load_wordlist(MP.WORDLIST)
    pre, mid, free, order = SRT.load_pool(MP.POOL)
    lay = SRT.build_layouts()
    vsets = coin_vsets(pre, mid, index_of)
    units = list(itertools.combinations(free, 3))
    return words, index_of, lay, vsets, order, units


_G = None


def _init():
    global _G
    _G = setup()


def work(idx):
    words, index_of, lay, vsets, order, units = _G
    t0 = time.time()
    n, d, hit, w = SRT.scan_unit(units[idx], None, index_of, words, lay, vsets,
                                 order, MP.make_derive(TARGET), TARGET)
    return idx, n, d, hit, w, time.time() - t0


def selftest():
    c = math.comb
    print('SELFTEST')
    words, index_of, lay, vsets, order, units = setup()
    exp = {(2, 2): c(2,1)*5*c(25,1)*c(2,2) + c(2,1)*5*c(25,2)*c(2,1),
           (3, 1): c(3,1)*5*c(25,2)*c(2,1) + c(1,1)*5*c(25,3)*c(2,0)}
    ok = True
    for sh, rows in vsets.items():
        e = exp.get(sh)
        got = len(rows)
        print(f'  shape {sh}: {got:,} rows (closed form {e:,}) '
              f'{"OK" if got == e else "FAIL"}')
        ok &= (got == e)
    vpairs = len(vsets[(2,2)])*c(3,2)*c(6,2) + len(vsets[(3,1)])*c(3,3)*c(6,1)
    arr = vpairs * len(units) * 5
    print(f'  video pairs {vpairs:,}  arrangements {arr:,}  '
          f'derivations ~{arr//16:,}')
    assert ok
    # every row must contain exactly one coin word
    ci = {index_of[x] for x in COINS}
    bad = sum(1 for sh in vsets for r in vsets[sh] if len(set(r) & ci) != 1)
    print(f'  rows with exactly one coin word: {"OK" if bad == 0 else f"FAIL ({bad})"}')
    assert bad == 0
    # planted witness inside THIS space, at a non-default path
    probe = {}
    def pd(mn):
        probe.setdefault('first', mn)
        return '0x' + '0'*40
    SRT.scan_unit(units[0], None, index_of, words, lay, vsets, order, pd, 'x'*42)
    mn = probe['first']
    assert any(w in mn.split() for w in COINS), 'planted phrase has no coin word'
    seed = O.mnemonic_to_seed(mn)
    out = []
    P._walk(MP.TREE, *MP._master(seed), out)
    lab, priv = [t for t in out if t[0] == "m/44'/60'/2'/0/0"][0]
    planted = O.eth_address(priv).lower()
    MP._RECHECK_TARGET[0] = planted
    n, d, hit, w = SRT.scan_unit(units[0], None, index_of, words, lay, vsets,
                                 order, MP.make_derive(planted), planted)
    print(f'  planted in-space phrase (contains a coin word) at {lab}: '
          f'{"OK" if hit == mn else "FAIL"} (witness {w})')
    assert hit == mn
    MP._RECHECK_TARGET[0] = TARGET
    print('SELFTEST OK')


if __name__ == '__main__':
    if '--selftest' in sys.argv:
        selftest(); sys.exit(0)
    words, index_of, lay, vsets, order, units = setup()
    done = set()
    if os.path.exists(LOG):
        for line in open(LOG):
            c0 = line.rstrip('\n').split('\t')
            if len(c0) > 1 and c0[0] != 'unit':
                done.add(int(c0[0]))
        print(f'resuming: {len(done)} of {len(units)} units logged')
    new = not os.path.exists(LOG)
    log = open(LOG, 'a')
    if new:
        log.write('unit\tarrangements\tderivations\twitness\tseconds\n'); log.flush()
    todo = [i for i in range(len(units)) if i not in done]
    print(f'{len(todo)} units, {len(P.PATHS)} paths each', flush=True)
    t0 = time.time(); tn = td = 0; k = 0
    with Pool(4, initializer=_init) as pool:
        for idx, n, d, hit, w, secs in pool.imap_unordered(work, todo):
            tn += n; td += d; k += 1
            log.write(f'{idx}\t{n}\t{d}\t{w}\t{secs:.1f}\n'); log.flush()
            el = time.time() - t0
            if k % 20 == 0 or hit:
                pct = 100.0 * k / max(1, len(todo))
                eta = (el / k) * (len(todo) - k) / 3600
                print(f'  {k}/{len(todo)} units ({pct:.1f}%) | derivations {td:,} '
                      f'| {td/el:.0f}/s | {el/3600:.2f} h elapsed | ETA {eta:.2f} h',
                      flush=True)
            if hit:
                open(HIT, 'w').write(hit + '\n')
                print('MATCH FOUND. Written to', HIT, '-- not printed.', flush=True)
                break
    log.close()
    el = time.time() - t0
    print(f'\narrangements {tn:,}  derivations {td:,}  '
          f'{td/el if el else 0:.0f}/s  elapsed {el/3600:.2f} h')
