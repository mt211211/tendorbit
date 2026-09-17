from PIL import Image
import numpy as np, json, math
from scipy import ndimage

IMG='/tmp/ocp/2-mid-prizes/logicbeach-powerful-moss-0-54eth/clues/powerfulmoss-poap.png'
a=np.array(Image.open(IMG).convert('RGB')).astype(int)
R,G,B=a[:,:,0],a[:,:,1],a[:,:,2]
eq=(R==G)&(G==B)
num=eq&(np.abs(R-83)<=3)
txt_under=eq&(np.abs(R-133)<=3)
glyph=num|txt_under
cl=ndimage.binary_closing(glyph,structure=np.ones((9,9)))
lab,n=ndimage.label(cl)
sizes=ndimage.sum(cl,lab,range(1,n+1))
objs=ndimage.find_objects(lab)
comps=[]
for i in range(1,n+1):
    if sizes[i-1]<2500: continue
    ys,xs=objs[i-1]
    comps.append(dict(x0=xs.start,x1=xs.stop,y0=ys.start,y1=ys.stop,size=int(sizes[i-1])))

# clock center estimate from all comps (centroid of ring)
CX=np.mean([(c['x0']+c['x1'])/2 for c in comps])
CY=np.mean([(c['y0']+c['y1'])/2 for c in comps])

def hour_of(c):
    cx=(c['x0']+c['x1'])/2; cy=(c['y0']+c['y1'])/2
    ang=math.degrees(math.atan2(cx-CX,-(cy-CY)))%360
    h=round(ang/30)%12
    return 12 if h==0 else h

groups={}
for c in comps:
    groups.setdefault(hour_of(c),[]).append(c)

NUM={}
for h,cs in groups.items():
    x0=min(c['x0'] for c in cs); x1=max(c['x1'] for c in cs)
    y0=min(c['y0'] for c in cs); y1=max(c['y1'] for c in cs)
    NUM[h]=dict(cx=(x0+x1)/2, cy=(y0+y1)/2, x0=x0,x1=x1,y0=y0,y1=y1,ncomp=len(cs))

if __name__=='__main__':
    print(f'clock center ~({CX:.1f},{CY:.1f})  hours found: {sorted(NUM)}')
    rows=json.load(open('rows.json'))
    for h in sorted(NUM):
        d=NUM[h]
        ri=[i for i,(s,e) in enumerate(rows) if s-10<=d['cy']<=e+10]
        print(f"  h{h:2d}: center ({d['cx']:7.1f},{d['cy']:7.1f}) bbox x{d['x0']}-{d['x1']} y{d['y0']}-{d['y1']} comps={d['ncomp']} rows={ri}")
    json.dump({str(k):v for k,v in NUM.items()},open('numerals.json','w'))
