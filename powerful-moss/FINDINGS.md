# LogicBeach "Powerful Moss" (0.55 ETH, Base) — image reconstruction and two corrections

Target: `2-mid-prizes/logicbeach-powerful-moss-0-54eth` in `floflo777/open-crypto-puzzles`.

**Status: NOT SOLVED.** No seed recovered, nothing claimed. What follows is a set of
*verified* results that correct the published analysis and materially change the search
space. They are recorded because they are reproducible and useful to anyone continuing
this puzzle — not because they constitute a solve.

## Summary

The puzzle is a POAP image: a clock face with 12 numerals laid over the full alphabetical
BIP39 wordlist. Each numeral marks a word; the 12 words in clock order are meant to form a
12-word BIP39 mnemonic deriving the winner wallet
`0x635739254BDE27d28301f25aD57c3cAC3C3468f3` at `m/44'/60'/0'/0/0`.

I reconstructed the image's layout exactly and read all 12 marked words directly from the
pixels. The method is validated three independent ways (below). It nevertheless does not
produce the winner wallet under any reading or ordering tested, which points to an error in
the documented mechanism rather than in the reading.

## Method (reproducible)

### 1. The render uses a fixed palette — so the layers separate exactly

Colour census of `clues/powerfulmoss-poap.png` (2004x2011):

| RGB | count | meaning |
|---|---|---|
| `(117,117,117)` | 1,874,297 | disc background |
| `(0,0,0)` | 917,299 | outside disc / hands |
| `(117,0,0)` | 291,438 | red sunburst ray over background |
| **`(177,177,177)`** | 210,165 | **wordlist text** |
| **`(83,83,83)`** | 142,126 | **clock numeral fill** |
| **`(133,133,133)`** | 12,589 | **text showing through a numeral** |
| `(177,0,0)` | 33,797 | text under a red ray |

Two consequences that make everything else possible:

- Overlays override *some* channels only, so the underlying value survives in whichever
  channel is untouched (text under a red ray is `(177,0,0)` — R still 177).
- **Gray 83 is exactly the 12 numerals.** Masking it renders a clean clock face, so the
  numerals can be extracted by connected components rather than guessed at. Gray 133 is
  precisely the text covered by a numeral (117→83 and 177→133 under the same overlay).

### 2. Layout

- 42 text rows, pitch **48 px** (horizontal projection of the text mask).
- Monospace cell width **25.46 px** (autocorrelation, confirmed by word-box regression).
- The wordlist is wrapped on a **wide virtual canvas and clipped to the circular disc** —
  each visible row is a contiguous alphabetical run, but consecutive rows skip words,
  because only the middle of each line falls inside the circle. Earlier reconstructions
  (mine and the dossier's) assumed a plain rectangular wrap, which is wrong.
- Each row was identified by matching observed word-box widths (letter counts) against the
  wordlist, then fitting the row origin `X0` so that `x = X0 + 25.46 * column`. Typical
  residual **< 1 px** (e.g. row 18 = `raccoon race rack radar radio rail rain raise rally
  ramp ranch random range rapid rare`).

### 3. Reading the numerals

Each numeral's glyph is extracted by connected components (two-digit numerals merged), and
the marked word is the one containing the numeral's pixel centroid.

## Validation (three independent checks)

1. **All three known anchors reproduce exactly**: `leisure`@12, `strategy`@4, `stick`@8 —
   each numeral's centroid falls squarely inside that word's box.
2. **The dossier's own candidate triples are independently regenerated** for 7 of the 9
   remaining hours (h1 `logic/mandate/mechanic`, h3 `retreat/romance/sand`,
   h5 `trash/turtle/unlock`, h6 `valve/vintage/waste`, h7 `traffic/tuition/uniform`,
   h11 `lizard/main/maze`, h2 `open/oyster/peace`) as the vertical neighbours at the
   numeral's x. This is strong evidence the grid is correct.
3. Row content matches the image when rendered and read by eye.

## Correction 1 — h9 and h10 candidates are shifted one row

For the two hours where my reconstruction disagrees with the published analysis, the
numeral centroids sit clearly in the row *below* the dossier's triple:

| hour | published triple | centroid row (this work) |
|---|---|---|
| 9 | `recycle / require / riot` | **`riot`** (row 21; `require` is row 20) |
| 10 | `notable / okay / outdoor` | **`outer` / `outdoor`** (row 12; `okay` is row 11) |

Centroid-to-row-centre distances: h9 = 14.5 px to row 21 vs 32 px to row 20; h10 = 7.5 px
to row 12 vs 42 px to row 11. **Every prior search used wrong candidates at these two
positions.**

## Correction 2 — every prior search filtered by BIP39 checksum

The published ledger records testing "1,193,373 combinations (**132,597 checksum-valid**)";
all my earlier sweeps did the same. But BIP39 seed derivation is `PBKDF2` over the phrase —
the checksum is only a validity flag that wallets enforce, not part of the derivation. If
the artist marked 12 words on the clock and funded whatever wallet that phrase produced,
the answer is checksum-**invalid** and is invisible to every search ever run on this puzzle.

This is not hypothetical: the best geometric reading
(`mandate oyster romance strategy turtle vintage tuition stick riot outer main leisure`)
**is checksum-invalid**.

## Best reading

| hour | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| word | mandate | oyster | romance | **strategy** | turtle | vintage |

| hour | 7 | 8 | 9 | 10 | 11 | 12 |
|---|---|---|---|---|---|---|
| word | tuition | **stick** | riot | outer/outdoor | main/major | **leisure** |

Bold = anchors confirmed independently. Only h10 and h11 are genuinely ambiguous — both
are two-digit numerals whose centroid lands in the gap between two words.

## What was ruled out (all negative)

| Test | Scale | Result |
|---|---|---|
| Best reading x **all** 12! orderings | 479,001,600 | 0 |
| Corrected candidates x 24 clock orderings (checksum-filtered) | 4.67 M | 0 |
| Horizontal (same-row) neighbours x clock orderings | 472 k | 0 |
| Corrected candidates, **no checksum filter** | 4.67 M derivations | 0 |
| **Vertical +/-1 on all 12 hours** (anchors free), no checksum | 12.75 M derivations | 0 |
| Best reading x 62 derivation paths x 10 passphrases x 24 orderings | 76,800 derivations | 0 |

## Interpretation

The best reading fails under *every one of its 479 million* orderings, and a one-row
misread on any hour — with or without checksum validity — fails too. Those two results
together mean the gap is not a near-miss in the reading. Something in the documented model
is wrong: an undocumented passphrase or transform, a different derivation path, or an
incorrect target address.

The derivation variants have since been tested and are negative: 62 derivation paths
(BIP44 accounts 0-3 x indexes 0-5 x change 0/1, BIP84, BIP49, `m/0/i`, `m/0'/i`, the
4-level `m/44'/60'/0'/0`, and the master key itself) crossed with 10 passphrase guesses,
over all 24 clock orderings of the best reading — 76,800 derivations, 0 matches.

That leaves one main untested assumption: **independently confirm the winner
wallet address on-chain.** The entire search is conditioned on
`0x635739254BDE27d28301f25aD57c3cAC3C3468f3`, taken on trust from the dossier and never
verified here (this environment's egress blocks Base RPC). If that address is wrong, every
search ever run on this puzzle — including all of the above — was aimed at the wrong
target. Anyone with a Base RPC endpoint should check it against the prize contract's
`withdraw()` before spending further compute.

## Files

    tools/moss_oracle.py   independent BIP39 -> BIP44 ETH oracle, certified against the
                           all-zero-entropy KAT (0x9858EfFD...) with +/- controls
    tools/numerals.py      extracts the 12 numerals (gray 83) by connected components
    tools/allrows.py       identifies each text row's wordlist run and fits its origin
    tools/final_read.py    picks each numeral's word by under-numeral pixel overlap
    tools/final_sweep.py   vertical +/-1 sweep over all 12 hours x clock orderings
    tools/hneigh.py        horizontal-neighbour sweep

The oracle is self-certifying: any candidate deriving the winner wallet is proof. Nothing
in this document is a claimed solve.
