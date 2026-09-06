# Fe compiler bug bounty (fe-lang/bountiful, 1 ETH) — investigation

Target: `2-mid-prizes/fe-lang-bountiful-compiler-bounty-1eth` in
`floflo777/open-crypto-puzzles`. Seven 15-puzzle contracts are deployed on
Ethereum mainnet in the parity-unsolvable start state `[1..13,15,14,0]`. The
bounty pays whoever makes `claim(challenge)` succeed, which requires
`isSolved()` to return `true` on a contract that the published move rules can
never solve — i.e. a defect in the Fe compiler (v26.1.0) or in the ~1,600 lines
of hand-written Fe.

## Toolchain built (all reproducible, nothing external beyond GitHub + crates.io + npm)

- Built the pinned compiler `fe 26.1.0` from source (`argotorg/fe` @ tag
  `v26.1.0`) with cargo.
- Compiled all challenge contracts with the default **sonatina** backend
  (`fe build`) — this is what the bounty's `make build` and its mainnet
  deployment use.
- Bridged the **yul** backend (which needs `solc`) to `solc-js` from npm via a
  small Node shim (`tools/solc_bridge.js`), so the same source could be compiled
  through a second, independent codegen path.
- Deployed and executed the compiled EVM bytecode in `pyrevm` (revm bindings),
  with a pure-Python reference 15-puzzle model for differential testing.

## What was proven faithful (the deployed / sonatina backend)

The certified derivation and the deployed contracts behave correctly under every
test run:

- **Move semantics**: an exhaustive per-state differential walk testing *all 16*
  candidate `moveField` arguments at each state against the reference model —
  **96,000 move-checks per game, zero divergence** across all seven games.
- **Boundary arguments**: out-of-range and huge indices (16, 17, 2^64+14,
  2^128, 2^256-1, …) are correctly rejected by every game.
- **`isSolved()` predicate**: deploying with crafted boards and flipping one
  cell at a time shows every game checks all 16 cells correctly; no cell is
  skipped or mis-checked.
- **Full registry claim flow**: deploying the real `BountyRegistry`, registering,
  locking and calling `claim()` — a solved board pays out (positive control),
  an unsolvable board reverts. The cross-contract `isSolved` return is handled
  correctly.

Under the sonatina backend that is actually deployed, the contracts are correct,
so no sequence of on-chain calls solves them. The on-chain boards read as
`[1..13,15,14,0]` (dossier, 2026-08-17), which is consistent only with sonatina.

## The compiler bug that WAS found (yul backend)

Running the identical source through the **yul** backend and differencing it
against sonatina in lockstep surfaced a real miscompilation in **GameNested**
(the variant using nested structs of arrays in storage:
`Board { rows: [Row { cells: [u256;4] }; 4] }`).

Reproduction (`tools/repro.py`), initial board via `getBoard`:

    expected      : [1, 2, 3, 4, 5, 6, 7, 8, 9,10,11,12,13,15,14, 0]
    sonatina      : [1, 2, 3, 4, 5, 6, 7, 8, 9,10,11,12,13,15,14, 0]   # correct
    yul backend   : [0, 0,360448,0,1024,32768,8192,32768,8192,8192,0,32768,8192,0,32768,8192]  # garbage

The yul backend lays out / accesses the nested `[Row;4]`-of-`[u256;4]` storage
incorrectly: the constructor's `store.board.rows[row].cells[col] = cells[i]`
writes and the `getBoard`/`find_empty` reads do not agree, so the board is
corrupted and `moveField` even accepts non-adjacent (illegal) moves. This is a
genuine `fe 26.1.0` codegen defect in nested aggregate storage lowering.

The other six games, and GameNested under sonatina, are byte-for-byte faithful.
GameBitboard and GameTrait (the two Sourcify-*unverified* contracts) are
faithful under **both** backends, so whichever backend was used to deploy them,
they are not exploitable.

## Why this is not (yet) a claim

The prize requires making a *deployed* contract report solved. The deployed
contracts use the **sonatina** backend, where GameNested — and everything else —
is correct. The miscompilation is in the **yul** backend, which is not what was
deployed (confirmed: the on-chain board reads correctly, whereas a yul build
reads garbage). So the bug found is real and reportable to the Fe team, but it
does not by itself unlock the on-chain prize.

The one thing that would change this: if the on-chain runtime bytecode of any
deployed game actually differs from its sonatina build (possible only for the
two Sourcify-unverified contracts, GameBitboard / GameTrait — though both are
faithful under both backends in local testing). Confirming that needs the
on-chain runtime bytecode, i.e. an Ethereum RPC endpoint or the bytecode pasted
from Etherscan — neither reachable from this session (egress allows only
github.com and package registries).

## Status

**Not solved.** A real `fe 26.1.0` yul-backend compiler bug was found and
reproduced (GameNested nested-struct storage), but the deployed sonatina
contracts are faithful, so `oracle`-equivalent success (a deployed unsolvable
board reporting solved) has not been achieved. No fabricated exploit is claimed.

## Files

    tools/harness.py       full differential fuzz (reference vs compiled, all games)
    tools/quickdiff.py     sonatina-vs-yul backend divergence probe
    tools/nested_char.py   per-move characterisation of GameNested on each backend
    tools/repro.py         minimal reproduction of the yul GameNested miscompilation
    tools/solc_bridge.js   Node shim exposing solc-js to fe's yul backend

## UPDATE: on-chain bytecode confirmed (user-supplied, 2026-09-06)

The user fetched the deployed runtime bytecode of the two Sourcify-unverified
contracts via `eth_getCode`. Both are **byte-for-byte identical to the sonatina
build**:

    GameBitboard  on-chain (4290 nibbles) == sonatina build   (yul differs, 6532)
    GameTrait     on-chain (6296 nibbles) == sonatina build   (yul differs, 7438)

So every deployed challenge contract — the 5 Sourcify-verified ones and these 2
unverified ones — is the correct **sonatina** build, which is proven faithful
here. The on-chain avenue is closed: there is no exploitable miscompilation in
the deployed bytecode reachable through the game or registry interface.

**Final status: not solved.** A real fe 26.1.0 yul-backend compiler bug was
found and reproduced (GameNested nested-struct storage), but it is not present
in the deployed sonatina code, so it does not unlock the prize. No exploit is
claimed.
