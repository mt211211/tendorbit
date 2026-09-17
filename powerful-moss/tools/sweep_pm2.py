"""+/-2 row sweep: the numeral glyphs are ~5 text rows tall, so the marked word can be
up to 2 rows either side of the centroid. Anchors (h4,h8,h12) fixed to their confirmed
words. All rotational + non-rotational orderings. No checksum filter. Checkpointed."""
import itertools, json, os, sys, time
from multiprocessing import Pool
from mnemonic import Mnemonic
import moss_oracle as O
W=Mnemonic('english').wordlist; idx={w:i for i,w in enumerate(W)}
CW=25.46
ROW={2:('knife',437.2),3:('left',361.1),4:('live',361.7),5:('maid',256.8),
     6:('maximum',307.3),7:('million',256.3),10:('noodle',-354.0),11:('oil',127.0),12:('other',-20.7),
     13:('pass',152.0),14:('phrase',-46.2),19:('recipe',-357.0),20:('report',-51.5),21:('ring',-46.1),
     22:('saddle',52.0),23:('science',-306.0),28:('spoil',177.5),29:('stereo',4.8),
     30:('suffer',33.8),31:('swim',106.7),33:('tobacco',81.3),34:('track',208.2),35:('tube',284.7),
     36:('unhappy',183.3),37:('vacuum',256.8),38:('video',358.2),39:('warrior',409.3),40:('when',-411.0)}
CENTER={1:5,2:12,3:21,4:29,5:35,6:38,7:35,8:29,9:21,10:12,11:5,12:3}
CONF={4:'strategy',8:'stick',12:'leisure'}
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
CAND={}
for h in range(1,13):
    if h in CONF: CAND[h]=[CONF[h]]; continue
    cx=PCX[str(h)]['pcx']; c0=CENTER[h]; c=[]
    for dr in (0,-1,1,-2,2):
        w=nearest(c0+dr,cx)
        if w and w not in c: c.append(w)
    CAND[h]=c
READ=[12,11,1,10,2,9,3,8,4,7,5,6]; COL=[9,8,10,7,11,6,12,1,5,2,4,3]
ORD=[]
for st in range(1,13):
    ORD.append([((st-1+k)%12)+1 for k in range(12)])
    ORD.append([((st-1-k)%12)+1 for k in range(12)])
ORD += [READ, READ[::-1], COL, COL[::-1]]
TARGET=O.WINNER.lower(); PROG='pm2_progress.txt'
def work(first):
    others=[CAND[h] for h in range(2,13)]
    n=0;hits=[]
    for rest in itertools.product(*others):
        d={1:first}
        for i,h in enumerate(range(2,13)): d[h]=rest[i]
        vals=[d[h] for h in range(1,13)]
        cands=[[d[h] for h in o] for o in ORD]+[sorted(vals),sorted(vals,reverse=True)]
        for words in cands:
            n+=1
            seed=O.mnemonic_to_seed(" ".join(words))
            if O.eth_address(O.derive(seed,[44+O.H,60+O.H,0+O.H,0,0])).lower()==TARGET:
                hits.append(words); print('!!!! MATCH',words,flush=True)
                open('MOSS_HIT_PM2.txt','w').write(json.dumps(words))
    return n,hits
if __name__=='__main__':
    done=set()
    if os.path.exists(PROG):
        for ln in open(PROG):
            if ln.startswith('DONE '): done.add(ln.split()[1])
    for h in range(1,13): print(h,CAND[h])
    tot=1
    for h in range(1,13): tot*=len(CAND[h])
    print('sets',tot,'x',len(ORD)+2,'orderings =',tot*(len(ORD)+2),'derivations',flush=True)
    t0=time.time(); g=0
    with Pool(4) as p:
        todo=[f for f in CAND[1] if f not in done]
        for f,(n,hits) in zip(todo,p.imap(work,todo)):
            g+=n
            with open(PROG,'a') as fh: fh.write(f'DONE {f} checked={n} cum={g} t={time.time()-t0:.0f}\n')
            if hits: print('SOLVED',hits,flush=True); break
    print('tested',g,'elapsed',time.time()-t0,flush=True)
