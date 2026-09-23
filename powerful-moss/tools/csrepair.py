"""Checksum-repair mechanism.

A 12-word phrase is 132 bits = 128 entropy + 4 checksum.  A hand-marked
phrase is checksum-valid only 1 time in 16, and all four of the visually
certain readings are invalid -- so the author cannot have marked 12 words
and funded that phrase directly.  The standard fix (what Ian Coleman's BIP39
tool and most "fix checksum" utilities do) is to keep the 128 entropy bits
and recompute the checksum, which changes ONLY the final word.

Variants tested here:
  repair_last : ent = bits >> 4, recompute cs  -> last word replaced
  repair_first: treat the 132 bits as 128 entropy taken from the TOP,
                i.e. drop the last 4 bits of the final word (same as above)
                but also the variant where entropy is the first 128 bits of
                the byte string (identical) -- kept for clarity
  raw         : the phrase as marked, unrepaired (control)
"""
import hashlib
from mnemonic import Mnemonic

_M = Mnemonic('english')
W = _M.wordlist
IDX = {w: i for i, w in enumerate(W)}


def bits_of(words):
    b = 0
    for w in words:
        b = (b << 11) | IDX[w]
    return b


def words_of(bits132):
    return [W[(bits132 >> (11 * (11 - i))) & 0x7FF] for i in range(12)]


def repair(words):
    """Keep the 128 entropy bits, recompute the 4-bit checksum."""
    ent = bits_of(words) >> 4
    cs = hashlib.sha256(ent.to_bytes(16, 'big')).digest()[0] >> 4
    return words_of((ent << 4) | cs)


def entropy_hex(words):
    return (bits_of(words) >> 4).to_bytes(16, 'big').hex()
