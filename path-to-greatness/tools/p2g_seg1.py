"""Segment 1 of Path to Greatness with `imagine` pinned to a few readings.

The folder crossed every 8-digit block written twice (10^8) with ~13,000 hand-built
readings of the clue 6 melody.  If `imagine` is one specific value, each `beach` guess
costs a single AES block instead of 10^8, so the melody side can be searched generically:

  G1  each of the 6 pitch classes gets its own digit (injective, 10P6 = 151,200 maps),
      octaves ignored, and exactly one extra character is inserted at any of 16 positions.

Check is identical to tools/oracle.py segment_oracle: AES-256-CBC, IV few_n_far_btween,
plaintext must end in eight 0x08 bytes (false-positive rate 2^-64).

A planted witness (a real G1 string encrypted under a real imagine candidate) must be
re-found or the run does not count.  A hit is written to a file, never printed in full.
"""
import base64, itertools, os, sys, time
from multiprocessing import Pool
from Crypto.Cipher import AES

IV = b"few_n_far_btween"
CT_REAL = base64.b64decode("I2c6TXU/Z1oCKnEQTWZUvg==")
PAD = bytes(a ^ 8 for a in IV[8:])          # D(C)[8:] must equal IV[8:] ^ 0x08

MELODY = ["A#", "F#", "B", "A#", "F#", "D#", "F", "C#", "B", "C#", "A#", "A#", "F#", "B", "A#"]
CLASSES = ["A#", "F#", "B", "D#", "F", "C#"]
IDX = [CLASSES.index(n) for n in MELODY]
EXTRA = "0123456789#b-.+',x^_*/"


def imagine_candidates():
    import os as _os
    if _os.environ.get("IMAGINE_SET") == "pearl":
        out = []
        for toll in (2403, 2402, 2404, 2390, 2395, 2386, 2388, 2335, 2341, 2345, 2008, 2117, 1177, 68):
            y = str(1941 + toll).zfill(4)
            for s in (y + "07" + "12", y + "12" + "07"):
                out.append(s + s)
        return list(dict.fromkeys(out))
    out = []
    for d in ("08", "09"):                      # 8 Dec (New York) / 9 Dec (UK)
        y, m = "2020", "12"
        for s in (y + d + m, y + m + d, m + d + y, d + m + y):
            out.append(s + s)
    return list(dict.fromkeys(out))


def beach_strings(digits):
    base = "".join(digits[i] for i in IDX)          # 15 chars
    for p in range(16):
        for c in EXTRA:
            yield (base[:p] + c + base[p:]).encode()


def work(args):
    imagines, ct2, perm = args          # ct2 = witness block + real block, one ECB call
    hits = []
    n = 0
    for b in beach_strings(perm):
        for im in imagines:
            n += 1
            d = AES.new(im + b, AES.MODE_ECB).decrypt(ct2)
            if d[8:16] == PAD:
                hits.append(("witness", im, b))
            if d[24:32] == PAD:
                hits.append(("REAL", im, b))
    return n, hits


def run(imagines, ct, label, limit=None):
    perms = itertools.permutations("0123456789", 6)
    if limit:
        perms = itertools.islice(perms, limit)
    t0 = time.time(); total = 0; found = []
    with Pool(4) as pool:
        for n, hits in pool.imap_unordered(work, ((imagines, ct, p) for p in perms), chunksize=64):
            total += n
            found += hits
    return total, found, time.time() - t0


if __name__ == "__main__":
    imag = [s.encode() for s in imagine_candidates()]
    print(f"imagine candidates: {len(imag)}  e.g. {imag[0].decode()}", flush=True)
    wd = ("5", "3", "6", "1", "2", "7")            # D# minor degrees, 6 classes
    wb = list(beach_strings(wd))[16 * 22 // 2 + 7]
    wkey = imag[3] + wb
    wct = AES.new(wkey, AES.MODE_CBC, IV).encrypt(os.urandom(8) + b"\x08" * 8)
    tot, hits, dt = run(imag, wct + CT_REAL, "both")
    ok = any(h == ("witness", imag[3], wb) for h in hits)
    real = [h for h in hits if h[0] == "REAL"]
    print(f"{tot:,} tests in {dt:.0f}s ({tot/dt:,.0f}/s)", flush=True)
    print(f"WITNESS {'OK' if ok else 'FAIL'} (planted mid-space under candidate 4)", flush=True)
    print(f"REAL hits: {len(real)}", flush=True)
    if real:
        with open("P2G_SEG1_HIT.txt", "w") as f:
            for _, im, b in real:
                f.write(f"{im.decode()} {b.decode()}\n")
        print("MATCH -- written to P2G_SEG1_HIT.txt", flush=True)
