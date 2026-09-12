"""Mechanism zoo: keep the reading, vary how the 12 words become a key.

The reading is visually near-certain and "one word wrong anywhere" is now a
16.6M-derivation negative, so the remaining suspect is the derivation itself.
This tries every plausible way 12 words become an Ethereum private key, cheap
enough to be exhaustive over readings x orderings x join styles.

  bip39      standard PBKDF2("mnemonic"+pw), BIP32, 18 paths
  electrum   PBKDF2 salt "electrum" (Electrum's own seed scheme), BIP32
  raw_seed   the phrase bytes used directly as the BIP32 master seed
  brain_*    hash the phrase straight to a secp256k1 key
  ent_*      the 128 entropy bits from the 12 words, padded/hashed to a key
"""
import hashlib, hmac, itertools, json, time
import coincurve
from Crypto.Hash import keccak
import moss_oracle as O
import csrepair as C
import pathcross as P
from orderlib import ORDERS

BASE = {1:'mandate', 2:'oyster', 3:'romance', 4:'strategy', 5:'turtle',
        6:'vintage', 7:'tuition', 8:'stick', 9:'riot', 12:'leisure'}
H10 = ['outer', 'outdoor']
H11 = ['main', 'major', 'maze', 'meadow']
TARGET = bytes.fromhex(O.WINNER[2:])


def kec(b):
    k = keccak.new(digest_bits=256); k.update(b); return k.digest()


def addr(priv):
    try:
        pub = coincurve.PublicKey.from_valid_secret(priv).format(compressed=False)[1:]
    except Exception:
        return None
    return kec(pub)[-20:]


def from_seed(seed):
    """all 18 BIP32 paths off a 64-byte seed"""
    I = hmac.new(b"Bitcoin seed", seed, hashlib.sha512).digest()
    out = []
    P._walk(P.TREE, I[:32], I[32:], out)
    return out


def candidates(words):
    """(label, 32-byte private key) for every mechanism"""
    ph_sp = " ".join(words)
    ph_cc = "".join(words)
    ent = (C.bits_of(words) >> 4).to_bytes(16, 'big')
    out = []
    for jn, ph in (('sp', ph_sp), ('cc', ph_cc)):
        b = ph.encode()
        # seed-based schemes
        for sname, seed in (
            ('bip39', hashlib.pbkdf2_hmac('sha512', b, b'mnemonic', 2048, 64)),
            ('electrum', hashlib.pbkdf2_hmac('sha512', b, b'electrum', 2048, 64)),
            ('raw_seed', hashlib.sha512(b).digest()),
        ):
            for lab, k in from_seed(seed):
                out.append((f'{sname}/{jn}{lab}', k))
        # direct-to-key schemes
        s = hashlib.sha256(b).digest()
        out += [(f'brain_sha256/{jn}', s),
                (f'brain_dsha256/{jn}', hashlib.sha256(s).digest()),
                (f'brain_keccak/{jn}', kec(b)),
                (f'brain_sha3/{jn}', hashlib.sha3_256(b).digest()),
                (f'brain_sha512h/{jn}', hashlib.sha512(b).digest()[:32]),
                (f'brain_blake2b/{jn}', hashlib.blake2b(b, digest_size=32).digest())]
    # entropy-based
    out += [('ent_padL', ent + b'\x00' * 16),
            ('ent_padR', b'\x00' * 16 + ent),
            ('ent_sha256', hashlib.sha256(ent).digest()),
            ('ent_keccak', kec(ent)),
            ('ent_double', ent + ent)]
    return out


if __name__ == '__main__':
    t0 = time.time(); n = 0; hits = []
    reads = []
    for w10 in H10:
        for w11 in H11:
            d = dict(BASE); d[10] = w10; d[11] = w11
            reads.append(d)
    for d in reads:
        for oname, o in ORDERS.items():
            base = [d[h] for h in o]
            for tag, words in (('raw', base), ('repair', C.repair(base))):
                for lab, k in candidates(words):
                    n += 1
                    if addr(k) == TARGET:
                        hits.append((words, lab, oname, tag))
                        print('!!!! MATCH', ' '.join(words), '|', lab, '|',
                              oname, tag, flush=True)
                        open('MOSS_HIT_ZOO.txt', 'w').write(json.dumps(
                            {'words': words, 'mech': lab, 'order': oname,
                             'mode': tag}))
    print(f'{len(reads)} readings x {len(ORDERS)} orderings x 2 modes')
    print(f'tested {n} key derivations across '
          f'{len(candidates(["abandon"]*11+["about"]))} mechanisms '
          f'in {time.time()-t0:.0f}s')
    print('hits:', hits)
