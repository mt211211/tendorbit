import hashlib, hmac
import coincurve
from Crypto.Hash import keccak
from mnemonic import Mnemonic

_M = Mnemonic("english")
WORDS = _M.wordlist
WIDX = {w:i for i,w in enumerate(WORDS)}
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
WINNER = "0x635739254bde27d28301f25ad57c3cac3c3468f3"

def kec(b):
    k=keccak.new(digest_bits=256); k.update(b); return k.digest()

def valid_checksum(words):
    # words: list of 12 valid wordlist words -> True if BIP39 checksum ok
    idxs = [WIDX[w] for w in words]
    bits = 0
    for i in idxs: bits = (bits<<11)|i
    # 12 words -> 132 bits = 128 entropy + 4 checksum
    ent = bits >> 4
    cs = bits & 0xF
    entb = ent.to_bytes(16,"big")
    h = hashlib.sha256(entb).digest()[0]
    return (h>>4) == cs

def mnemonic_to_seed(mn, passphrase=""):
    return hashlib.pbkdf2_hmac("sha512", mn.encode("utf-8"), ("mnemonic"+passphrase).encode("utf-8"), 2048, 64)

def _ckd_priv(k, c, index):
    if index & 0x80000000:
        data = b"\x00" + k + index.to_bytes(4,"big")
    else:
        P = coincurve.PublicKey.from_valid_secret(k).format(compressed=True)
        data = P + index.to_bytes(4,"big")
    I = hmac.new(c, data, hashlib.sha512).digest()
    IL, IR = I[:32], I[32:]
    ki = (int.from_bytes(IL,"big") + int.from_bytes(k,"big")) % N
    return ki.to_bytes(32,"big"), IR

def derive(seed, path):
    I = hmac.new(b"Bitcoin seed", seed, hashlib.sha512).digest()
    k, c = I[:32], I[32:]
    for idx in path:
        k, c = _ckd_priv(k, c, idx)
    return k

def eth_address(priv32):
    pub = coincurve.PublicKey.from_valid_secret(priv32).format(compressed=False)[1:]
    return "0x"+kec(pub)[-20:].hex()

H = 0x80000000
def path_addr(words, account=0, index=0, coin=60):
    seed = mnemonic_to_seed(" ".join(words))
    path = [44+H, coin+H, account+H, 0, index]
    return eth_address(derive(seed, path))

def check(words, target=WINNER, sweep=True):
    """words: list of 12 wordlist words. Returns (path_str,address) if match else None."""
    if len(words)!=12: return None
    if any(w not in WIDX for w in words): return None
    if not valid_checksum(words): return None
    seed = mnemonic_to_seed(" ".join(words))
    accounts = range(3) if sweep else range(1)
    indexes = range(3) if sweep else range(1)
    for a in accounts:
        for i in indexes:
            addr = eth_address(derive(seed, [44+H,60+H,a+H,0,i]))
            if addr.lower()==target.lower():
                return (f"m/44'/60'/{a}'/0/{i}", addr)
    return None

if __name__=="__main__":
    # self-test 1: all-zero entropy vector -> known address
    z = ["abandon"]*11+["about"]
    assert valid_checksum(z), "zero vector checksum"
    got = path_addr(z)
    exp = "0x9858EfFD232B4033E47d90003D41EC34EcaEda94".lower()
    print("zero-vector addr:", got, "== expected:", got.lower()==exp)
    assert got.lower()==exp, "BIP44 ETH derivation mismatch!"
    # positive control: point at zero-vector's own address
    assert check(z, target=got) is not None, "positive control failed"
    # negative control: zero vector should NOT match winner
    assert check(z) is None, "neg control failed"
    print("SELFTEST OK (independent oracle certified against BIP39/BIP44 ETH KAT)")
