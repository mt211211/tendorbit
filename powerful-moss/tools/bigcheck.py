"""Focused cross of everything cheap around the visually-read phrase.

readings (h10 x h11 alternates) x 34 orderings (incl. album-track permutations)
x {raw, checksum-repaired} x passphrases x 18 derivation paths.
Small enough to be exhaustive, and it covers combinations no previous sweep did.
"""
import json, time
import moss_oracle as O
import csrepair as C
import pathcross as P
from orderlib import ORDERS, TRACKS

BASE = {1:'mandate', 2:'oyster', 3:'romance', 4:'strategy', 5:'turtle',
        6:'vintage', 7:'tuition', 8:'stick', 9:'riot', 12:'leisure'}
H10 = ['outer', 'outdoor', 'okay', 'old']
H11 = ['main', 'maze', 'meadow', 'major', 'mind']
PASS = ['', 'powerfulmoss', 'PowerfulMoss', 'Powerful Moss', 'powerful moss',
        'POWERFULMOSS', 'logicbeach', 'LogicBeach', 'LOGIC BEACH',
        'logicbeach.eth', 'moss', 'Moss', 'DKC2', 'dkc2', 'bifurcations',
        'PM', 'powerfulmoss.eth'] + TRACKS
TARGET = P.TARGET


def test(words, pw):
    seed = O.mnemonic_to_seed(" ".join(words), pw)
    for lab, priv in P.addrs_for_seed(seed):
        if O.eth_address(priv).lower() == TARGET:
            return lab
    return None


if __name__ == '__main__':
    t0 = time.time(); n = 0; hits = []
    for w10 in H10:
        for w11 in H11:
            d = dict(BASE); d[10] = w10; d[11] = w11
            for oname, o in ORDERS.items():
                words = [d[h] for h in o]
                for tag, cand in (('raw', words), ('repair', C.repair(words))):
                    for pw in PASS:
                        n += 1
                        lab = test(cand, pw)
                        if lab:
                            hits.append((cand, lab, pw, oname, tag))
                            print('!!!! MATCH', ' '.join(cand), '| path', lab,
                                  '| passphrase', repr(pw), '|', oname, tag,
                                  flush=True)
                            open('MOSS_HIT_BIG.txt', 'w').write(json.dumps(
                                {'words': cand, 'path': lab, 'pass': pw,
                                 'order': oname, 'mode': tag}))
    print(f'tested {n} phrase/passphrase pairs x {len(P.PATHS)} paths '
          f'= {n*len(P.PATHS)} derivations in {time.time()-t0:.0f}s')
    print('hits:', hits)
