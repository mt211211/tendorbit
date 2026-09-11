import numpy as np, json
from PIL import Image
from mnemonic import Mnemonic
W=Mnemonic('english').wordlist; idx={w:i for i,w in enumerate(W)}
rows=json.load(open('rows.json'))
NUM={int(k):v for k,v in json.load(open('numerals.json')).items()}
CW=25.46
a=np.array(Image.open('/tmp/ocp/2-mid-prizes/logicbeach-powerful-moss-0-54eth/clues/powerfulmoss-poap.png').convert('RGB')).astype(int)
R,G,B=a[:,:,0],a[:,:,1],a[:,:,2]
eq=(R==G)&(G==B)
UNDER=eq&(np.abs(R-133)<=3)     # text showing through a numeral
NORMAL=(np.abs(R-177)<=2)       # normal text

# per-row: (first word of visible run, X0) verified against observed boxes
ROWDEF={
 3:('left',   360.9),
 5:('maid',   257.1),
 12:('other', -20.8),
 21:('ring',  -46.3),
 29:('stereo',  4.8),
 35:('tube',  272.0),
 38:('vessel',256.8),
}
HOURROW={12:3,1:5,11:5,2:12,10:12,3:21,9:21,4:29,8:29,5:35,7:35,6:38}

def spans(ri):
    """word spans (idx, x0, x1) across the visible row"""
    sw,X0=ROWDEF[ri]; start=idx[sw]
    out=[];c=0
    for k in range(0,80):
        i=start+k
        if i>=len(W): break
        x0=X0+CW*c; x1=x0+CW*len(W[i])
        if x0>2100: break
        out.append((i,x0,x1))
        c+=len(W[i])+1
    return out

def pick(h):
    ri=HOURROW[h]; s,e=rows[ri]
    d=NUM[h]
    nx0,nx1=int(d['x0']),int(d['x1'])          # restrict to THIS numeral's glyph box
    sp=spans(ri)
    res=[]
    for i,x0,x1 in sp:
        A=max(0,int(round(x0)),nx0); Bx=min(2004,int(round(x1)),nx1)
        if Bx<=A: continue
        cnt=int(UNDER[s:e+1,A:Bx].sum())
        res.append((cnt,i,x0,x1))
    res.sort(reverse=True)
    return res

if __name__=='__main__':
    print('validation on confirmed anchors (h12=leisure, h4=strategy, h8=stick):')
    out={}
    for h in [12,4,8]+[x for x in range(1,13) if x not in (12,4,8)]:
        r=pick(h)
        best=r[0]; out[h]=W[best[1]]
        runner=r[1] if len(r)>1 else None
        rr='' if runner is None else f'   runner-up {W[runner[1]]}({runner[0]})'
        print(f'  h{h:2d}: {W[best[1]]:10s} under-px={best[0]:5d}{rr}')
    print()
    seq=[out[h] for h in range(1,13)]
    print('CLOCK WORDS 1..12:',seq)
    json.dump(out,open('clockwords_final.json','w'))
