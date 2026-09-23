import sys; sys.path.insert(0,'/home/user/tendorbit/puzzle2/tools')
import numpy as np, glyphlib as gl
from templates import normalize_patch
from PIL import Image, ImageDraw

folder, lo, hi, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
roll = int(sys.argv[5]); rot = int(sys.argv[6])
y0,y1,x0,x1 = [int(v) for v in sys.argv[7].split(',')]

bg = gl.temporal_background(folder, sample=300)
paths = gl.frame_paths(folder)
items=[]
for i in range(lo,hi):
    z = gl.normalized_residual(gl.load_gray(paths[i]), bg)
    st = gl.stretch(z,50,99.9)
    r = np.roll(st, roll, axis=1) if roll else st
    c = np.rot90(r[y0:y1, x0:x1], k=rot)
    if (c>120).sum() < 400:      # nothing substantial in view
        continue
    items.append((i,c))

groups=[]
for i,c in items:
    v = normalize_patch(c)
    if v is None: continue
    if groups and float(groups[-1]['v'] @ v) > 0.90:
        g=groups[-1]; g['last']=i; g['n']+=1
        if (c>120).sum() > (g['c']>120).sum(): g['c']=c; g['v']=v
    else:
        groups.append({'first':i,'last':i,'n':1,'c':c,'v':v})
groups=[g for g in groups if g['n']>=2]
print(f'{out}: {len(groups)} distinct')
for k,g in enumerate(groups): print(f"  [{k}] f{g['first']}-{g['last']} n={g['n']}")

cell=200; cols=8; rows=(len(groups)+cols-1)//cols
im=Image.new('L',(cols*cell,rows*(cell+16)),0); d=ImageDraw.Draw(im)
for k,g in enumerate(groups):
    t=Image.fromarray(np.clip(g['c'],0,255).astype(np.uint8)); t.thumbnail((cell-8,cell-8))
    px,py=(k%cols)*cell+4,(k//cols)*(cell+16)+4
    im.paste(t,(px,py)); d.text((px,py+cell-6),f"{k}:f{g['first']}",fill=200)
im.save(f'/tmp/{out}.png')
