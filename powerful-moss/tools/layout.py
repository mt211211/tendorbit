"""Exact global layout model of the wordlist background.

Established: the wordlist is space-joined into one 13116-char stream and HARD
wrapped at exactly 171 characters per line (CPL = 171.01 +/- 0.13 over 23
independent consecutive-row pairs -- far too tight for word wrapping, which
would vary by several chars per line).  So for any character p on physical
row i:

    x(p, i) = A + CW * (p - 171*i)

Fitting A and CW against all 28 identified rows at once gives every row origin
to sub-pixel accuracy, including the 14 rows never identified individually,
and L0 (which virtual line the top of the image shows).
"""
import json
import numpy as np
from mnemonic import Mnemonic
from rankcand import ROW, ROWS

W = Mnemonic('english').wordlist
IDX = {w: i for i, w in enumerate(W)}
COFF = []
_c = 0
for _w in W:
    COFF.append(_c); _c += len(_w) + 1
TOTAL = _c
CPL = 171

rows = sorted(ROW)
c_i = np.array([COFF[IDX[ROW[r][0]]] for r in rows], float)
i_a = np.array(rows, float)
X_a = np.array([ROW[r][1] for r in rows], float)

# X0_i = A + CW*(c_i - 171*i)
M = np.stack([np.ones_like(i_a), c_i - CPL * i_a], axis=1)
sol, *_ = np.linalg.lstsq(M, X_a, rcond=None)
A, CW = sol
pred = M @ sol
resid = X_a - pred
print(f'A={A:.2f}px  CW={CW:.4f}px')
print(f'row-origin residual: rms={np.sqrt((resid**2).mean()):.2f}px '
      f'max={np.abs(resid).max():.2f}px  (vs 2.47/5.97 for per-row fits)')

# which virtual line is physical row 0?
L0s = [int(np.floor(c / CPL)) - r for c, r in zip(c_i, rows)]
vals, cnts = np.unique(L0s, return_counts=True)
L0 = int(vals[np.argmax(cnts)])
print(f'L0 (virtual line shown as physical row 0) = {L0} '
      f'(agreement {cnts.max()}/{len(L0s)})')
print(f'wordlist needs {int(np.ceil(TOTAL/CPL))} lines; image shows '
      f'{len(ROWS)} -> lines {L0}..{L0+len(ROWS)-1}')
first_char, last_char = CPL * L0, CPL * (L0 + len(ROWS))
fw = max(j for j in range(len(W)) if COFF[j] <= first_char)
lw = max(j for j in range(len(W)) if COFF[j] <= min(last_char, TOTAL - 1))
print(f'visible character range {first_char}..{last_char} '
      f'-> words "{W[fw]}" .. "{W[lw]}"')


def x_of(word_or_char, rowi):
    p = COFF[IDX[word_or_char]] if isinstance(word_or_char, str) else word_or_char
    return A + CW * (p - CPL * rowi)


def row_of_word(j):
    """physical row index of word j under the global model."""
    return int(np.floor(COFF[j] / CPL)) - L0


def spans_model(ri):
    """(word, x0, x1) for every word with ink on physical row ri."""
    out = []
    lo, hi = CPL * (ri + L0), CPL * (ri + L0 + 1)
    for j, w in enumerate(W):
        a, b = COFF[j], COFF[j] + len(w)
        if b < lo or a > hi:
            continue
        out.append((w, x_of(a, ri), x_of(b, ri)))
    return out


if __name__ == '__main__':
    json.dump({'A': float(A), 'CW': float(CW), 'CPL': CPL, 'L0': L0},
              open('layout.json', 'w'), indent=1)
    print('\nwrote layout.json')
    print('\ncheck: model rows vs the rows identified by letter-count matching')
    bad = 0
    for r in rows:
        sw = ROW[r][0]
        mr = row_of_word(IDX[sw])
        flag = '' if mr == r else '   <-- MISMATCH'
        if mr != r:
            bad += 1
        print(f'  row {r:>3}: starts "{sw}" ; model puts it on row {mr}{flag}')
    print(f'{len(rows)-bad}/{len(rows)} rows agree')
