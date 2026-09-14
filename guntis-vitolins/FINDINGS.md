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

---

## RESULT — lead 3 is a certified negative

The sweep completed cleanly on 2026-09-14.

| | |
|---|---|
| units | **816 / 816**, every one `witness OK` |
| arrangements enumerated | **167,688,000** |
| checksum-valid derivations | **10,484,919** |
| derivation paths per phrase | **18** |
| total derivations | **≈ 188.7 million** |
| matches | **0** |
| wall clock | 104.9 min on 4 CPU cores, 1,667 derivations/s |

### The enumeration is provably the same space as the original RO1

My run produced **exactly 10,484,919** checksum-valid derivations. The folder's own
`analysis/tested.md` records the RO1 sweep at **10,484,919** (lines 110 and 139). An
identical count to the digit, from an independently driven run, is strong evidence that
the space enumerated here is the same one — which is what makes this negative
transferable rather than merely a negative about some nearby space.

### What this closes

Every negative in that folder was previously a negative *at the MetaMask default path*.
This upgrades them: the RO1 reading-order model is now negative across
`m/44'/60'/0'/0/{0..4}`, the change chain, accounts 1-3, the 4-level Ledger-style form,
`m/0..2` and the master key — 18 paths in total, a superset of the 4 the folder named.

So the hypothesis "the author funded from a second MetaMask account, and every recorded
negative is about the wrong address" is **dead**. The remaining gap is word
identification, exactly as the folder's own lead ranking argues.

## Sizing the next lead (lead 1: on-screen words)

Lead 1 found the real blocking gap: 122 dictionary words are legible on screen and 109 of
them appear in no written surface, so the pool every sweep used was incomplete. The five
that match the portfolio-table prediction are `atom`, `link`, `basic`, `token`, `dash`.

Extending the RO1 model to admit them as free-position video words, sized here:

| coin words admitted | arrangements | derivations | hours at 1,667/s x 18 paths |
|---|---|---|---|
| 0 (= RO1, done) | 167,688,000 | 10,484,919 | 1.7 (done) |
| at most 1 | 1,817,028,000 | 113,564,250 | 18.9 |
| at most 2 | 4,170,780,000 | 260,673,750 | 43.4 |
| at most 4 | 4,903,711,200 | 306,481,950 | 51.1 |

The **exactly-one-coin-word** shell is 103,083,750 derivations, about 17 hours across 18
paths — the highest-prior slice, since a phrase drawing one word from the on-screen
portfolio table is far likelier than one drawing four.
