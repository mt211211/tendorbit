"""Global consistency test of the layout, and sub-pixel refinement.

If the wordlist is ONE continuous monospace flow wrapped at a constant
characters-per-line CPL on a wide virtual canvas, then for every row i whose
first visible word is index s_i:

    X0_i = margin + CW * c(s_i) - CW * CPL * i

where c(s) is the character offset of word s in the space-joined wordlist.
Fitting margin and CPL (and CW) against all 28 independently measured rows is
a strong global check: 28 measurements, 3 unknowns.  A good fit also lets us
recompute every row origin from the model, which is more accurate than each
row's individual fit, and predict the rows never identified.
"""
import json
import numpy as np
from mnemonic import Mnemonic
from rankcand import ROW

W = Mnemonic('english').wordlist
idx = {w: i for i, w in enumerate(W)}

# character offset of each word in the space-joined wordlist
coff = []
c = 0
for w in W:
    coff.append(c)
    c += len(w) + 1

rows = sorted(ROW)
i_arr = np.array(rows, float)
s_arr = np.array([coff[idx[ROW[r][0]]] for r in rows], float)
X_arr = np.array([ROW[r][1] for r in rows], float)

# X0 = margin + CW*s - CW*CPL*i   -> linear in (margin, CW, CW*CPL)
A = np.stack([np.ones_like(i_arr), s_arr, -i_arr], axis=1)
sol, res, rank, sv = np.linalg.lstsq(A, X_arr, rcond=None)
margin, CW_fit, CWCPL = sol
CPL = CWCPL / CW_fit
pred = A @ sol
resid = X_arr - pred

print(f'fitted: margin={margin:.2f}px  CW={CW_fit:.4f}px  CPL={CPL:.4f} chars/line')
print(f'        CW*CPL = {CWCPL:.2f}px = virtual line advance')
print(f'residual: rms={np.sqrt((resid**2).mean()):.2f}px  max={np.abs(resid).max():.2f}px')
print()
print(f"{'row':>4} {'startword':<10} {'X0_meas':>9} {'X0_model':>9} {'resid':>7}")
for k, r in enumerate(rows):
    print(f'{r:>4} {ROW[r][0]:<10} {X_arr[k]:>9.1f} {pred[k]:>9.1f} {resid[k]:>+7.2f}')

if np.abs(resid).max() < 6:
    print('\nLayout is ONE continuous flow -- model confirmed globally.')
    model = {'margin': float(margin), 'CW': float(CW_fit), 'CPL': float(CPL)}
    json.dump(model, open('flowmodel.json', 'w'), indent=1)
    print('wrote flowmodel.json')
else:
    print('\nNo single continuous flow fits; layout is not a plain constant-CPL wrap.')
