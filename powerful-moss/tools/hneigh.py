import json, itertools, sys
from multiprocessing import Pool
from mnemonic import Mnemonic
import moss_oracle as O
W=Mnemonic('english').wordlist; idx={w:i for i,w in enumerate(W)}
CW=25.46
NUM={int(k):v for k,v in json.load(open('numerals.json')).items()}
ROWDEF={3:('left',360.9),5:('maid',257.1),12:('other',-20.8),21:('ring',-46.3),
        29:('stereo',4.8),35:('tube',272.0),38:('video',358.2)}
HOURROW={12:3,1:5,11:5,2:12,10:12,3:21,9:21,4:29,8:29,5:35,7:35,6:38}
CONF={4:'strategy',8:'stick',12:'leisure'}

def spans(ri):
    sw,X0=ROWDEF[ri]; s=idx[sw]; out=[];c=0
    for k in range(60):
        i=s+k
        if i>=len(W): break
        x0=X0+CW*c; x1=x0+CW*len(W[i])
        if x0>2100: break
        out.append((W[i],x0,x1)); c+=len(W[i])+1
    return out

K=int(sys.argv[1]) if len(sys.argv)>1 else 3
FIXCONF = (len(sys.argv)<3 or sys.argv[2]!='freeconf')
cand={}
for h in range(1,13):
    if FIXCONF and h in CONF:
        cand[h]=[CONF[h]]; continue
    ri=HOURROW[h]; cx=NUM[h]['cx']; sp=spans(ri)
    def dist(t):
        w,a,b=t
        return 0 if a<=cx<=b else (a-cx if a>cx else cx-b)
    cand[h]=[w for w,a,b in sorted(sp,key=dist)[:K]]

def ords():
    o=[]
    for st in range(1,13):
        o.append([((st-1+k)%12)+1 for k in range(12)])
        o.append([((st-1-k)%12)+1 for k in range(12)])
    return o
ORD=ords()

def work(first):
    hits=[]; n=0
    others=[cand[h] for h in range(2,13)]
    for rest in itertools.product(*others):
        d={1:first}
        for i,h in enumerate(range(2,13)): d[h]=rest[i]
        for order in ORD:
            words=[d[h] for h in order]
            n+=1
            if not O.valid_checksum(words): continue
            seed=O.mnemonic_to_seed(" ".join(words))
            a=O.eth_address(O.derive(seed,[44+O.H,60+O.H,0+O.H,0,0]))
            if a.lower()==O.WINNER.lower():
                hits.append((words,a))
                print('!!!! MATCH',words,a,flush=True)
                open('MOSS_HIT.txt','w').write(json.dumps({'words':words,'addr':a}))
    return n,hits

if __name__=='__main__':
    for h in range(1,13): print(h,cand[h])
    tot=1
    for h in range(1,13): tot*=len(cand[h])
    print('sets',tot,'x orderings',len(ORD),'=',tot*len(ORD),flush=True)
    g=0; H=[]
    with Pool(4) as p:
        for n,hits in p.imap_unordered(work,cand[1]):
            g+=n; H+=hits
    print('tested',g,'hits',H,flush=True)
