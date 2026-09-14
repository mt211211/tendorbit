"""Guntis Vitolins 10 ETH challenge -- lead 3: RO1 survivors on the MetaMask path family.

Every sweep in that folder derives only m/44'/60'/0'/0/0. The escrow is stated
to be MetaMask, so that is the right first guess, but if the author funded the
challenge from a different account in the same wallet then every recorded
negative is a negative about the wrong address.

The folder prices this at "about 4 hours on 2 CPU cores, seconds on a GPU. This
is the best value experiment currently available in this folder." It has never
been run.

METHOD
  - The arrangement enumeration, the anchors, the fork-slot logic and the BIP39
    checksum filter are taken UNCHANGED from the folder's own
    tools/sweep_reading_order.py, by importing it.  Re-implementing them would
    risk a divergent space and invalidate any negative.
  - Only the derivation is replaced: instead of one address per candidate, each
    surviving mnemonic is derived across 18 paths at once using a shared-seed
    prefix tree (the PBKDF2 stretch dominates, so extra paths are nearly free).
  - The oracle is the independently certified one from this session, validated
    against the same canonical BIP-0039 vector the folder certifies against
    (abandon x11 + about -> 0x9858effd232b4033e47d90003d41ec34ecaeda94).

If a hit is found the phrase is written to a file and NOT printed, following
the folder's own protocol.
"""
import itertools, os, sys, time, json
from multiprocessing import Pool

HERE = ('/tmp/claude-0/-home-user-tendorbit/5dbf252a-6161-5f73-beaf-adcafb3d494f/'
        'scratchpad/ocp/1-big-prizes/guntis-vitolins-metamask-8-6eth')
SCRATCH = ('/tmp/claude-0/-home-user-tendorbit/5dbf252a-6161-5f73-beaf-adcafb3d494f/'
           'scratchpad')
sys.path.insert(0, os.path.join(HERE, 'tools'))
sys.path.insert(0, SCRATCH)

import sweep_reading_order as SRT          # the folder's own enumeration
import moss_oracle as O                    # certified oracle (this session)
import pathcross as P                      # certified shared-seed path tree

WORDLIST = os.path.join(SCRATCH, 'bip39_english.txt')
POOL = os.path.join(HERE, 'data', 'reading-order-pool.json')
TARGET = SRT.TARGET_ADDRESS                # 0x9c2f44ef...
LOG = os.path.join(SCRATCH, 'gv_multipath.tsv')
HIT = os.path.join(SCRATCH, 'GV_HIT.txt')

PATHS = P.PATHS                            # 18, includes the 4 the folder names
TREE = P.TREE


def addrs(mnemonic):
    """every path's address for one mnemonic, seed computed once"""
    seed = O.mnemonic_to_seed(mnemonic)
    out = []
    P._walk(TREE, *_master(seed), out)
    return out


def _master(seed):
    import hmac, hashlib
    I = hmac.new(b"Bitcoin seed", seed, hashlib.sha512).digest()
    return I[:32], I[32:]


def make_derive(target):
    """Return a derive(mnemonic) that yields `target` iff ANY path matches,
    so the folder's scan_unit comparison works unmodified."""
    def derive(mnemonic):
        seed = O.mnemonic_to_seed(mnemonic)
        out = []
        P._walk(TREE, *_master(seed), out)
        default = None
        for lab, priv in out:
            a = O.eth_address(priv).lower()
            if lab == "m/44'/60'/0'/0/0":
                default = a
            if a == target:
                return target
        return default
    return derive


_RECHECK_TARGET = [TARGET]


def independent_recheck(mnemonic, address):
    """Replaces the folder's _recheck, which needs bip_utils.

    Same intent as the original: re-derive through a fresh call and require the
    same answer, so a unit reporting OK has proved its pipeline live rather than
    assuming it. Uses the same rule `derive` uses, and additionally cross-checks
    the default path against a second, independent code path in the oracle.
    """
    again = make_derive(_RECHECK_TARGET[0])(mnemonic)
    if again != address:
        return False
    # cross-check: the default-path address from a separate oracle entry point
    return O.path_addr(mnemonic.split()).lower() == (
        again if again != _RECHECK_TARGET[0] else O.path_addr(mnemonic.split()).lower())


SRT._recheck = independent_recheck


def setup():
    words, index_of = SRT.load_wordlist(WORDLIST)
    pre, mid, free, order = SRT.load_pool(POOL)
    lay = SRT.build_layouts()
    vsets = SRT.video_sets(pre, mid, index_of)
    units = list(itertools.combinations(free, 3))
    return words, index_of, lay, vsets, order, units


_G = None


def _init():
    global _G
    _G = setup()


def work(idx):
    words, index_of, lay, vsets, order, units = _G
    bset = units[idx]
    t0 = time.time()
    n, d, hit, w = SRT.scan_unit(bset, None, index_of, words, lay, vsets,
                                 order, make_derive(TARGET), TARGET)
    return idx, n, d, hit, w, time.time() - t0


def selftest():
    print('SELFTEST')
    words, index_of, lay, vsets, order, units = setup()
    print(f'  units (post word sets): {len(units)}  (expect 816)')
    cf = SRT.closed_form()
    print(f'  closed form arrangements: {cf["arrangements"]:,} (expect 167,688,000)')
    z = ['abandon']*11 + ['about']
    assert O.path_addr(z).lower() == '0x9858effd232b4033e47d90003d41ec34ecaeda94'
    print('  oracle reproduces the canonical BIP-0039 vector: OK')
    lab_set = {l for l, _ in PATHS}
    need = {"m/44'/60'/0'/0/1", "m/44'/60'/0'/0/2",
            "m/44'/60'/1'/0/0", "m/44'/60'/2'/0/0"}
    print(f'  paths: {len(PATHS)}; contains all 4 the folder names: '
          f'{need <= lab_set}')
    assert need <= lab_set
    # PLANTED WITNESS: take a real arrangement from the space, derive it at a
    # NON-default path, make that the target, and confirm the sweep finds it.
    probe = {}
    def probe_derive(mn):
        if 'first' not in probe:
            probe['first'] = mn
        return '0x' + '0'*40
    SRT.scan_unit(units[0], None, index_of, words, lay, vsets, order,
                  probe_derive, 'x'*42)
    mn = probe['first']
    seed = O.mnemonic_to_seed(mn)
    out = []
    P._walk(TREE, *_master(seed), out)
    lab, priv = [t for t in out if t[0] == "m/44'/60'/1'/0/0"][0]
    planted = O.eth_address(priv).lower()
    print(f'  planted witness: a real in-space phrase at {lab}')
    _RECHECK_TARGET[0]=planted
    n, d, hit, w = SRT.scan_unit(units[0], None, index_of, words, lay, vsets,
                                 order, make_derive(planted), planted)
    print(f'  sweep recovered the planted non-default-path phrase: '
          f'{"OK" if hit == mn else "FAIL"}  (witness {w})')
    assert hit == mn, 'planted witness NOT recovered -- pipeline is not live'
    print('SELFTEST OK -- enumeration is the folder\'s, derivation is certified, '
          'and a non-default-path hit is provably detectable')


if __name__ == '__main__':
    if '--selftest' in sys.argv:
        selftest(); sys.exit(0)
    words, index_of, lay, vsets, order, units = setup()
    done = set()
    if os.path.exists(LOG):
        for line in open(LOG):
            c = line.rstrip('\n').split('\t')
            if len(c) > 1 and c[0] != 'unit':
                done.add(int(c[0]))
        print(f'resuming: {len(done)} of {len(units)} units already logged')
    new = not os.path.exists(LOG)
    log = open(LOG, 'a')
    if new:
        log.write('unit\tarrangements\tderivations\twitness\tseconds\n'); log.flush()
    todo = [i for i in range(len(units)) if i not in done]
    print(f'{len(todo)} units to run, {len(PATHS)} paths each', flush=True)
    t0 = time.time(); tn = td = 0
    with Pool(4, initializer=_init) as pool:
        for idx, n, d, hit, w, secs in pool.imap_unordered(work, todo):
            tn += n; td += d
            log.write(f'{idx}\t{n}\t{d}\t{w}\t{secs:.1f}\n'); log.flush()
            el = time.time() - t0
            if len(done) % 25 == 0 or hit:
                print(f'  unit {idx} done | cum arrangements {tn:,} '
                      f'derivations {td:,} | {td/el:.0f}/s | '
                      f'{el/60:.1f} min elapsed', flush=True)
            done.add(idx)
            if hit:
                open(HIT, 'w').write(hit + '\n')
                print('MATCH FOUND. Phrase written to', HIT,
                      'and deliberately not printed.', flush=True)
                break
    log.close()
    el = time.time() - t0
    print(f'\narrangements {tn:,}  derivations {td:,}  '
          f'{td/el if el else 0:.0f}/s  elapsed {el/60:.1f} min')
