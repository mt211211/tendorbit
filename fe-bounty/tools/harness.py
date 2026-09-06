import sys, os, random
from pyrevm import EVM
from Crypto.Hash import keccak

BOUNTY="/home/user/fe-lang/bountiful"
OUT=os.path.join(BOUNTY,"contracts/out")
UNSOLVABLE=0x0EFDCBA987654321
SOLVED=0x0FEDCBA987654321
DEPLOYER="0x1000000000000000000000000000000000000001"

def sel(sig):
    k=keccak.new(digest_bits=256); k.update(sig.encode()); return k.digest()[:4]
def enc_u(x): return int(x).to_bytes(32,'big')
def load_bin(name):
    p=os.path.join(OUT,name)
    data=open(p,'rb').read()
    # Makefile converts hex->binary; if still hex text, decode
    try:
        txt=data.decode().strip()
        if all(c in '0123456789abcdefABCDEF' for c in txt) and len(txt)%2==0:
            return bytes.fromhex(txt)
    except Exception: pass
    return data

def deploy(evm, name, args=b""):
    code=load_bin(name)+args
    addr=evm.deploy(DEPLOYER, list(code))
    return addr

def call(evm, to, data, caller=DEPLOYER):
    out=evm.message_call(caller=caller, to=to, calldata=list(data))
    return bytes(out)

# ---- reference 15-puzzle model ----
def unpack(packed):
    return [(packed>>(i*4))&0xF for i in range(16)]
ADJ={0:[1,4],1:[0,2,5],2:[1,3,6],3:[2,7],4:[0,5,8],5:[1,4,6,9],6:[2,5,7,10],
     7:[3,6,11],8:[4,9,12],9:[5,8,10,13],10:[6,9,11,14],11:[7,10,15],
     12:[8,13],13:[9,12,14],14:[10,13,15],15:[11,14]}
def ref_move(board, index):
    empty=board.index(0)
    if index>15: return None,"InvalidIndex"
    if index not in ADJ[empty]: return None,"NotMovable"
    b=board[:]; b[empty]=b[index]; b[index]=0
    return b,None

def read_board_flat(evm, addr):
    return [int.from_bytes(call(evm,addr,sel("getBoard(uint256)")+enc_u(i)),'big') for i in range(16)]
def read_board_2d(evm, addr):
    b=[0]*16
    for i in range(16):
        r,c=i//4,i%4
        b[i]=int.from_bytes(call(evm,addr,sel("getBoard(uint256,uint256)")+enc_u(r)+enc_u(c)),'big')
    return b
def is_solved(evm, addr):
    return int.from_bytes(call(evm,addr,sel("isSolved()")),'big')==1

def try_move(evm, addr, index, two_d=False):
    """Return True if the call succeeded (no revert)."""
    try:
        if two_d:
            call(evm,addr,sel("moveField(uint256,uint256)")+enc_u(index//4)+enc_u(index%4))
        else:
            call(evm,addr,sel("moveField(uint256)")+enc_u(index))
        return True
    except Exception:
        return False

GAMES=[("Game.bin",False),("Game2D.bin",True),("GameEnum.bin",False),
       ("GameBitboard.bin",False),("GameMonadic.bin",False),
       ("GameNested.bin",False),("GameTrait.bin",False)]

def run():
    for name,two_d in GAMES:
        if not os.path.exists(os.path.join(OUT,name)):
            print(f"{name:18} MISSING"); continue
        evm=EVM()
        evm.set_balance(DEPLOYER, 10**20)
        try:
            val=deploy(evm,"DummyLockValidator.bin",enc_u(0))
            game=deploy(evm,name,bytes(12)+bytes.fromhex("%040x"%int(val,16))[-20:] if isinstance(val,str) else enc_u(int(val)) ) if False else None
        except Exception as e:
            print(f"{name:18} deploy-validator FAIL {e}"); continue
        # proper arg encoding: address left-padded to 32 + board
        vaddr=int(val,16) if isinstance(val,str) else int(val)
        game=deploy(evm,name, enc_u(vaddr)+enc_u(UNSOLVABLE))
        # differential fuzz
        ref=unpack(UNSOLVABLE)
        rng=random.Random(12345)
        diverged=False
        for step in range(4000):
            idx=rng.randint(0,15)
            ok=try_move(evm,game,idx,two_d)
            rb,err=ref_move(ref,idx)
            ref_ok = err is None
            if ok!=ref_ok:
                got=read_board_2d(evm,game) if two_d else read_board_flat(evm,game)
                print(f"{name:18} DIVERGENCE step {step} move {idx}: contract_accepted={ok} ref_accepted={ref_ok}")
                print(f"                   ref_board={ref} contract_board={got}")
                diverged=True; break
            if ok:
                got=read_board_2d(evm,game) if two_d else read_board_flat(evm,game)
                ref=rb
                if got!=ref:
                    print(f"{name:18} STATE DIVERGENCE step {step} move {idx}")
                    print(f"                   ref={ref}\n                   got={got}")
                    diverged=True; break
            if is_solved(evm,game):
                print(f"{name:18} *** SOLVED after fuzz — exploit path found at step {step} ***")
                diverged=True; break
        if not diverged:
            print(f"{name:18} no divergence in 4000 moves; solved={is_solved(evm,game)}")

if __name__=="__main__":
    run()
