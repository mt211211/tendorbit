# Guntis Vitolins "10 ETH Challenge" — lead 3: the MetaMask path family

Target: `1-big-prizes/guntis-vitolins-metamask-8-6eth` in `floflo777/open-crypto-puzzles`.
Escrow `0x9C2F44EFAd0c1E852a09dF9939e6DaF061140CaF`, **8.6125 ETH**, open.

**Status: IN PROGRESS.** Nothing claimed.

## Why this puzzle

Of the 30 open puzzles in that repository, exactly **one** is classified
`difficulty_left: bounded-compute` — this one. The other 29 need an *insight* (14),
*external information* (16), *human action* (1), or are *uneconomic* (1, a $31k-156k
compute bill against an $18.90 prize). "Insight" is precisely the class that cannot be
forced by effort.

## The experiment

Lead 3 of that folder, never run, and described there as *"the best value experiment
currently available in this folder"*:

> Every sweep in the folder derives only `m/44'/60'/0'/0/0`. The escrow is stated to be
> MetaMask, so that is the correct first guess — but if the author funded the challenge
> from a second account in the same wallet, then every negative on record is a negative
> about the wrong address and says nothing about the phrase.
> Cost: about 4 hours on 2 CPU cores.

It is cheap because the PBKDF2 seed stretch dominates a BIP39 derivation; changing the
path only repeats the child-key step and the address hash.

## Method, and why the negative (if it is one) will be trustworthy

- **The enumeration is the folder's own.** `tools/gv_multipath.py` *imports*
  `sweep_reading_order.py` and calls its `scan_unit`; the arrangement space, the anchors
  (`dutch`@1, `fog`@5, `parrot`@12), the `fork` floater logic and the BIP39 checksum
  filter are untouched. Re-implementing them would risk a divergent space and invalidate
  the result.
- **Only the derivation is replaced**, with a shared-seed prefix tree over **18 paths**
  (the folder names 4: `m/44'/60'/0'/0/1`, `/0/2`, `m/44'/60'/1'/0/0`, `m/44'/60'/2'/0/0`
  — all 18 are a superset).
- **The oracle is certified** against the same canonical BIP-0039 vector the folder
  certifies against: `abandon`x11 + `about` → `0x9858effd232b4033e47d90003d41ec34ecaeda94`.
  (The folder's own `oracle.py` needs `bip_utils`, whose `crcmod` dependency will not
  build in this environment.)

### Selftest

    units (post word sets): 816              (expect 816)
    closed form arrangements: 167,688,000    (expect 167,688,000)
    oracle reproduces the canonical BIP-0039 vector: OK
    paths: 18; contains all 4 the folder names: True
    planted witness: a real in-space phrase at m/44'/60'/1'/0/0
    sweep recovered the planted non-default-path phrase: OK  (witness OK)

The planted-witness line is the important one: a genuine in-space arrangement was derived
at a **non-default** path, made the target, and recovered by the sweep — so the pipeline
provably detects the exact thing this experiment exists to find.

Each unit also re-derives its first candidate through a fresh call and must agree
(`witness OK`), so a unit reporting OK has proved its own pipeline live.

## Expected outcomes

- **Hit**: the author funded from a non-default account; the phrase is written to a file
  and not printed, following the folder's protocol.
- **Miss**: upgrades every negative in that folder from "negative at the default path" to
  "negative across the plausible MetaMask path family" — a real, certified contribution.

Prior estimate that it hits: **10-20 %**, being the chance the author used a non-default
account index. This is a bounded experiment with a defined payoff either way, not a search
for an insight that may not exist.
