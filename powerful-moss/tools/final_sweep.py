import itertools, json, sys
import numpy as np
from multiprocessing import Pool
from mnemonic import Mnemonic
import moss_oracle as O
W=Mnemonic('english').wordlist; idx={w:i for i,w in enumerate(W)}
CW=25.46
ROW={2:('knife',437.2),3:('left',361.1),4:('live',361.7),5:('maid',256.8),6:('maximum',307.3),
     11:('oil',127.0),12:('other',-20.7),13:('pass',152.0),20:('report',-51.5),21:('ring',-46.1),
     22:('saddle',52.0),28:('spoil',177.5),29:('stereo',4.8),30:('suffer',33.8),34:('track',208.2),
     35:('tube',284.7),36:('unhappy',183.3),37:('vacuum',256.8),38:('video',358.2),39:('warrior',409.3)}
TRI={1:(4,5,6),2:(11,12,13),3:(20,21,22),4:(28,29,30),5:(34,35,36),6:(37,38,39),
     7:(34,35,36),8:(28,29,30),9:(20,21,22),10:(11,12,13),11:(4,5,6),12:(2,3,4)}
PCX=json.load(open('numcentroid.json'))
def spans(ri):
    sw,X0=ROW[ri]; s=idx[sw]; out=[];c=0
    for k in range(70):
        i=s+k
        if i>=len(W): break
        x0=X0+CW*c; x1=x0+CW*len(W[i])
        if x0>2150: break
        out.append((W[i],x0,x1)); c+=len(W[i])+1
    return out
def nearest(ri,cx,k=1):
    sp=spans(ri)
    def d(t):
        w,a,b=t
        return 0 if a<=cx<=b else (a-cx if a>cx else cx-b)
    return [w for w,a,b in sorted(sp,key=d)[:k]]
KN=int(sys.argv[1]) if len(sys.argv)>1 else 1
CAND={}
for h in range(1,13):
    cx=PCX[str(h)]['pcx']
    c=[]
    for ri in TRI[h]:
        for w in nearest(ri,cx,KN):
            if w not in c: c.append(w)
    CAND[h]=c
ORD=[]
for st in range(1,13):
    ORD.append([((st-1+k)%12)+1 for k in range(12)])
    ORD.append([((st-1-k)%12)+1 for k in range(12)])
TARGET=O.WINNER.lower()
def work(first):
    others=[CAND[h] for h in range(2,13)]
    n=0;hits=[]
    for rest in itertools.product(*others):
        d={1:first}
        for i,h in enumerate(range(2,13)): d[h]=rest[i]
        for order in ORD:
            words=[d[h] for h in order]; n+=1
            seed=O.mnemonic_to_seed(" ".join(words))
            a=O.eth_address(O.derive(seed,[44+O.H,60+O.H,0+O.H,0,0]))
            if a.lower()==TARGET:
                hits.append((words,a))
                print('!!!! MATCH',words,a,flush=True)
                open('MOSS_HIT_FINAL.txt','w').write(json.dumps({'words':words,'addr':a}))
    return n,hits
if __name__=='__main__':
    for h in range(1,13): print(h,CAND[h])
    tot=1
    for h in range(1,13): tot*=len(CAND[h])
    print('sets',tot,'x ord',len(ORD),'=',tot*len(ORD),'derivations',flush=True)
    g=0;H=[]
    with Pool(4) as p:
        for n,hits in p.imap_unordered(work,CAND[1]):
            g+=n;H+=hits
    print('tested',g,'hits',H,flush=True)
