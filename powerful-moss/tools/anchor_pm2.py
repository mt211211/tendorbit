"""Anchors are not independent evidence - they come from the same centroid rule.
Test: exactly one anchor (h4/h8/h12) misread by up to +/-2 rows, all other hours at +/-1.
All 30 orderings, no checksum filter."""
import itertools, json, os, time
from multiprocessing import Pool
from mnemonic import Mnemonic
import moss_oracle as O
W=Mnemonic('english').wordlist; idx={w:i for i,w in enumerate(W)}
CW=25.46
exec(open('sweep_pm2.py').read().split("CENTER=")[0].split("CW=25.46")[1])  # ROW dict
CENTER={1:5,2:12,3:21,4:29,5:35,6:38,7:35,8:29,9:21,10:12,11:5,12:3}
PCX=json.load(open('numcentroid.json'))
def spans(ri):
    if ri not in ROW: return []
    sw,X0=ROW[ri]; s=idx[sw]; out=[];c=0
    for k in range(70):
        i=s+k
        if i>=len(W): break
        x0=X0+CW*c; x1=x0+CW*len(W[i])
        if x0>2150: break
        out.append((W[i],x0,x1)); c+=len(W[i])+1
    return out
def nearest(ri,cx):
    sp=spans(ri)
    if not sp: return None
    def d(t):
        w,a,b=t
        return 0 if a<=cx<=b else (a-cx if a>cx else cx-b)
    return sorted(sp,key=d)[0][0]
def cands(h,K):
    cx=PCX[str(h)]['pcx']; c0=CENTER[h]; out=[]
    order=(0,-1,1) if K==1 else (0,-1,1,-2,2)
    for dr in order:
        w=nearest(c0+dr,cx)
        if w and w not in out: out.append(w)
    return out
READ=[12,11,1,10,2,9,3,8,4,7,5,6]; COL=[9,8,10,7,11,6,12,1,5,2,4,3]
ORD=[]
for st in range(1,13):
    ORD.append([((st-1+k)%12)+1 for k in range(12)])
    ORD.append([((st-1-k)%12)+1 for k in range(12)])
ORD += [READ, READ[::-1], COL, COL[::-1]]
TARGET=O.WINNER.lower()
ANCH=[4,8,12]
def work(task):
    """anchor h gets its +/-2 alternates; every other hour gets +/-1.
    Split by the fixed word chosen for hour 1 so all cores are used."""
    anchor,first=task
    CAND={}
    for h in range(1,13):
        CAND[h]=cands(h,2) if h==anchor else cands(h,1)
    CAND[1]=[first]
    n=0;hits=[]
    keys=list(range(1,13))
    for combo in itertools.product(*[CAND[h] for h in keys]):
        d=dict(zip(keys,combo))
        vals=[d[h] for h in range(1,13)]
        for words in [[d[h] for h in o] for o in ORD]+[sorted(vals),sorted(vals,reverse=True)]:
            n+=1
            seed=O.mnemonic_to_seed(" ".join(words))
            if O.eth_address(O.derive(seed,[44+O.H,60+O.H,0+O.H,0,0])).lower()==TARGET:
                hits.append(words); print('!!!! MATCH',words,flush=True)
                open('MOSS_HIT_ANCH.txt','w').write(json.dumps(words))
    return (anchor,first),n,hits
PROG='anchor_progress.txt'
if __name__=='__main__':
    done=set()
    if os.path.exists(PROG):
        for ln in open(PROG):
            if ln.startswith('DONE '): done.add(ln.split()[1])
    for a in ANCH: print('anchor',a,'->',cands(a,2))
    tasks=[(a,f) for a in ANCH for f in cands(1,1)]
    tasks=[t for t in tasks if f'{t[0]}|{t[1]}' not in done]
    print('tasks',len(tasks),'(resuming, %d already done)'%len(done),flush=True)
    t0=time.time(); g=0
    with Pool(4) as p:
        for key,n,hits in p.imap_unordered(work,tasks):
            g+=n
            with open(PROG,'a') as fh: fh.write(f'DONE {key[0]}|{key[1]} checked={n} cum={g} t={time.time()-t0:.0f}\n')
            print(f'task {key} done checked={n} cum={g} t={time.time()-t0:.0f}',flush=True)
            if hits: print('SOLVED',hits,flush=True); break
    print('tested',g,'elapsed',time.time()-t0,flush=True)
