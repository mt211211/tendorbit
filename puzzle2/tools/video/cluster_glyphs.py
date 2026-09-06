import sys; sys.path.insert(0,'/home/user/tendorbit/puzzle2/tools')
import numpy as np, glyphlib as gl
from templates import normalize_patch
from PIL import Image, ImageDraw

folder,lo,hi,rollspec,rot,box,out = sys.argv[1],int(sys.argv[2]),int(sys.argv[3]),sys.argv[4],int(sys.argv[5]),sys.argv[6],sys.argv[7]
y0,y1,x0,x1=[int(v) for v in box.split(',')]
bg=gl.temporal_background(folder,sample=300); paths=gl.frame_paths(folder)

frames=[]
for i in range(lo,hi):
    z=gl.normalized_residual(gl.load_gray(paths[i]),bg)
    st=gl.stretch(z,50,99.9)
    rx,ry=[int(v) for v in rollspec.split(',')]
    r=st
    if rx: r=np.roll(r,rx,axis=1)
    if ry: r=np.roll(r,ry,axis=0)
    c=np.rot90(r[y0:y1,x0:x1],k=rot)
    if (c>120).sum()<500: continue
    gs=[g for g in gl.segment(c,split=False) if g.ink>400]
    if not gs: continue
    g=max(gs,key=lambda x:x.ink)
    v=normalize_patch(g.patch)
    if v is None: continue
    frames.append((i,g.patch,v))

# greedy clustering
clusters=[]
for i,p,v in frames:
    best,bi=-1,-1
    for k,cl in enumerate(clusters):
        s=float(cl['v']@v)
        if s>best: best,bi=s,k
    if best>0.88:
        cl=clusters[bi]; cl['members'].append(i)
        if (p>120).sum()>(cl['p']>120).sum(): cl['p'],cl['v']=p,v
    else:
        clusters.append({'p':p,'v':v,'members':[i]})
clusters=[c for c in clusters if len(c['members'])>=2]
print(f'{len(clusters)} clusters from {len(frames)} frames')
lab={id(c):k for k,c in enumerate(clusters)}
seq=[]
for i,p,v in frames:
    best,bi=-1,-1
    for k,cl in enumerate(clusters):
        s=float(cl['v']@v)
        if s>best: best,bi=s,k
    seq.append((i,bi,round(best,2)))
# runs
runs=[]
for i,k,s in seq:
    if runs and runs[-1][0]==k and i-runs[-1][2]<=2: runs[-1][2]=i; runs[-1][3]+=1
    else: runs.append([k,i,i,1])
print('RUNS (cluster, first, last, n):')
print('  '+' '.join(f'{k}[{a}-{b}]' for k,a,b,n in runs if n>=2))
cell=170; cols=10; rows=(len(clusters)+cols-1)//cols
im=Image.new('L',(cols*cell,rows*(cell+16)),0); d=ImageDraw.Draw(im)
for k,cl in enumerate(clusters):
    t=Image.fromarray(np.clip(cl['p'],0,255).astype(np.uint8)); t.thumbnail((cell-8,cell-8))
    px,py=(k%cols)*cell+4,(k//cols)*(cell+16)+4
    im.paste(t,(px,py)); d.text((px,py+cell-8),f'{k} n={len(cl["members"])}',fill=220)
im.save(f'/tmp/{out}.png')
