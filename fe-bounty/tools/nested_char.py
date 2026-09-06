import os
from pyrevm import EVM
from Crypto.Hash import keccak
ME="0x1000000000000000000000000000000000000001"; UNS=0x0EFDCBA987654321
def sel(s):
    k=keccak.new(digest_bits=256);k.update(s.encode());return k.digest()[:4]
def u(x): return int(x).to_bytes(32,'big')
def load(d,n): return bytes.fromhex(open(os.path.join(d,n),'rb').read().decode().strip())
def make(d,board):
    e=EVM(); e.set_balance(ME,10**20)
    v=e.deploy(ME,list(load(d,"DummyLockValidator.bin")+u(0)))
    g=e.deploy(ME,list(load(d,"GameNested.bin")+u(int(v,16))+u(board))); return e,g
def board(e,g):
    return [int.from_bytes(bytes(e.message_call(caller=ME,to=g,calldata=list(sel("getBoard(uint256)")+u(i)))),'big') for i in range(16)]
def mv(e,g,i):
    try: e.message_call(caller=ME,to=g,calldata=list(sel("moveField(uint256)")+u(i))); return 1
    except Exception: return 0
def solved(e,g):
    return int.from_bytes(bytes(e.message_call(caller=ME,to=g,calldata=list(sel("isSolved()")))),'big')

for backend in ("/tmp/out_sona","/tmp/out_yul_ok"):
    print("=====",backend)
    e,g=make(backend,UNS)
    print("initial board:",board(e,g))
    for i in range(16):
        s=e.snapshot()
        ok=mv(e,g,i)
        after=board(e,g) if ok else None
        print(f"  move {i:2}: accepted={ok} board={after}")
        e.revert(s)
