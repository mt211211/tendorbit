import os
from pyrevm import EVM
from Crypto.Hash import keccak
ME="0x1000000000000000000000000000000000000001"; UNS=0x0EFDCBA987654321
def sel(s):
    k=keccak.new(digest_bits=256);k.update(s.encode());return k.digest()[:4]
def u(x): return int(x).to_bytes(32,'big')
def load(d,n): return bytes.fromhex(open(os.path.join(d,n),'rb').read().decode().strip())
def board(d):
    e=EVM(); e.set_balance(ME,10**20)
    v=e.deploy(ME,list(load(d,"DummyLockValidator.bin")+u(0)))
    g=e.deploy(ME,list(load(d,"GameNested.bin")+u(int(v,16))+u(UNS)))
    return [int.from_bytes(bytes(e.message_call(caller=ME,to=g,calldata=list(sel("getBoard(uint256)")+u(i)))),'big') for i in range(16)]
print("expected      :",[1,2,3,4,5,6,7,8,9,10,11,12,13,15,14,0])
print("sonatina (dflt):",board("/tmp/out_sona"))
print("yul backend    :",board("/tmp/out_yul_ok"))
