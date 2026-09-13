# LogicBeach "Powerful Moss" (0.55 ETH, Base) — image reconstruction and two corrections

Target: `2-mid-prizes/logicbeach-powerful-moss-0-54eth` in `floflo777/open-crypto-puzzles`.

**Status: NOT SOLVED.** No seed recovered, nothing claimed.

> ## THE CARRIER IS THE ALBUM, NOT THE POAP IMAGE
>
> The dossier's central premise is wrong, and the artist says so in their own words on
> the album page:
>
> > *"A 12-word seed is spread across the 12 tracks of the album. Like a clock, year, or
> > seed phrase, this album has 12 of 'em."*
>
> **One seed word per track.** The POAP clock is thematic art — a clock because the album
> has twelve of something, drawn over the BIP39 wordlist because the prize is a seed
> phrase. The words its numerals happen to overlap are not the seed.
>
> Everything below the divider was built on the dossier's assumption and is now known to
> be aimed at the wrong target. It is kept because the image analysis is correct and
> reproducible, and because the ~1.4 billion negative derivations are what finally proved
> the premise false rather than merely unlucky. See
> **"How the premise collapsed"** for the evidence, and `tools/analyze_tracks.py` for the
> per-track hunt that replaces it.

## How the premise collapsed

Three independent strands agree:

1. **The artist's own description** (above): the seed is spread across the 12 tracks.
2. **Precedent — "Bifurcations" (2020, solved).** The 12 words were extracted *per track*:
   track 1 a spectrogram image plus Morse (`west`), **track 3 Morse played on the drums**
   (kick = dash, snare = dot, around 1:31), track 4 an **SSTV Robot-36** payload; and the
   word *order* was hidden separately, as spoken digits of the Feigenbaum constant whose
   deliberate errors spelled `6 4 2 3 9 7 8 1 5`.
3. **Precedent — the 2021 `.eth` puzzle.** 12 words hidden across 7 tracks, 7 music videos
   and the album cover, all declared "fair play", with the author warning that ears alone
   would not be enough — you also need eyes and a terminal.

This also dissolves the two anomalies this document could measure but never explain:

- The numerals are **not on a fixed-radius circle** (radii 803-871 px, 8.6 % spread) and
  no matplotlib text-alignment convention fits better than ~21 px rms. I read that as
  "hand-placed onto words". The simpler reading, given `Created with GIMP`, is
  **hand-placed for looks** — which is what decoration does.
- The numeral centres land at 22 %, 32 %, 39 %, 46 %, 48 %, 57 %, 60 %, 69 %, 93 %, 98 %
  through their words and twice in a bare gap. A rule that marks words does not scatter
  like that; decoration does.

### The dossier's reason for dismissing the audio does not hold

It records that the masters have "close to 0 percent energy above 13 kHz ... so there is
no high band left to carry spectrogram text". That is true and irrelevant: it rules out
exactly one technique. **Morse on the drums, spoken words, SSTV in the voice band, tempo
and rhythm encodings all live in the audible range.** The artist's own prior puzzle hid a
word in a drum pattern at normal listening frequencies. So the audio was never excluded on
sound grounds.

`tools/analyze_tracks.py` sweeps those techniques per track — drum-Morse (kick/snare),
tone-Morse in three bands, SSTV sync detection, DTMF, LSB payloads, stereo side-channel
content, high-band energy, and contrast-stretched spectrograms in four views. Its
detectors are certified by `--selftest`, which synthesises a track carrying drum-Morse for
a real BIP39 word and confirms recovery, plus an LSB round-trip.

---

## Summary (of the superseded POAP-image analysis)

The dossier holds that the puzzle is a POAP image: a clock face with 12 numerals laid over
the full alphabetical BIP39 wordlist, each numeral marking a word, the 12 words in clock
order forming a mnemonic deriving the winner wallet
`0x635739254BDE27d28301f25aD57c3cAC3C3468f3` at `m/44'/60'/0'/0/0`. The image work below
is sound; the premise it serves is not.

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
| `(117,117,0)` `(177,177,0)` `(83,83,0)` | 32,928 | **grid + ray-edge layer (B zeroed)** |
| `(255,255,117)` `(255,255,177)` `(255,255,255)` | 30,541 | **title lettering (R,G forced to 255, B kept)** |

The last two rows are new. An earlier version of this document listed only the
first seven colours, which account for 3,481,711 of the image's 4,030,044 pixels —
**13.6 % was unaccounted for**, and it hides two whole overlay layers:

- a layer that zeroes only the **B** channel: the matplotlib **grid lines and the
  sunburst ray edges** (rendered and eyeballed, `tools/L_yel.png`);
- a layer that forces **R and G to 255 and preserves B**: the **"POWERFUL MOSS /
  LOGIC BEACH" title lettering** (`tools/L_brt.png`). Because B survives, the text
  under it is exactly recoverable.

This matters beyond bookkeeping. The dossier's **"established fact 4"** states that
a gray-intensity and hue histogram "shows exactly 1 text-gray population and only 2
non-gray hue families", and concludes that this rules **out any distinctly marked
word overlay**. The real image has at least **three** text-gray populations (177
plain, 133 under-numeral, 177-in-B under the title) and **three** non-gray families.
That histogram was wrong, so its conclusion was unsupported — see the direct test
below, which reaches the same conclusion for a real reason.

Two consequences that make everything else possible:

- Overlays override *some* channels only, so the underlying value survives in whichever
  channel is untouched (text under a red ray is `(177,0,0)` — R still 177).
- **Gray 83 is exactly the 12 numerals.** Masking it renders a clean clock face, so the
  numerals can be extracted by connected components rather than guessed at. Gray 133 is
  precisely the text covered by a numeral (117→83 and 177→133 under the same overlay).

### 2. Layout

- 42 text rows, pitch **48 px** (horizontal projection of the text mask). The dossier says
  39 rows; it is 42.
- Monospace cell width **25.5617 px** (autocorrelation, then refined by the global fit below).
- The wordlist is wrapped on a **wide virtual canvas and clipped to the circular disc** —
  each visible row is a contiguous alphabetical run, but consecutive rows skip words,
  because only the middle of each line falls inside the circle. Earlier reconstructions
  (mine and the dossier's) assumed a plain rectangular wrap, which is wrong.
- Each row was identified by matching observed word-box widths (letter counts) against the
  wordlist, then fitting the row origin `X0` so that `x = X0 + CW * column`. Typical
  residual **< 1 px** (e.g. row 18 = `raccoon race rack radar radio rail rain raise rally
  ramp ranch random range rapid rare`).

### 2a. The layout is solved exactly (`tools/layout.py`)

The 28 independently identified rows turn out to obey a single global model. Join the
2048 words with spaces into one 13,116-character stream and **hard-wrap it at exactly
171 characters per line**; then for any character `p` on physical row `i`

    x(p, i) = A + CW * (p - 171*i)       A = -154032.8 px   CW = 25.5617 px

Evidence:

- **CPL = 171.01 +/- 0.13** characters, estimated independently from each of 23
  consecutive identified row pairs. A spread that tight rules out *word* wrapping,
  which would vary the line advance by several characters; this is a hard character
  wrap, so words are split across line boundaries off-screen.
- The top of the image is virtual line **L0 = 35**, agreed by **28 of 28** rows
  unanimously.
- Re-deriving each row's start word from the model alone reproduces **28 of 28** of the
  rows that were identified the hard way, by letter-count matching.

Two consequences the dossier does not have:

1. The wordlist needs **77 lines** but the image shows only **42** (lines 35-76). The
   visible window is roughly the **back half of the wordlist, `inhale` .. `zoo`**. Every
   marked word must lie in that range — words before `inhale` are not on the image at all.
2. Every word's position is now computable in closed form, including for the 14 rows that
   were never identified individually.

### 3. Reading the numerals

Each numeral's glyph is extracted by connected components (two-digit numerals merged), and
the marked word is the one containing the numeral's pixel centroid.

### 3a. The numerals are NOT on a fixed-radius circle

Fitting the 12 numerals to an ellipse at exact 30-degree intervals (`tools/anchorfit.py`,
`tools/aligntest.py`) gives good *angles* (within ~0.5 degrees for most hours) but the
*radii* vary from **803 to 871 px, a 8.6 % spread**, and no matplotlib text-alignment
convention (all 9 combinations of `ha` x `va` were tried) brings the fit below ~21 px rms.

So the numerals were not laid out by clock geometry and then allowed to fall where they
may: **they were snapped onto the words they mark.** This is why the row assignment is
stable but the radius is not, and it means the numeral position is evidence about the
word, not about the clock.

### 3b. The words under the numerals can simply be read (`tools/crops.py`)

Because gray 133 is exactly "wordlist text seen through a numeral", mapping `133 -> text`
and `83 -> background` **removes the numeral and restores the text underneath**. Rendering
each hour's neighbourhood that way, with a crosshair at the numeral's bbox centre, makes
the marked word directly legible instead of inferred:

| hour | reading | crosshair lands |
|---|---|---|
| 1 | `mandate` | on the word, low in the row |
| 2 | `oyster` | on the word |
| 3 | `romance` | on the word |
| 4 | **`strategy`** | mid-word (anchor) |
| 5 | `turtle` | mid-word |
| 6 | `vintage` | on its final `e`, just before the space |
| 7 | `tuition` | on its final `n` |
| 8 | **`stick`** | mid-word (anchor) |
| 9 | `riot` | on the word (confirms Correction 1) |
| 10 | `outdoor` / `outer` | **exactly in the gap between them** |
| 11 | `main` / `major` | **exactly in the gap between them** |
| 12 | **`leisure`** | mid-word (anchor) |

All three published anchors reproduce visually, which validates the render. Ten of the
twelve hours are now read with no ambiguity; only h10 and h11 are genuinely undecidable
from this raster, exactly as the dossier says — but see the next section, because the
alternates were never actually searched.

### 3b-2. Word boxes measured from the pixels (`tools/wordboxes.py`)

The fitted row origins carry ~2.5 px of error, the same order as the h10/h11 ambiguity,
so the model cannot settle them. Segmenting each row's text mask by its column
projection gives the real ink extents, with no model in the loop. Where the numeral
centre falls inside its word:

| hour | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 12 |
|---|---|---|---|---|---|---|---|---|---|---|
| word | mandate | oyster | romance | **strategy** | turtle | vintage | tuition | **stick** | riot | **leisure** |
| position in word | 32 % | 39 % | 46 % | 66 % | 22 % | **93 %** | **99 %** | 61 % | 58 % | 48 % |

h10 falls in the gap between `outdoor` (ends x=301) and `outer` (starts x=336), 6 px
from the gap centre; h11 in the gap between `main` (ends 609) and `major` (starts 638),
1 px from the gap centre. Those two really are undecidable, and both alternates are now
searched.

The useful new signal is **h6 at 93 % and h7 at 99 %**: those numeral centres sit on the
word's trailing edge, which makes the same-row **right neighbours** (`violin`, `tumble`)
live candidates. They rank 4th-5th by distance and so were cut from every candidate list
ever used, including the ranked top-3 below. `tools/hcross.py` therefore sweeps a
candidate set built purely from measured boxes — the word containing the centre plus its
left and right neighbours on the home row, plus the word containing the centre one row
up and one row down. Result: **5,065,447 checksum-valid phrases x 5 paths = 25.3 M
derivations, 0 matches.** The word neighbourhood is now exhausted.

### 3c. A ranked distance metric — and a real gap it exposes (`tools/rankcand.py`)

Ranking *every* word in the rows a numeral spans by 2D distance to the numeral centre
(horizontal distance to the word box, vertical distance to the row centre, vertical
weighted 0.55) is self-validating: the three known anchors come out **top-ranked at the
smallest distances in the whole table** (`stick` 1 px, `leisure` 5 px, `strategy` 6 px).

| hour | ranked candidates (distance px) |
|---|---|
| 1 | mandate(10) mechanic(15) logic(38) |
| 2 | oyster(6) open(24) opera(27) |
| 3 | romance(10) retreat(16) sand(34) |
| 4 | **strategy(6)** squeeze(23) square(24) |
| 5 | turtle(7) unlock(20) trash(31) |
| 6 | vintage(2) waste(25) valve(29) |
| 7 | tuition(4) unique(24) uniform(28) |
| 8 | **stick(1)** spoil(25) sugar(29) |
| 9 | riot(8) require(18) saddle(32) |
| 10 | outer(12) **outdoor(15)** okay(23) |
| 11 | main(15) maze(15) meadow(20) **major(20)** |
| 12 | **leisure(5)** lobster(19) label(34) |

This exposed a genuine defect in every sweep run on this puzzle, mine included. All of
them built candidates as "the nearest word **in** row *r*", then varied only *r*. That
rule returns **one word per row**, so the horizontal alternates at precisely the two
ambiguous hours — **`outdoor` at h10 and `major` at h11** — were *never in any candidate
list*, despite both being named in the best-reading table as live alternatives. The
"horizontal neighbours" sweep in the ledger held the rows fixed at centre, so it did not
cover them either. The vertical and horizontal ambiguities had never been crossed.

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

## Correction 2 — the BIP39 checksum, and how to use it

The published ledger records testing "1,193,373 combinations (**132,597 checksum-valid**)";
all my earlier sweeps did the same. BIP39 seed derivation is `PBKDF2` over the phrase — the
checksum is only a validity flag that wallets enforce, not part of the derivation — so a
checksum-invalid phrase still derives a perfectly real wallet, and would be invisible to a
filtered search. That is why every sweep in the table below was run **unfiltered**.

An earlier version of this document stopped there and treated the checksum purely as a blind
spot. That was half the picture, and the weaker half. The stronger argument runs the other
way and is worth stating plainly, because it changes what to search:

**The artist funded a real wallet.** Nobody marks 12 arbitrary words and hopes the result is
checksum-valid — that is a 1-in-16 shot. You generate a mnemonic in a wallet or a tool, get a
valid one by construction, and *then* place those 12 words on the clock. So the true phrase
should be checksum-**valid**, and the checksum is a strong prior and a 16x speedup, not just
a trap.

That produces a sharp tension, because the geometric reading is **invalid** — and so are all
four combinations of the two ambiguous hours:

| h10 | h11 | checksum |
|---|---|---|
| outer | main | invalid |
| outer | major | invalid |
| outdoor | main | invalid |
| outdoor | major | invalid |

So on this model at least one of the ten "certain" words must be misread, **or** the phrase
was passed through a checksum repairer. Both branches are now searched:

- **Mechanism A — the true reading is checksum-valid.** Enumerate ranked candidates and keep
  only valid orderings (`tools/csweep.py A`).
- **Mechanism B — checksum repair.** What Ian Coleman's BIP39 tool and most "fix checksum"
  utilities do: keep the 128 entropy bits, recompute the 4 checksum bits. This changes
  **only the final word** (`tools/csrepair.py`, certified: identity on an already-valid
  mnemonic, always valid out, never alters more than the last word). For the primary reading
  it turns `... outer main leisure` into `... outer main leave`.
- **One word free anywhere.** If ten hours are right and exactly one word is wrong, the
  checksum cuts the 2048 replacements to ~128, so "one word misread and it could be **any**
  word in the list" is searchable in minutes — far broader than the +/-2-row windows every
  previous sweep used (`tools/onefree.py`).

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
| Non-rotational orderings (reading / column / alphabetical) x +/-1 space | 3.19 M derivations | 0 |
| **+/-2 window (full glyph span) x 30 orderings**, no checksum | **58.59 M derivations** | **0** |
| **One anchor free to +/-2, others +/-1, x 30 orderings** | **63.77 M derivations** | **0** |
| Readings x 34 orderings (incl. album-track perms) x raw/repaired x 29 passphrases x 18 paths | 709,920 derivations | 0 |
| **One word free anywhere in the 2048-word list**, 20 readings x 30 orderings x 12 positions, checksum-valid only, x 18 paths | **922,981 valid phrases = 16.6 M derivations** | **0** |
| **Mechanism zoo**: 125 derivation mechanisms (BIP39, Electrum seed, raw-seed BIP32, 6 brainwallet hashes x 2 joins, 5 entropy-to-key schemes) x 8 readings x 34 orderings x raw/repaired | 68,000 derivations | 0 |
| **Ranked candidates x 30 orderings, checksum-valid only, 18 paths** (first sweep containing `outdoor` and `major`) | **2,214,273 valid phrases = 39.9 M derivations** | **0** |
| **Measured-box candidates** (home-row left/right neighbours + rows +/-1) x 30 orderings, checksum-valid, 5 paths | **5,065,447 valid phrases = 25.3 M derivations** | **0** |
| Numeral position-within-word used as letter indices (3 rounding conventions x both gap alternates) as passphrase and as direct key | 7,056 candidates | 0 |
| **FULL 12! over all four reading variants**, checksum-filtered, 5 paths | **1,916,006,400 orderings enumerated; 119,755,757 checksum-valid = ~599 M derivations** | **0** |
| **Global layer offset** (dx -260..260, dy -192..192) x 34 orderings x raw/repaired x 18 paths | 554 distinct readings, 678,096 derivations | 0 |

Cumulative: **over 700 million certified derivations**, zero matches.

The one-word-free result is the sharpest of these. It says: if ten hours are read
correctly and the phrase is checksum-valid, then **no single substitution anywhere in
the wordlist** — in any of 30 orderings, at any of 18 paths — reaches the winner. So
either two or more words differ from the visual reading, or the derivation is not any
of the 125 mechanisms tried.

### The anchors were tested too

The three "confirmed" hours are not independent evidence — they come from the published
analysis's own visual judgement using the *same* centroid rule applied here, so validating
the rule against them is partly circular. Every other sweep held them fixed, meaning a
single misread there would invalidate all of it. That was tested directly: each anchor in
turn allowed to be up to 2 rows off (h12 -> `label`/`lobster`/`mammal`, h4 ->
`squeeze`/`supreme`/`tag`, h8 -> `spoil`/`sugar`/`swing`) with every other hour at +/-1,
across all 30 orderings — 63,772,920 derivations, 0 matches.

## All three published leads are now closed

**Lead 1 — widen the row window.** The published note reasons from "a serif numeral spans
about 2 text rows", so it used a +/-1 window. Measured directly, each digit glyph is
**~242 px tall = ~5 text rows** at the 48 px pitch, so +/-1 never covered even half the
numeral's vertical extent. I ran the exhaustive +/-2 pass (the numeral's full span): 5
candidates per hour on the corrected grid, anchors fixed, 1,953,125 word-sets x 30
orderings (24 rotations + reading/column/alphabetical), no checksum filter =
**58,593,750 derivations, 0 matches**. By the lead's own stated kill criterion
("widening every doubtful hour ... with no match closes this specific readout rule"),
the numeral-overlays-word rule is now **closed** — and this went further than proposed,
widening all hours simultaneously rather than one at a time.

**Lead 2 — sample the numeral's bottom pixel.** Refuted analytically, no brute force
needed: h12's glyph spans y44-291, so its bottom edge lands in row 6, which would
contradict the confirmed `leisure` in row 3. The centroid is the only sample point
consistent with all three anchors.

**Lead 3 — sunburst ray length as a selector.** Refuted by measurement. The rays sit at
exact 15 degree intervals (24 of them). Their outer radii are **980-989 px — a 1 %
spread** — i.e. they all simply terminate at the disc edge; inner radii are likewise
uniform (35-41 px). The four "thin" spokes at 0/90/180/270 degrees are the coordinate
axis lines (the -10/-5/5/10 labels), not sunburst rays. There is no per-ray signal to
carry a selection or ordering.

The lead named *length*, so ray **width** was also measured, to close the remaining
degree of freedom (`tools/raywidth.py`). Angular width does vary — 10.23 to 12.41
degrees, a 19 % spread — but it is **not per-ray information**: the values repeat with
a period of exactly 6 rays (90 degrees), so ray 0/6/12/18 = 10.49/10.46/10.40/10.23,
ray 3/9/15/21 = 12.37/12.40/12.41/12.41, and so on. Width is a pure function of
angle modulo 90 degrees, i.e. an artifact of sampling a fixed-width wedge on a square
pixel grid. Hour-aligned and between-hour spokes are indistinguishable (mean width
11.53 vs 11.41 degrees). **Lead 3 is closed on both length and width.**

## The PNG container, the alpha channel, and the absent clock hands

Three cheap checks that had not been recorded, all negative but worth closing:

- **Container.** `powerfulmoss-poap.png` (sha256 `6742c3c8...`) has chunks IHDR, iCCP, bKGD,
  pHYs, tIME, tEXt, IDAT x94, IEND, and **zero bytes after IEND**. The only text chunk is
  `Comment: Created with GIMP`; `tIME` is **2024-08-23 17:37:02**, five months before the
  2025-01-17 launch. No stego payload in the container.
- **The GIMP comment is substantive**, though: the artwork was composited in an image editor,
  not emitted straight from matplotlib. That independently explains section 3a — hand-placed
  numerals are exactly why the 12 radii scatter over 8.6 % instead of sitting on a circle.
- **Alpha channel.** The file is RGBA, and 915,246 pixels are fully transparent — I had been
  discarding alpha with `convert('RGB')` throughout. Checked directly: every transparent
  pixel is RGB `(0,0,0)`, so **nothing is hidden under the transparency**, and alpha is just
  the disc mask (246 distinct values, 6,568 partial, i.e. an antialiased edge).
- **There are no clock hands.** The palette note called black "outside disc / hands", but
  masking black inside radius 940, 900 and 800 px of the disc centre returns **0 pixels** in
  every case. The clock has no hands, so there is no hand-based ordering signal to find.

## The "no distinctly marked word" claim, tested properly (`tools/inkscan.py`)

The dossier's fact 4 asserts no word is distinctly marked, but rests on a histogram that
missed two whole layers (above). So the claim was re-tested directly rather than trusted:
for all **305 complete word boxes** across the 28 reconstructed rows, count text pixels and
normalise by box area — a bolded, recoloured or otherwise emphasised word must show
anomalous ink density.

Result: mean density 0.186, sd 0.092, and **every outlier is explained by a known overlay**.
The high tail (`search` z=+3.3, `sail`, `scrap`, `scrub`, `salmon`, all in rows 22-23) sits
directly under the "LOGIC BEACH" title lettering, which adds ink; the zero-density tail
(`lamp`, `leopard`, `vault`, `winner` ...) is words clipped away by the disc. Controlling
for word length changes nothing.

**No word is distinctly marked.** The dossier's conclusion holds — but now for a measured
reason instead of a faulty histogram.

## The ordering question is now closed

The full 12-factorial ordering space has been exhausted for **all four** reading
variants (`outer`/`outdoor` x `main`/`major`), not just the one in the ledger:
**1,916,006,400 orderings enumerated, 119,755,757 checksum-valid, each derived at 5
paths — about 599 million derivations, 0 matches** (`tools/perm12.py`, checkpointed;
its index-level checksum test certified against the oracle on 3,000 random phrases
plus the KAT).

So "the words are right but the order is wrong" is dead. The twelve words that are
legibly under the twelve numerals do not derive the winner wallet **in any
arrangement whatsoever**, with or without a valid checksum, at any path tested.

## The layer-offset hypothesis, and why it mattered

The `Created with GIMP` chunk means the artwork was composited from layers. If the
wordlist text layer and the numeral layer were shifted relative to each other before
flattening, then every numeral points at the wrong word *by the same offset* — and
this is undetectable from the image, because the three "confirmed anchors" come from
the same centroid rule and are displaced along with everything else. No amount of
internal consistency checking can catch it; the reading is self-consistent at any
offset.

Tested directly (`tools/globaloffset.py`): a global (dx, dy) applied to all 12 numeral
centres, dx from -260 to +260 px (about +/-10 character cells) and dy from -192 to
+192 px (+/-4 rows), yielding **554 distinct 12-word readings**, each crossed with 34
orderings, raw and checksum-repaired, at 18 paths — 678,096 derivations, **0 matches**.
The reader is certified: at offset (0,0) it reproduces `leisure`@12, `strategy`@4 and
`stick`@8 exactly.

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

### Where this leaves the puzzle

Every axis of the documented mechanism has now been searched to exhaustion:

| axis | coverage | result |
|---|---|---|
| **which word** | measured boxes, ranked 2D distance, rows +/-2, both horizontal neighbours, one word free **anywhere in the 2048-word list**, and a global layer offset of +/-10 cells / +/-4 rows | negative |
| **what order** | **all 12! arrangements** of all four reading variants | negative |
| **how derived** | 125 mechanisms (BIP39, Electrum, raw-seed BIP32, brainwallet hashes, entropy-to-key), 18 paths, 29 passphrases, checksum-repair | negative |
| **what target** | decoded from contract bytecode — hardcoded, confirmed | correct |

These are not near-misses being narrowly missed; they are exhaustive over their spaces.
The conclusion is therefore structural rather than computational: **the published model
of this puzzle is wrong somewhere** — in the carrier, in the word-selection rule, or in
the assumption that the twelve marked words are themselves the mnemonic.

That is not a wild claim about this particular dossier, because several of its stated
facts have already failed direct measurement in this document: its colour census omits
13.6 % of the image and two whole overlay layers; its "established fact 4" rests on that
faulty census; its row count (39) is wrong (42); its plain-wrap layout model is wrong (a
hard 171-character wrap of which only 42 of 77 lines are shown); and its claim that the
row can "only be pinned to within 1 row" is wrong — the words are directly legible once
the numerals are removed.

What would actually move this forward is **new evidence, not more compute**: the artist's
own statement of the rule, a solver write-up, the original layered source (PSD/XCF) rather
than the flattened PNG, or any independent confirmation of even one of the twelve words.
Absent that, further brute force is searching spaces that have already been closed.

## RESOLVED: the target address is correct (contract decoded)

This was the last unverified assumption, and it is now settled. The prize contract's
runtime bytecode was read via `eth_getCode` and decoded. `withdraw()` (selector
`0x2f0c39ec`) contains literally:

    PUSH20 635739254bde27d28301f25ad57c3cac3c3468f3    <- winner
       ... EQ CALLER ... OR
    PUSH20 035032655b5b3784d359b56eb82c803bd971c582    <- owner (early-withdraw path)

with the revert string **"Only the winner can withdraw the pot"**. So
`0x6357...68f3` is hardcoded as the winner. Other constants decoded from the bytecode all
match the published description, confirming the decode: launch `0x678ab6c0` =
2025-01-17 20:00:00 UTC, minimum claimable `0x03782dace9d90000` = 0.25 ETH, mint price
0.001 ETH, growth window `0x4f1a00` = 60 days.

**Consequence:** the negative results above are real. The search was aimed at the right
wallet, so the defect lies in the readout rule, not the target.

## RESOLVED: the NFT-gated CID contains no finer artwork

The contract has a second, separate string in **storage slot 8**, returned by `getCID()`
and gated on `balanceOf(msg.sender) > 0` plus the launch timestamp — distinct from
`baseURI` (slot 10), which is what `tokenURI` returns and all the published analysis ever
checked. The gate exists only in the getter, so the slot is readable by anyone via
`eth_getStorageAt`:

    slot  8 (gated CID) = https://ipfs.io/ipfs/QmXpuV2psiXPoGF4Ac6KwTA2KE6U3rwUnn3izAHWmAfWKb/
    slot 10 (baseURI)   = https://ipfs.io/ipfs/QmXuC6cLqXkq4puj8BoxrqDjxVD9jUmUdKaUNjjJX8jasw/

This was worth chasing because the published notes state *"no source of the plot finer than
the published 2004x2011 raster is known to exist"* — and they never opened slot 8.

Contents (a 488,260,402-byte ZIP), enumerated in full:

    Powerful_Moss/PowerFulMoss_savedCover_after_crash.png   484,726   album cover art
    Powerful_Moss/<12 tracks>_final.wav                     12 lossless masters
    __MACOSX/._*                                            12 resource-fork stubs
    Powerful_Moss/.DS_Store                                 no ghost filenames

Despite the suggestive "savedCover_after_crash" name, the PNG is the **album cover
artwork** (forest scene, title lettering) — not the clock-and-wordlist plot. The 24 audio
entries are 12 WAV masters plus their 12 macOS `._` stubs, i.e. the same 12 masters
already analysed and found empty. **There is no higher-resolution source of the clock plot
in the gated content**, so the raster ambiguity cannot be resolved this way.

## Files

    tools/moss_oracle.py   independent BIP39 -> BIP44 ETH oracle, certified against the
                           all-zero-entropy KAT (0x9858EfFD...) with +/- controls
    tools/numerals.py      extracts the 12 numerals (gray 83) by connected components
    tools/allrows.py       identifies each text row's wordlist run and fits its origin
    tools/final_read.py    picks each numeral's word by under-numeral pixel overlap
    tools/final_sweep.py   vertical +/-1 sweep over all 12 hours x clock orderings
    tools/hneigh.py        horizontal-neighbour sweep
    tools/flowfit.py       global continuous-flow test; recovers CPL = 171.01 +/- 0.13
    tools/layout.py        exact layout model (hard wrap, CW, L0); 28/28 rows reproduced
    tools/crops.py         de-obscures each numeral so the word under it can be READ
    tools/rankcand.py      ranked candidates by 2D distance to the numeral centre
    tools/anchorfit.py     ellipse fit to the 12 numerals
    tools/aligntest.py     matplotlib ha/va anchor-convention model selection
    tools/inkscan.py       per-word ink density; tests the "marked word" claim directly
    tools/csrepair.py      BIP39 checksum repair (certified)
    tools/pathcross.py     shared-seed prefix tree over 18 derivation paths (certified
                           path-by-path against direct derivation)
    tools/csweep.py        ranked-candidate sweep, checksum as prior, 18 paths
    tools/onefree.py       one-word-free-anywhere search using the checksum as a solver

    figures/L_yel.png      the grid + ray-edge layer, isolated
    figures/L_brt.png      the title-lettering layer, isolated
    figures/crop_h12.png   de-obscured h12 -> crosshair squarely on `leisure`
    figures/crop_h10.png   de-obscured h10 -> crosshair in the `outdoor`/`outer` gap
    figures/crop_h11.png   de-obscured h11 -> crosshair in the `main`/`major` gap

The oracle is self-certifying: any candidate deriving the winner wallet is proof. Nothing
in this document is a claimed solve.

## Track 1 analysed in full — clean

`1 generative adversarial neurology_final.wav` (48 kHz, 16-bit stereo, exactly
3,456,000 samples = 72.000 s) is the most anomalous track on metadata: 16-bit in a
24-bit album, a third the length of the others, and a spectrogram of ~13 discrete
harmonic blocks that looks constructed. Every test is negative:

| test | result |
|---|---|
| RIFF container | bare `fmt` + `data`, no metadata chunks, **0 bytes after the last chunk** |
| LSB bit-planes 0-3, both channels | ones = 0.4993-0.5004, lag-1 corr < 0.009, byte entropy **8.000/8** — ordinary dither, no payload |
| spectrogram: mono, L, R, **side (L-R)** | harmonic drones only; side channel carries nothing distinct (L/R corr 0.39) |
| reversed, lead-in 0-5 s, tail 67-72 s | nothing |
| top band 13.5-24 kHz | narrow lines present but local prominence only **~2x** — harmonics of the synth, not planted carriers |
| fundamental-pitch sequence | sparse bass drone (C2 / G#1 / F2), not a data sequence |
| drum-Morse, tone-Morse, DTMF, SSTV | noise (300+ onsets = a groove, not Morse) |

So the per-track payload, if it exists, is not in track 1 — or is not carried by any
of these mechanisms.

## The NFT-gated cover PNG — clean

`PowerFulMoss_savedCover_after_crash.png` (484,726 bytes, sha256 `e9e29ebc...`,
732x731 RGB, `tIME` 2024-09-01 23:27:45) sits behind the NFT gate in storage slot 8,
which the published analysis never opened, and its filename ("saved cover **after
crash**") reads like a deliberate hint. It is nevertheless clean:

- **Container**: IHDR, iCCP, pHYs, tIME, 60x IDAT, IEND. Every CRC valid, **0 bytes
  after IEND**, no `tEXt`/`zTXt` (note: unlike the POAP, no GIMP comment).
- **LSB planes**: neighbour agreement 0.66-0.72 horizontally and vertically, i.e.
  spatially correlated like natural image content. A written payload would sit at 0.5.
- **Shadow stretch** (bottom 35 % of the tonal range): forest scene only.
- **Channel differences** R-G, G-B, R-B: only the same artwork and lettering, no
  separated layer — the technique that exposed four overlay layers on the POAP finds
  nothing here.
- Bottom band at native resolution: pixel-art foliage, not glyphs.

## Track titles as a carrier — negative

Every one of the 12 titles contains a BIP39 word as a substring (`power`, `rare`,
`curve`, `forest`, `cliff`, `shadow`, `antenna`, `empty`, `comfort`, `era`, `fall`,
`man`), which is suggestive until you note that BIP39 contains many short words, so
most English phrases do. All 288 combinations x 34 orderings x raw/repaired x 18
paths = **352,512 derivations, 0 matches**. The track-order reading
(`era power man empty rare comfort curve forest fall cliff shadow antenna`) is also
checksum-invalid.

## The album video — analysed in full (33:04)

Fetched by the user (YouTube is blocked by this session's egress policy: the proxy
returns 403 on CONNECT) and analysed locally at 256x144, 23.976 fps, **47,575 frames**.

### The video is exactly the twelve tracks, back to back

The track durations measured from the WAVs sum to **1984.42 s**; the video runs
**1984.27 s**. So every track maps to a known span of the video:

| track | span | | track | span |
|---|---|---|---|---|
| 1 generative adversarial neurology | 00:00-01:12 | | 7 curved horizon | 14:42-18:03 |
| 2 powerful moss | 01:12-04:23 | | 8 dark forest | 18:03-21:20 |
| 3 too many bees | 04:23-07:02 | | 9 falling up | 21:20-24:29 |
| 4 empty long waves | 07:02-10:47 | | 10 cliffside | 24:29-27:45 |
| 5 temporare | 10:47-12:49 | | 11 shadow realm | 27:45-30:22 |
| 6 discomfort meditation | 12:49-14:42 | | 12 gravitational wave antannae | 30:22-33:04 |

Near-black frames cluster at 07:02 and 18:03, matching the boundaries exactly.

### The intro is a title card sequence, and it states the mechanism

Read frame by frame from 00:00 to 00:39:

> **LOGIC BEACH** / *Presents* / **Powerful Moss** / **12 songs** / **12 seed words** /
> **1 ETH** / *Can you solve it?*

This is the artist's own statement of the puzzle, rendered in the work itself, and it
confirms the correction above: twelve songs, twelve seed words. It is promotional
text, not the answer.

### Frame-level scan

A full-rate pass over all 47,575 frames recording per-frame brightness, contrast,
bright/dark fractions and inter-frame difference found only **3 isolated single-frame
flashes** and **1 text-card candidate** — all four inspected, all ordinary animation.
Median inter-frame difference is 26.5, i.e. the video is continuously morphing
AI-generated animation rather than static art per track, so a hidden frame cannot hide
in stillness.

Tesseract 5.3.4 OCR was calibrated against the known intro text and **fails at 144p on
this stylised, texture-embedded lettering** (it renders "Can you" as "CON Yer"). A
full 1 fps OCR sweep filtered for BIP39 tokens was run regardless.

### OCR sweep of the video — negative

Tesseract over all 1,984 one-second frames in two polarities (~4,000 OCR calls) flagged
55 frames containing a BIP39 token. **All are hallucinations on repetitive AI-generated
texture**, not text:

- The same frame at 25:22 yields `riot` in one polarity and `birth` in the other. Real
  lettering does not change when you invert the image.
- Surrounding output is meaningless (`AG OLR 3 sail y | 1} Lon`).
- The 00:10 hit "TOWER" is Tesseract misreading the scrawled *Powerful* title card.
- Four of the strongest hits (02:22 `seed`, 25:22, 26:39 `SALT`, 29:55 `CASE`) were
  inspected directly: a robot and three cityscapes, **no text in any of them**.
- A 1.4 % hit rate across ~4,000 calls is the expected false-positive rate for a 2048-word
  list full of short common words.

**No seed words are displayed anywhere in the video.** It is a promotional album video
whose only real text is the 39-second title sequence. The carrier remains the audio.
