# Path to Greatness: Treasure Hunt — work log

Target: `2-mid-prizes/path-to-greatness-treasure-hunt-3ltc` in `floflo777/open-crypto-puzzles`.
Escrow `LUtL7qnm3gzxKjHcfVLSjydqhhinTVmTmS`, **3.03 LTC** (~$163), open. **Nothing claimed.**

## Why this puzzle

Chosen on 2026-09-22 from a fresh survey of all 31 open puzzles, filtered by one hard
constraint of this environment: outbound requests to YouTube, archive.org and author sites
return `403 Forbidden` on CONNECT (organisation network policy), so any puzzle whose
missing evidence lives online is out of reach. This one ships every clue image byte for
byte in the repo, and its key is split into four independent AES segments, each with an
exact padding test (false-positive rate 2^-64). Progress is therefore provable one segment
at a time, and no step is compute-bound.

Honest prior, stated before starting: well under even odds for a full solve.

## The checking tool

The folder's `tools/oracle.py --selftest` passes here (secp256k1 vectors, both AES layers,
the author's own byte arithmetic, the base64 canonicity check). My search harness
`tools/p2g_seg1.py` uses the identical single-block test: AES-256-CBC, IV
`few_n_far_btween`, plaintext must end in eight `0x08` bytes.

## Segment 1 (`imagine` + `beach`): two certified negatives

### The idea

The folder crossed every 8-digit block written twice (10^8) with ~13,000 hand-built
readings of the clue 6 melody. If `imagine` is pinned to a few values, each `beach` guess
costs one AES block instead of 10^8, so the melody side can be searched generically rather
than by hand.

`beach` family G1: each of the 6 pitch classes of the measured melody
(A# F# B A# F# D# F C# B C# A# A# F# B A#) gets its own digit, injectively (10P6 = 151,200
maps, octaves ignored), and exactly one extra character from `0-9 # b - . + ' , x ^ _ * /`
is inserted at any of the 16 positions. That covers accidentals, octave marks, separators
and two-digit numbers far more broadly than any fixed convention.

### Readings of clue 1 tested

**Lennon.** "Imagine life was taken" = John Lennon, killed 1980-12-08 (12-09 in UK time);
"left a number in its place" = his age, 40; "that number of years past that fateful day" =
2020-12-08, the 40th anniversary, weeks before the demo shipped; "the infamous way" = the
format demonstrated by the printed `19410712`, which is Pearl Harbor ("a date which will
live in infamy") written year-day-month. 8 candidates (2 days × 4 layouts, doubled),
e.g. `2020081220200812`.

**Pearl Harbor.** The printed `19410712` *is* the fateful day; "left a number in its place"
= the death toll; that many years later, written the same way, twice. 14 cited tolls
(2,403 most common) × 2 layouts = 28 candidates, e.g. `4344071243440712`.

### Results

| clue 1 family | candidates | tests | witness | real hits |
|---|---|---|---|---|
| Lennon, 40 years | 8 | 425,779,200 | OK | **0** |
| Pearl Harbor, death toll | 28 | 1,490,227,200 | OK | **0** |

Witness protocol: a genuine G1 string is encrypted under a genuine candidate key, placed
mid-space, and checked in the same AES call as the real ciphertext on every test. Both runs
re-found it. Rate 574,000–585,000 tests/s on 4 cores.

So if `imagine` is either of these readings, `beach` is **not** a one-digit-per-pitch-class
writing of the measured melody with one extra character. Either the clue 1 reading is
wrong, or the melody needs octave-distinct digits, or the notes themselves are wrong.

## Steganography checks the folder had not listed

"This time we change the channel / And traverse to lost dimensions" was read against
`Beach.png` for three standard hiding places. All negative:

- **Hidden rows beyond the header height** (a classic "lost dimensions" trick): IDAT
  decompresses to exactly 412 × 312 rows, no surplus. Same for `Ship.png` and
  `treasure_chest.png`. All chunk CRCs valid, nothing after IEND.
- **The alpha channel** (the folder's "24 bit planes" covered RGB only): fully opaque, one
  value (255) on all 128,544 pixels. Carries nothing.
- **Text and time chunks**: `iTXt` is GIMP's stock "Created with GIMP"; `tIME` is a save
  date, 2021-01-22 15:08:16.

## New observation: clue 8 cross-references clue 5

The clue 8 panel carries small red pictograms in the exact style of clue 5's, which the
folder does not mention:

- bottom: an **anchor** (asterisk beneath) and the **three-headed devil** — clue 5 row 2
  is anchor, ▲, devil, ◄;
- top right: a **banner marked 0,0,0**, an **old TV** (asterisk beneath), **three stars** —
  clue 5 row 3 ends in stars around a question mark;
- top left: a **key**, then a winding path, "?", a square-wave path, "?", and separately a
  **padlock** over a squiggle — drawn like a route on a map.

Clue 5's full poem also has **eight** lines, not four ("Charting the eight wonders", "We
used to swim the same moonlight waters", "Dragged by the force of some inner tide", "No
longer will we wait for your answers"), and one line says "A bit of help from each line".

Hypothesis: each pictogram names an **album track title** (the ghost fits "Ghost March"),
making the pictograms a second index into the album the puzzle already uses as its
dictionary. Testing it needs the full 13-track list, which is not in the repo and cannot be
fetched from here. Six titles are known: Few and Far Between (1), Exit Light (4), Ghost
March (5), All Art Must Die (7), Nocturnal Sugars, Seconds of Dream.

## Where it stands

No segment opened. Two certified negatives on segment 1 (1.92 billion tests), three
steganographic channels ruled out, and one new cross-reference between clues 5 and 8. The
single most useful input from outside would be the album's full tracklist.
