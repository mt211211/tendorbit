import os
from pyrevm import EVM
from Crypto.Hash import keccak
ME="0x1000000000000000000000000000000000000001"; UNS=0x0EFDCBA987654321
def sel(s):
    k=keccak.new(digest_bits=256);k.update(s.encode());return k.digest()[:4]
def u(x): return int(x).to_bytes(32,'big')
def load(d,n): return bytes.fromhex(open(os.path.join(d,n),'rb').read().decode().strip())
def make(d,name):
    e=EVM(); e.set_balance(ME,10**20)
    v=e.deploy(ME,list(load(d,"DummyLockValidator.bin")+u(0)))
    g=e.deploy(ME,list(load(d,name)+u(int(v,16))+u(UNS))); return e,g
def board(e,g,td):
    b=[]
    for i in range(16):
        cd=sel("getBoard(uint256,uint256)")+u(i//4)+u(i%4) if td else sel("getBoard(uint256)")+u(i)
        b.append(int.from_bytes(bytes(e.message_call(caller=ME,to=g,calldata=list(cd))),'big'))
    return b
def mv(e,g,i,td):
    cd=sel("moveField(uint256,uint256)")+u(i//4)+u(i%4) if td else sel("moveField(uint256)")+u(i)
    try: e.message_call(caller=ME,to=g,calldata=list(cd)); return 1
    except Exception: return 0
G=[("Game.bin",False),("Game2D.bin",True),("GameEnum.bin",False),("GameBitboard.bin",False),
   ("GameMonadic.bin",False),("GameNested.bin",False),("GameTrait.bin",False)]
IDX=list(range(18))+[2**64+14,2**128,2**256-1,13,14,11]
anydiff=False
for name,td in G:
    es,gs=make("/tmp/out_sona",name); ey,gy=make("/tmp/out_yul_ok",name)
    diffs=[]
    for idx in IDX:
        ss=es.snapshot(); sy=ey.snapshot()
        rs=mv(es,gs,idx,td); ry=mv(ey,gy,idx,td)
        bs=board(es,gs,td); by=board(ey,gy,td)
        if rs!=ry or bs!=by: diffs.append((idx,rs,ry))
        es.revert(ss); ey.revert(sy)
    print(f"{name:16} {'DIFFS '+str(diffs) if diffs else 'sona==yul on all probed indices'}", flush=True)
    anydiff=anydiff or bool(diffs)
print("ANY BACKEND DIVERGENCE:", anydiff, flush=True)
