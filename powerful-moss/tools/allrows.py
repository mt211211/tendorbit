import numpy as np, json
from mnemonic import Mnemonic
W=Mnemonic('english').wordlist
m=np.load('textmask2.npy'); rows=json.load(open('rows.json'))
CW=25.46

def boxes(ri,gap=16):
    s,e=rows[ri]
    xp=m[s:e+1].sum(axis=0)
    runs=[];inr=False
    for x,v in enumerate(xp):
        if v>0 and not inr: st=x;inr=True
        if v==0 and inr: runs.append((st,x-1));inr=False
    if inr: runs.append((st,len(xp)-1))
    if not runs: return []
    out=[];c,e2=runs[0]
    for A,B in runs[1:]:
        if A-e2<=gap: e2=B
        else: out.append((c,e2));c,e2=A,B
    out.append((c,e2))
    return out

def score(ri,j):
    """align boxes of row ri to wordlist run starting at j; anchor X0 on box1."""
    bx=boxes(ri)
    if len(bx)<4: return None
    # cumulative columns for words j, j+1, ...
    cols=[];c=0
    for k in range(len(bx)+6):
        if j+k>=len(W): return None
        cols.append(c); c+=len(W[j+k])+1
    X0=bx[1][0]-CW*cols[1]
    err=0.0;cnt=0
    for k in range(1,len(bx)):
        if k>=len(cols): break
        pred=X0+CW*cols[k]
        err+=abs(pred-bx[k][0]); cnt+=1
    if cnt<3: return None
    return err/cnt, X0, j

def identify(ri, lo=0, hi=2048):
    best=None
    for j in range(lo,hi):
        s=score(ri,j)
        if s and (best is None or s[0]<best[0]): best=s
    return best

if __name__=='__main__':
    out={}
    for ri in range(len(rows)):
        b=identify(ri)
        if b is None:
            print(ri,'skip (too few boxes)'); continue
        err,X0,j=b
        out[ri]=dict(start=W[j],X0=round(X0,1),err=round(err,2),n=len(boxes(ri)))
        flag='' if err<6 else '   <-- weak'
        print(f'row {ri:2d} y={rows[ri]}  start={W[j]:10s} X0={X0:8.1f} err={err:5.2f} boxes={len(boxes(ri))}{flag}')
    json.dump(out,open('allrows.json','w'))
