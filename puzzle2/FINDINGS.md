# Findings from the real 720p60 footage

Source: itag 311 renditions (1280x720, 60fps, 1800 frames, 30.00s each) of
`TRUUTryah70` (part 1), `U_0DtYHDPy0` (part 2), and `0jJ6XadOAWk` (Puzzle #1's
solution screen, used to build the labelled template library).

## Settled: the source

720p60 is the ceiling. `yt-dlp -F` on all three videos lists nothing above
1280x720; itag 311 (~664-842 kbps) is the best stream and is what these findings
use. The upstream note that "only itag 18 (640x360, 30fps) is served" is wrong.

## Settled: the template library

Puzzle #1's solution screen reads
`4487FC620AD0C4C67E80BE342B2EA1F5A3DC482BE6FB9C2451007322EA8BE35F`, matching the
published answer. Averaging its stable hold (frames 1320-1700) and segmenting
yields exactly 64 components, all 16 hex digits, **100% self-classification**.
The display face used for the payload glyphs is close enough to the solution
screen's face to classify against: part 1's static decoy glyph scores 0.654 as
`4` with a 0.344 margin over the runner-up.

## Settled: the payload glyphs wrap the frame edge

Part 1's seam-A glyphs are split across the left/right frame boundary. Rolling
the frame by half its width rejoins them and **the strokes align exactly across
the join** -- a closed `0`, a clean `A`, a clean `B`. Seam-A glyphs are rotated
90 degrees (corrected with `np.rot90(k=3)`).

The upstream ledger's row 7 concluded the payload does *not* wrap and dismissed
wrap-joined readings as chimeras that manufactured phantom `R`/`U` shapes. That
conclusion does not survive the higher-resolution source. (The one `R`-looking
frame in seam A is a crossfade between two characters, not a glyph.)

## Settled: the fragment is real

Seam A, read frame by frame with the wrap-join, gives
**`6 A 6 B 0 8 6 0 ... B ... 4`** -- independently reproducing `6A6B0860B4`,
which the upstream ledger had withdrawn ("No reading is claimed"). It was
withdrawn on 360p evidence.

The long runs of `4` following each reveal are the static decoy the author's own
README describes, not payload. Fitting and subtracting it leaves nothing new.

## Settled: part 2

- Static block (frames 1220-1549): exactly **8 components** -- two payload
  characters (`8` and `C`, at y240-334) plus the six letters of the word
  MIRROR (y446-480). Confirms the upstream `C`/`8` reading.
- Alternating column (frames 1550-1618): three states cycle X->Y->Z->Y->X.
  `corr(Y, max(X,Z)) = 0.9996`, so **Y is exactly X overlaid with Z** and X, Z
  are the two separate layers.
- The column window is hard-cut: x 622-656 (34px) per state, widening to 47px
  when all states are combined, against a ~65px character width.
- The column does not scroll, and rotating it does not produce a text line.
- **Superseded below.** X and Z are not two independent strings but the two
  halves of one; joined, the column reads `723504`. See "The column is a split
  glyph, and it joins".

## The blocking result: there are not 64 character-slots in these videos

Exhaustive per-frame scans of both videos (glyph-shaped components, all frames)
find payload in only these places:

| Source | Character slots | Readable |
|---|---|---|
| Part 1 seam A (1220-1260) | 10 | **10** -- `6A6B0860B4` |
| Part 1 seam B (1455-1496) | 10 | **10** -- `6A6B0860B4` again, the same ten characters re-encoded (see below) |
| Part 2 static block | 2 | **2** -- `C`, `8` |
| Part 2 column | 6 | **6** -- `723504` (see below) |
| Everything else | 0 | title cards, the `4` decoy, and background fog |

**Total distinct slots present: 18. Total confidently read: 18.**
(Seam B repeats seam A, so the two seams together carry ten characters, not
twenty.)

Exhaustively verified: every remaining edge-activity burst in part 1 (frames
147-193, 800-855, 996-1007, 1104-1136) and every glyph-component run in part 2
(12-102, 110-172, 288-306, 716-726) contains only title cards, the static `4`
decoy, or background fog -- no payload.

Every glyph that physically exists in these two files has now been read. That is
18 of the 64 characters. The remaining 46 are not in the published footage at
any resolution, because there is nowhere in either video that they appear.

With 46 characters unknown the search space is 16^46 = 1.1e55. That is not
reachable, and `assemble.sweep()` refuses it.

## What this means

The reading is no longer the bottleneck at all: everything present has been
read. The bottleneck is that the footage does not contain the whole key.
Puzzle #2 as published does not appear to be solvable from these two videos
alone. What would change that is a source showing more than these files do, or a
mechanism (not visible in the frames) that expands the 18 recovered characters
into 64.

## The two seams are one message, split twice

Part 1 carries its ten characters twice, through two independent splits, and
both splits use the same trick: **the glyph is cut in half and the two halves
are shown at different times, 19 frames apart.**

- **Seam A** (frames 1220-1260): the right-edge stream runs 19 frames ahead of
  the left-edge stream. `hstack(right_band(f), left_band(f + 19))`, rotated 90
  degrees clockwise, produces ten complete, unambiguous characters:
  **`6A6B0860B4`**.
- **Seam B** (frames 1455-1496): the same characters cut by the top and bottom
  edges instead, the same 19-frame lead.
  `vstack(bottom_band(f), top_band(f + 19))` produces them upright:
  **`6A6B0860B4`**.

Ten distinct top-edge states and ten bottom-edge states, each held 2-3 frames,
then the composition freezes and fades. There is no eleventh character.

An earlier entry here recorded seam B as "bottom halves only, no wrap
counterpart, 0 confident". That was wrong: the counterpart exists, it is just
offset in time rather than in space. `tools/video/decode_real.py` reproduces
both strips.

## The column is a split glyph, and it joins

Part 2's column (frames 1551-1619) alternates between two still images every
~8 frames, with the union appearing on the crossfade frames. Both images are
identical every time they recur (Jaccard 0.997 between repeats), so there are
exactly two layers.

They are not two strings. They are the two halves of one:

- state **A** carries each glyph's right part, cut at x=622;
- state **C** carries the left part, cut at x=663.

The two cuts fall at the *same point within the glyph* -- which is why the two
cut columns are the same cross-section. Comparing them directly, they agree at
**Jaccard 0.93 at a vertical offset of -1 px**, and the best offset is a sharp
peak. That is the test that decides the join; a wrong pairing does not produce
it.

`hstack(state_C[:, 617:664], state_A[:, 622:658])` rejoins them into complete
characters, six of them at a pitch of 82 px, reading **`723504`**:

    7  2  3  5  0  4

The strokes run continuously across the seam (the `7`'s bar and diagonal, the
`3`'s two bowls), which is the visual confirmation of the numerical one.

Earlier entries here recorded the column as "truncated to ~half width, not a
readable result" and "each layer holds ~7-9 characters". Both are superseded:
the truncation is real but complementary, and there are six characters, not
14-18.

## Correction to the Puzzle #1 control

The control experiment above is right that Puzzle #1's statement A carries a
faint horizontal line and that spatial high-pass on a frame average reads it.
It is wrong about how much that line carries.

Averaging all 870 frames of statement A's static hold and high-passing gives a
line of exactly **39 components**, x 133-1235, y 360, reading

    4487FC620AD0C4C67E80BE342B2EA1F5A3DC482

-- positions 1-39 of the published answer, fading progressively to the right and
stopping (there is blank frame to the right of the last `2`; the line is not cut
off by the frame edge).

Statement B carries a **different twelve**: two rows of six, rendered mirrored,
which un-mirror to `07322E` and `A8BE35` -- positions 52-63.

That is 51 of 64. Positions 40-51 and 64 are in neither video's main
composition. They do appear, at very low opacity, in a **rotated, scattered
layer visible only in statement A's final ~20 frames**: averaging frames
1181-1200 and high-passing shows large 90-degree-rotated characters (`B`, `9`,
`C`, `0`, `0`, `1`, `5`, `4`) plus a rotated column reading `0073 22EA`, all of
which belong to the missing span `BE6FB9C24510`.

Two things follow, and they are the reason this correction matters:

1. **The author does render the whole key, but not all of it in one place, one
   orientation, or one opacity.** A single carrier per video is not the pattern;
   a main carrier plus a low-opacity transition layer is.
2. **Puzzle #2 has no such transition layer.** The same deep-average +
   high-pass, applied to every transition window in both Puzzle #2 videos
   (300-720, 730-1160, 1170-1215, 1380-1450, 1620-1700, 1700-1800, and the
   final 60 frames of each), returns title cards, the scene's geometric
   overlays and background texture -- no glyphs. The census of 18 stands.

## The control experiment (Puzzle #1's statement videos)

Puzzle #1's answer is published, so its statement videos are a ground-truth
control: whatever mechanism hides a full 64-character key there should also be
hiding Puzzle #2's.

**Result: the control worked, and it rules Puzzle #2's mechanism out.**

Puzzle #1 hides its key as a **faint, static, low-contrast horizontal line of
small text across the vertical centre of the frame** (y 352-374) in statement
video `3l1jFa3Mw0s`. A spatial high-pass (subtract a 25px uniform filter from a
frame average, then percentile-stretch) reads it directly:

    4487FC620AD0C4C67E80BE342B2...

matching the published answer's opening. (Superseded in detail by "Correction to
the Puzzle #1 control" above: that line carries positions 1-39 only, statement B
carries 52-63 mirrored, and 40-51 plus 64 appear in a low-opacity rotated layer
in statement A's final frames.)

Two things follow.

**The method is validated.** Temporal background subtraction actively destroys
this kind of payload -- a static faint line is voted into the median background
and subtracted to nothing. Spatial high-pass on a frame average is what recovers
it. That is why the earlier passes over Puzzle #2 could not have found such a
line even if one existed.

**Puzzle #2 does not use this mechanism.** With the validated method applied
exhaustively to both Puzzle #2 videos -- every 100- and 150-frame window, every
row band, the exact centre row that carries Puzzle #1's line, and the tail
frames after the column -- there is no hidden text line. The centre band at the
most promising window is background texture, not glyphs. Puzzle #2's payload is
only what the census above lists: the two edge seams, the static block, and the
truncated column.

This closes the most promising remaining lead. Puzzle #1 renders its key
directly and completely; Puzzle #2 renders a partial key through truncating
windows, and the missing characters are not hidden elsewhere in the frames.

## Higher-bitrate renditions (3x) change nothing structural

A second pair of renditions of Puzzle #2's videos, roughly 3x the bitrate of the
itag 311 streams and encoded differently, was tested:

| | itag 311 | higher-bitrate pair |
|---|---|---|
| part 1 | 469 kb/s, h264 **High** | **1324 kb/s**, h264 **Main** |
| part 2 | 419 kb/s, h264 High | **1351 kb/s**, h264 Main |

The profile change (High -> Main) means these are not simply a better YouTube
transcode of the same ladder; they are a different encode, plausibly closer to
the author's original upload. That makes them the strongest available test of
whether compression was destroying the evidence.

It was not.

- **No hidden text line.** The band-wise high-pass search was first fixed
  against ground truth: stretching each row band separately (rather than the
  whole frame) is what makes Puzzle #1's line detectable, showing 32-34
  components at y 336-350. A whole-frame stretch misses it entirely, which is
  why an earlier version of this search produced a false negative. With the
  corrected, ground-truth-validated detector applied to the higher-bitrate
  Puzzle #2 pair, the only recurring band is y=434, and it resolves under
  inspection to background fog and the scene's geometric overlay lines --
  component heights scatter from 6 to 15px, against the control line's uniform
  run. There is no text line in Puzzle #2 at any bitrate.
- **The truncation is geometric, not compression.** The column's bounding box is
  identical in both encodes: x 617-663, width 47px. Tripling the bitrate does
  not widen it by a pixel, because the window edge is baked into the footage.
- **Seam A re-confirms.** The same glyph sequence reads `6 A 6 B 0 8 6 0 ... 4`
  from the higher-bitrate source, reproducing `6A6B0860B4` a third time.

This rules out the last mechanism by which the missing characters could have
been present but unreadable. They are absent, not degraded.

## Audio ruled out

All nine video files obtained were video-only itags (311/298), so the audio
tracks went unexamined until now. Spectrogram steganography is common in this
genre, so this was a real gap. It is now closed, and the control settles it
decisively:

- **Puzzle #1's statement video A -- the one carrying its full key -- has a
  completely silent audio track** (all samples zero, verified). The author
  demonstrably does not hide payload in audio.
- Puzzle #2's two tracks are ordinary music, correlating 0.98 with Puzzle #1's,
  with the usual AAC lowpass near 16 kHz and an empty band above 15 kHz
  (mean magnitude 0.0013) where spectrogram text would live.
- The two Puzzle #2 tracks differ in only 13,075 of 1,443,353 samples, confined
  to a 0.46s burst at 20.53-20.99s. Its spectrogram is scattered unstructured
  blobs at -41 dB relative to signal: AAC quantisation noise at a loud
  transient, not a payload.

## Other hypotheses tested and rejected this round

- **Column glyphs are complete.** Rejected. An earlier `edge_report` reading of
  `cut=False` was the taper test being fooled by curved glyph edges; rendering
  layer X at 7x magnification shows hard vertical cuts on both sides. The
  column is truncated, as originally assessed.
- **The two videos combine.** Rejected. Their payloads never coincide in time --
  part 1 shows only fog during part 2's column. Overlay, mirrored overlay and
  vertical-roll alignment all produce nothing.
- **Micro-text hidden beneath the column glyphs.** Rejected; a 9px high-pass
  over the column region returns glyph outlines only.
- **Payload concealed under the static `4` decoy.** Rejected; subtracting a
  median-estimated decoy across frames 1262-1442 leaves only background cloud
  motion.
- **Seam A begins before frame 1219.** Rejected; frames 1190-1218 are fog.

## Final round: baseline detector, seam B refined, further rejections

**A reliable micro-text detector.** Scoring candidate row bands by baseline
alignment (component count divided by 1 + std of component bottom edges)
finally separates text from fog. On Puzzle #1 it puts every top hit at exactly
y=360 -- its real key line -- with baseline-std 0.56 to 1.05. Applied to both
Puzzle #2 videos at 3x bitrate, the best candidates sit at y=0-30 with
baseline-std 3.9 to 5.7: fog texture, not text. This is now a validated
negative rather than an absence of evidence.

**Seam B has 9 states, not 6.** Per-frame correlation at a 0.99 threshold
(rather than 0.96) resolves nine distinct glyphs before the decoy:
`0 A 0 D 0 8 0 0 D`. They remain bottom halves only, and a bottom half does not
separate 0/8/6/9/D, so none is promoted to confident.

**Also rejected this round:**

- Part 2's column window is a hard cut, measured: mean residual jumps 14x at
  x=622 and falls 26x at x=664, with background level either side. Nothing
  exists outside the window at any threshold.
- Part 2 has no content at its frame edges during the column (0 ink at
  threshold 140), so the missing halves do not wrap to the edges the way part
  1's do.
- The two column layers are not adjacent slices: stroke continuity across every
  candidate join (X|Z, Z|X, and all mirrored orderings) is 0.000 to 0.224,
  against 0.633 for part 1's genuine wrap.
- The column window does not wrap internally: the high continuity scores at
  particular roll offsets (0.986 for X at 22px) come from joins landing in
  blank rows, and rendering shows only shifted fragments.

## Census after all refinements

| Source | Slots | Confident |
|---|---|---|
| Part 1 seam A | 10 | **10** (`6A6B0860B4`) |
| Part 1 seam B | 9 | 0 (bottom halves) |
| Part 2 static block | 2 | **2** (`C`, `8`) |
| Part 2 column | ~16 | 0 (hard-cut window) |
| **Total** | **~37** | **12** |

## Single-frame flash search, background differencing, constructed candidates

Three more mechanisms tested, all negative:

- **Single-frame flash.** Puzzle #1's statement B hides its key in a one-frame
  flash, so both Puzzle #2 videos were scanned for frame-to-frame anomalies.
  The method works: it ranks the control's flash at frame 1180 top. Puzzle #2's
  largest jumps are the end fade-out (part 1, frame 1718, a steady brightness
  decay) and title-card transitions (part 2, frames 730, 1220, 1550). No
  payload flash exists in either video.
- **Static overlay unique to one video.** Both videos share the same scene, so
  differencing their temporal medians cancels it. The difference contains only
  the title digit ('1' vs '2'). No hidden static overlay.
- **Constructed candidates.** 36 keys built from the confirmed characters
  (`6A6B0860B4`, `C8`, seam B's `0A0D0800D`) by repetition, reversal and
  zero/F padding were tested against the oracle. All rejected.

## Assessment

Puzzle #1 was solved within three hours of release. Puzzle #2 has stood for
eight years with roughly 785 combined channel views. Its two videos contain
about 37 character slots against the 64 the answer needs, and the shortfall is
geometric -- windows and frame boundaries baked into the footage -- not a
processing or resolution limit. Every mechanism the author is known to have
used (direct faint rendering, rotated columns, edge wrapping, mirroring, decoy
overlay, single-frame flash, silent audio) has now been tested with methods
validated against Puzzle #1's published answer.

The likeliest explanation consistent with all of the evidence is that Puzzle #2
as published does not contain its complete key. That is a claim about the
footage, and it is falsifiable: a source showing more than these files, or a
mechanism not yet conceived, would overturn it.

## A methodological error found and corrected: the two-stream seams

Reviewing my own seam analysis exposed a real flaw. Every seam pass took
`max(gs, key=ink)` -- the single largest component per frame -- which would
silently discard a second character if two were visible at once. Checking that
directly revealed something the earlier passes had obscured.

**Both seams carry two edge streams, active sequentially, not one.**

- Seam A: right edge holds states across frames 1219-1241, then the left edge
  holds states across 1238-1260. The rolled component is 66px wide up to frame
  1237 and jumps to 120px at 1239, which is the roll joining the two.
- Seam B: top edge 1454-1474, then bottom edge 1473-1495.

For seam A this is a genuine wrap and the join is correct: reading the full
joined span (rather than one component) gives 21 states, of which ten are
characters and the rest crossfades, reading `6A6B0860B4` -- the fourth
independent confirmation.

For seam B it is **not** a wrap. During frames 1456-1471 the bottom edge is
completely empty: ink 0 at threshold 140, maximum value 19-20, which is the
background noise floor. The characters visible at the top edge in that window
have their upper portions nowhere in the frame. They are absent, not displaced.

## Display-font templates on the column

Templates were rebuilt from part 1's own confirmed seam glyphs (`0 4 6 8 A B`),
so the column could be matched against the same typeface at the same size
rather than the lighter solution-screen face. Masked correlation over every
horizontal alignment still peaks at 0.464, against 0.654 for a *complete* glyph
matched across *different* fonts. A 43px slice of a ~66px character does not
carry enough shape to identify, even with a same-font reference.

## Final census

| Source | Slots | Recoverable | Why not |
|---|---|---|---|
| Part 1 seam A | 10 | **10** (`6A6B0860B4`) | complete via genuine edge wrap |
| Part 1 seam B | 9 | 0 | tops absent from the frame entirely |
| Part 2 static block | 2 | **2** (`C`, `8`) | complete |
| Part 2 column | ~14 | 0 | hard-cut 43px window, both sides |
| **Total** | **~35** | **12** | |

## Final exhaustion of hypotheses

Additional avenues tested this round, all negative: mp4 container metadata and
embedded strings; LSB and bit-plane analysis (bit-plane row correlation
0.51-0.74, i.e. ordinary compressed video, no hidden data); the central window
across all 1800 frames of both videos (part 2's late activity at frames
1620-1798 is the bright smoke plume, not glyphs); part 1's unexamined
vertical-wrap periods 1280-1400 (one state, no characters); 16 derivations of
Puzzle #1's key (reversal, byte-reversal, increment, complement, XOR, single
and double hashing, nibble swap, half swap); and 552 hash-of-seed candidates
over video IDs, channel id, escrow address and puzzle strings across five hash
functions.

Layer X's components do not touch the window edges, but rendering them shows
crescents and hooks rather than characters: X is one layer of a glyph whose
full extent is the overlay Y, and Y is cut at x617-664. The column stays
unreadable.

## A calibrated test for glyph completeness

The strongest evidence in this folder, because it is calibrated against known
complete glyphs in the payload's own display face.

Four complete display-font glyphs are available: the `8` and `C` of part 2's
static block (un-mirrored), and the large `1` and `2` of the "PART 1" and
"PUZZLE 2" title cards. Matched against the 16-digit library built from Puzzle
#1's solution screen, each is identified correctly and confidently:

| glyph | best match | score | margin |
|---|---|---|---|
| static-block `8` | `8` | 0.867 | 0.365 |
| static-block `C` | `C` | 0.901 | 0.357 |
| title `1` | `1` | 0.907 | 0.488 |
| title `2` | `2` | 0.787 | 0.431 |

So a complete glyph of this face scores **0.79 to 0.91** against this library,
with a wide margin, despite the library being built from a lighter weight.

Every character of part 2's column, in all three states (X, Z and the overlay
Y), split on ink-profile valleys, tested both mirrored and not, scores at most
**0.672** and typically 0.2 to 0.5. Not one reaches the range that complete
glyphs occupy.

This also corrected an error: templates built from part 1's seam glyphs are
themselves cut -- rendering them shows `0` as a bare arch, `A` as a bare V and
`B` as a D-shape. They were unusable as templates, which is why earlier
same-font matching attempts scored poorly. The seam glyphs remain *identifiable*
(a partial `6` still reads as `6`, which is why seam A's `6A6B0860B4` reproduces
against the published fragment) but they are not complete letterforms.

The conclusion is now quantitative rather than visual: the column does not
contain complete characters, and no processing recovers what the window
removed before encoding.

## The column read, verified two ways

`tools/video/verify_column.py` checks the six characters without relying on
anyone's eyes.

**Against part 1's own glyphs.** Part 1's seam gives ten complete characters
whose labels are fixed by `6A6B0860B4`, so the footage supplies in-face,
in-scale templates for `0`, `4`, `6`, `8`, `A`, `B`. Run against the column:

    cell 5 -> 0  0.517  (next 6 at 0.289)
    cell 6 -> 4  0.549  (next A at 0.330)
    cells 1-4 -> nothing above 0.27, top choices unstable

which is exactly the expected signature: the two cells that *are* in that set
come back correct with a wide margin, and the four that are not (`7`, `2`, `3`,
`5`) match nothing.

**Against the 16-digit library** from Puzzle #1's solution screen, on tightly
cropped cells, at three normalisation sizes -- all three agree:

    (32,22) (40,28) (24,17)  ->  7 2 3 5 [0|D] 4

`7` (margin 0.24), `2` (0.24) and `4` (0.38) are decisive; `3` and `5` carry
thin margins over each other's neighbours but are unambiguous at magnification;
cell 5 splits `D` 0.63 / `0` 0.60 in the small library and is settled as `0` by
the part-1 test above and by the glyph itself -- a symmetric closed oval with
two curved sides, where a `D` in this face has a flat left stem.

**Column = `723504`.**

## Corroboration from the upstream ledger

`floflo777/open-crypto-puzzles`, folder
`3-small-prizes/crypto-puzzles-2018-puzzle-2-0-05eth`, was read directly
(2026-08-31). It confirms the frame here and settles two premises:

- The channel has exactly **five** videos: Puzzle #1 statement parts 1 and 2 and
  its solution reveal, and Puzzle #2 parts 1 and 2. There is no part 3 to find.
- The escrow `0x1fa8Be9De5bBFE047C72dB8E8E3257128F7661ad` was **funded and
  unspent, nonce 0** as of 2026-08-16, funded by the same wallet that funded
  Puzzle #1's escrow, for the same 0.05 ETH, five days before Puzzle #2 was
  posted. The oracle's target is right.

Its own census, taken at 360p30 (the only rendition it could fetch), is **2 of
64** -- `C` and `8`. The "about 40 to 50 of 64 hex characters legible" line in
its README is explicitly marked as not reproduced by its own later ledger. Its
row 7 concludes the payload glyphs do *not* wrap the frame edge; at 720p60 they
demonstrably do, which is what yields `6A6B0860B4` twice over. So the reading
here (18) supersedes both upstream numbers.

## Searches run to exhaustion against these two files

Every one of these returned nothing beyond the 18 characters already read:

- **Temporal max and min projection** over all 1800 frames of each video (the
  upstream's stated technique): superimposes the ten seam glyphs at one spot,
  adds nothing.
- **Transient-layer detector**: 90 windows of 20 frames per video, each window's
  mean minus the median of all window means, scored for glyph-shaped
  components. The only windows that stand out in part 1 are its last 60 frames,
  which resolve to the title ghosting back in.
- **Tile-wise adaptive stretch** (48px tiles) on the spatial high-pass of deep
  window means -- the detector calibrated on Puzzle #1's low-opacity terminal
  layer, where it renders those glyphs plainly. Applied to every scene window of
  both videos, and to part 2's 180-frame black tail: photograph, geometric
  overlays, background texture, nothing else.
- **Chroma**: U and V channel means over the payload windows show only 4:2:0
  subsampling artefacts around the luma glyphs.
- **Temporal frequency**: per-pixel amplitude at periods 2, 3, 4, 6 and 10
  frames. Part 2 and Puzzle #1's statement A give the same profile (a period-3
  bump, the 20fps source cadence rendered at 60fps); no structured carrier.
- **Spatial frequency**: 2-D FFT of the static-block deep mean has no
  high-frequency peaks, only the vignette and panel structure.
- **Container**: the two direct-from-YouTube mp4s carry no `udta`, `meta` or
  text tracks -- no metadata payload.
- **The early flashing bursts** in part 1 (frames 11-173, eight 7-frame bursts):
  identical bounding box and ink to within 1%; they are the title blinking, not
  characters.
- **The "static decoy"**: the right-edge object from frame 1262 to 1372 is one
  `4` fading monotonically -- the last character of the parade held on screen.
- **Derivations from Puzzle #1's key**: 10,017 candidates (±5000 additive, XOR
  with repeated fragments, byte/hex reversal, complement, SHA-256/SHA-3/Keccak/
  SHA-512 over bytes and both hex casings). No match.
- **Constructions from the 18 read characters**: 512 orderings and paddings
  (each fragment forward and reversed, all orders, zero/F padding left, right
  and centred, cyclic repetition). No match.

Both puzzle-2 videos were re-confirmed to be the highest-bitrate renditions
available here (1324 and 1351 kb/s, h264 Main), not the 469/419 kb/s itag-311
streams; the three renditions of part 1 give byte-identical parade timing.

## Egress

`youtube.com`, `googlevideo.com`, `archive.org` and `web.archive.org` are
refused by this session's egress policy (CONNECT 403), as are public Ethereum
RPC endpoints. `github.com` is allowed, which is how the upstream ledger was
read. Fetching a better rendition, or checking the escrow on-chain, has to
happen outside this session.

## Complete component census (every pixel that ever changes)

The strongest form of the negative result. Take each video's temporal max minus
its temporal min -- every pixel that changes at any point in 1800 frames --
high-pass it, and enumerate every connected component above 4 sigma.

**Part 1: 63 components.** 21 letter-sized (h 32-42) at the known title-card
positions, spelling CRYPTO PUZZLER / PUZZLE / PART; one 268x183 block (the
large `2` and `1`); a 225x465 and several long thin components (the square and
diamond overlays); and **four** payload slivers -- (y0,x574,74x140) top,
(y676,x583,44x109) bottom, (y301,x0,140x72) left, (y314,x1177,109x103) right.
Those four are seams A and B. Nothing else.

**Part 2: 20 components.** Title letters, one 445x196 block (the large `2`),
`8` at (y240,x365,93x79), the mirrored `C` at (y240,x816,121x97), the MIRROR
letters at y446, and the column at x622. Nothing else.

Every component in both videos is accounted for. There is no unexplained ink.

## The key is random, so 18 characters cannot be expanded into 64

The last escape route would be a key generated from a guessable seed, since
then the 18 read characters would only need to confirm a derivation rather than
supply the entropy. Puzzle #1's key is the test case, because its answer is
published:

- 3,000,000 integer seeds swept as decimal strings under SHA-256 and SHA3-256
  against `4487FC62...E35F`: no hit.
- Its byte string carries no visible structure (one repeated byte pair in 32).

It is a random 256-bit key, and Puzzle #2's is too. 18 hex characters are 72
bits. No mechanism recovers the remaining 184 bits from footage that does not
contain them; this is an information-theoretic bound, not a search-budget
problem.

## Audio, closed for good

- **Puzzle #1's statement A -- the video that carries its key -- has an all-zero
  audio track.** The author does not use audio.
- Puzzle #2's two tracks are the same music (correlating 0.98 with Puzzle #1's
  statement B), differing in one 0.44s window at 20.53-20.97s. That difference
  is broadband 500-6000 Hz with a smooth envelope, no discrete tones, nothing
  above 16 kHz, at -53 dB relative to signal: a codec quantisation difference at
  a musical transient.

## The author's own reading rule, from the channel branding

The channel banner and both videos' title scene carry the same 13 glyphs in the
same scattered layout:

    row 1  (y178)          C        R        Y
    row 2  high (y327)          P        T        O
    row 2  low  (y361)     P        U        Z        Z
    row 3  (y508)          L        E        R

Read in raster order that is `CRYPPUTZOZLER` -- a jumble. Separated by
**baseline** it is exact:

    row 1 + row 2 high  ->  CRY + PTO   = CRYPTO
    row 2 low + row 3   ->  PUZZ + LER  = PUZZLER

So the author's own branding states the grammar: **glyphs sharing a layout but
sitting on two baselines are two interleaved strings, and must be separated by
baseline before reading.** This is worth having explicitly, because it is the
rule that makes both of Puzzle #2's payload carriers make sense -- part 1's two
edge streams and part 2's two column layers are the same idea moved into time.

Applied to every payload element, it adds nothing further:

- **Part 1's ten seam glyphs sit on one baseline.** Measured on the composites:
  bottoms at 126-130 (seam A) and 108-112 (seam B), the spread being the face's
  overshoot -- round `0`/`6`/`8` reach 130, flat `A`/`B`/`4` stop at 126. One
  string of ten, not two of five.
- **Part 2's two static characters share a baseline and a cap height.** On the
  deep-mean high-pass both `8` (x386) and the mirrored `C` (x823) measure
  top 240, bottom 333, h93. (An earlier h121 for the `C` came from the max-minus-
  min census merging it with an overlay line.)
- **The column's two states do not read independently.** If they were two
  condensed strings rather than two halves of one, each would classify on its
  own. Neither does: state C alone gives `522FC0` at 0.05-0.42 with margins
  under 0.1, state A alone `77A51F` at 0.11-0.48, against the joined `723504`
  whose decisive cells score 0.63 and 0.75. Aspect normalisation makes the
  result stretch-invariant, so a condensed-render reading is excluded too.

## The channel banner is an untested carrier

The banner is the same 13-glyph device, but **its letter spacing is not the
video's**: in the video the three top letters sit at x439/629/818, evenly spaced
190px apart; in the banner as displayed they are visibly unevenly spaced. It is
a different arrangement of the same device, not a still of the title scene.

That matters because a YouTube banner is stored at 2560x1440 and most surfaces
display only a wide central strip of it. The cropped-away area is roughly four
fifths of the image -- and hiding payload in the part of a frame that normal
viewing discards is exactly this author's method in both videos.

The banner at display resolution shows nothing beyond the 13 letters. The
full-resolution asset has not been examined; `yt3.googleusercontent.com`,
`yt3.ggpht.com`, `i.ytimg.com` and `lh3.googleusercontent.com` are all refused
by this session's egress policy, so it cannot be fetched here.

## Video descriptions

    part 1: "Do you have the intellience to solve the Crypto Puzzle? 0.05ETH is
             waiting for the best puzzler solver. Is it you?"
    part 2: "The first puzzle was solved in hours, so our second is decidely
             trickier.  Are you smart enough?"

Two misspellings, each a single dropped letter -- `intelligence` -> `intellience`
(drops `g`), `decidedly` -> `decidely` (drops `d`) -- plus a double space after
"trickier.". `g` is not a hex digit, which weakens a "the dropped letters are
payload" reading to the point of not being worth pursuing on its own. Both are
common misspellings and the author's prose is informal throughout. Recorded, not
relied on. Puzzle #1's two descriptions would settle it as a control: if they
are clean, the typos here are deliberate.

## The author's concealment device: single-frame flashes

The Puzzle #1 control was re-run frame by frame instead of by window average, and
it changes the picture of how this author hides characters.

**Statement A, frame 1181, is a single-frame flash.** Against a reference of
`0.5 * (frame 1171 + frame 1191)` its high-pass peaks at **167**, where every
neighbouring frame sits at 8-10. One frame at 60fps -- 1/60 of a second. Every
earlier pass here averaged 20 frames around it and diluted it twentyfold, which
is why it read as a vague "low-opacity terminal layer".

Isolated properly, that one frame carries:

- a **rotated column** down the centre of the frame, glyphs ~15px, which
  rotated upright and read reversed gives `451007322EA` -- Puzzle #1's
  positions 48-58;
- **large scattered glyphs** mirrored about the horizontal centreline, forming
  converging arcs: `B 9 C 2 4` on the left, `0 0 1 5` on the right, repeated
  below the mirror line. Those belong to the `BE6FB9C24510` span that neither
  statement's static composition contains.

**Statement B has four flashes**, at frames 1025, 1040, 1054 and 1181, peaks
179-190. Frame 1040 carries a **third row of six characters** above the two
static rows -- content not in the static composition at all.

So the author does publish every character, but some of them only in a frame
that is on screen for 1/60 second. That is the device, and it is the reason
Puzzle #1 is fully readable from its two videos while a window-averaged pass
concludes otherwise.

## Puzzle #2 has no flash frames

The detector was calibrated on the control (statement A frame 1181 ranks first
in its own video, isolation ratio 34, peak 184) and then run over **all three
renditions of each Puzzle #2 video** -- the 1324/1351 kb/s pair, the itag-311
pair, and the direct-fetch pair -- listing every frame whose isolated deviation
exceeds 120.

The result is identical in all six files:

| Event | Frames | Peak | What it is |
|---|---|---|---|
| Title template | 17, 46, 135, 138, 145, 174 | 137-179 | shared by all five videos in the series, Puzzle #1 included, at the same frame numbers |
| Part 1 seam A | 1220-1260 (multi-frame runs) | 222-232 | known payload |
| Part 1 decoy | 1282-1286, 1301-1305, 1517-1521, 1536-1540 | 150-167 | the fading `4` at the left and right frame edges, isolated and confirmed |
| Part 1 seam B | 1455-1495 (multi-frame runs) | 195-220 | known payload |
| Part 2 column | 1556-1613 (multi-frame runs) | 217-228 | known payload |

**No single-frame flash exists anywhere in either Puzzle #2 video.** Every
non-title event is a multi-frame run coinciding exactly with a payload window
already read. Checked directly at the control's own flash frame numbers
(1025, 1040, 1054, 1181) and at the proportional position (1772 of 1800): the
Puzzle #2 videos measure 8-22 there, against the control's 184-190 -- compression
noise, not a flash.

This is the strongest form the negative can take. The author's hidden channel has
been found, proven to carry the missing characters in the puzzle that *is*
solved, and shown to be absent from the one that is not.

Both polarities were checked. The control's flash is bright (+168, -76); a dark
flash would have been missed by a positive-only scan, so the quiet periods of
both Puzzle #2 videos were re-scanned on `max(+peak, -peak)`. Nothing exceeds 85,
and every candidate above 40 resolves on inspection to a compression fluctuation
on the edge of a glyph already accounted for -- h2 frame 1361's extreme sits at
(447, 1023), which is the `I` of the MIRROR row; h2 frame 497 and h1 frame 1160
likewise land on title letters. The 12-frame runs near frames 717-736 in both
videos are the title scene change, not a flash.

## The parade's repeat structure confirms the fragment combinatorially

Censusing the four edge streams for *distinct images* (Jaccard > 0.985 between
frames) rather than reading them gives an independent check that needs no
template library at all.

The right edge of seam A holds **six** distinct images across frames 1220-1265,
with multiplicities:

    3x  frames 1220,1221 / 1225,1226 / 1235,1236
    1x  frames 1222-1224
    2x  frames 1227-1229 / 1240,1241
    2x  frames 1230,1231 / 1237-1239
    1x  frames 1232-1234
    -   frames 1242+ (the decoy, held)

That is the multiplicity profile 3,1,2,2,1,1 in the order
`A B C D E F -> A B A C D E A D C F`. `6A6B0860B4` has exactly that profile:
`6` three times at positions 1,3,7; `0` twice at 5,8; `B` twice at 4,9; `A`, `8`
and `4` once each. A random ten-character string reproduces both the repeat
pattern *and* the reading by coincidence only rarely, so this is a genuine
independent confirmation of the fragment.

All four streams agree. The left edge shows the same six images with the same
multiplicities, shifted **exactly +19 frames** ({1220,1225,1235} -> {1239,1244,
1254}; {1227,1240} -> {1246,1259}; {1230,1237} -> {1249,1256}), and seam B's top
and bottom pair the same way. Four streams, one string of ten, confirmed without
classifying a single glyph.

It also closes the parade as a hiding place: six distinct images exist and no
more, so there is no eleventh character concealed between the held states.

## The solution video has no flash either

`0jJ6XadOAWk` is 1800 frames -- the same length as both Puzzle #2 videos -- so it
shows where this author places events on that timeline. Scanned: the shared
title template at 17, 46, 135, 138, 145, 174, and one run at 429-470 (the SOLVED
card appearing). No isolated payload flash, which fits: that video publishes the
key openly and has nothing to hide. Flashes are a statement-video device, and
Puzzle #2's two statements have none.

## Channel banner and avatar, examined

Both were recovered at full size and put through the detector calibrated on
Puzzle #1's low-opacity terminal layer.

**Avatar** (1440x1440, lossless PNG). A generic stock "bookmark with a question
mark" graphic on the channel's navy. Not a carrier:

- PNG chunk dump: `IHDR`, `sBIT`, `iCCP`, `zTXt`, `IDAT`, `IEND`. The `zTXt`
  chunk is ImageMagick's "Raw profile type APP1" wrapper; decompressed and
  un-hexed it is a 34-byte TIFF header whose single tag is
  **`Software: Picasa`**. No comment, no payload.
- Bit-plane occupancy is 0.77/0.77/0.78 for the three LSBs with row-correlation
  0.76 -- smooth gradient banding, not the ~0.50 uncorrelated plane that LSB
  stego produces.
- Spatial high-pass shows the bookmark outline, the question mark, and gradient
  dither. Nothing else.

**Banner** (2000x1125). Carries the same 13 branding glyphs and nothing else.

- 245 glyph-sized components at 4 sigma, but scattered across the smoke texture
  at every size with **no row structure** -- no set sharing a baseline at a
  regular pitch. Texture, not text.
- Edge bands (60px, all four sides) carry only cloud gradient.
- **Its background is not the video plate.** Registering it against Puzzle #1's
  statement A and both Puzzle #2 videos by normalised cross-correlation over a
  scale sweep gives 0.072-0.101 on the high-pass and 0.45-0.48 on coarse
  downscales -- the signature of a different photograph in the same duotone
  house style, not the >0.9 a shared plate would give. So the banner is not a
  wider view of the video composition, and the video's edge-clipped glyphs do
  not appear in it.

One caveat worth stating: the banner reached this session as a 24 KB lossy
re-encode of a 2000x1125 image. Blocking artefacts dominate its high-pass, so a
low-amplitude layer would not have survived. The original CDN JPEG, attached as
a file rather than pasted, would be worth a re-run; the avatar needs no re-run
because its PNG was lossless.

## The mechanism I had been missing: single-frame flashes

Puzzle #1 hides part of its key in frames that are on screen for **one frame at
60 fps**. Sampling a pixel through such a flash makes it unmistakable -- here is
a glyph position in statement B across frames 1048-1061:

    52 53 52 53 53 53 [241] 53 53 53 53 55 53 55

One frame at 241, the rest at 53. A sixtieth of a second, invisible in playback,
and **destroyed by every averaging method used up to this point** -- temporal
median, temporal mean, max projection, background subtraction, deep-window
averaging. A whole session's worth of detectors can miss it because they are all
designed to suppress exactly this.

`tools/video/flash_scan.py` finds it. A frame's *novelty* is its departure from
the mean of its two neighbours, measured only over pixels that are not routinely
bright, scored by how many glyph-shaped components that novelty contains.
Calibrated on Puzzle #1:

| video | frame | glyph components | amplitude |
|---|---|---|---|
| statement A | 1181 | 18 | 182 |
| statement B | 1054 | 21 | 200 |
| statement B | 1040 | 9 | 199 |
| statement B | 1025 | -- | 190 |

**Statement A's flash is the missing span.** Its content is a 90-degree-rotated
column of small glyphs; read bottom-up it is unambiguous at magnification:

    4 8 2 B E 6 F B 9 C 2 ...

-- positions **37-47** of the published answer `...A3DC482BE6FB9C2451007322EA...`,
precisely the stretch that statement A's static line (positions 1-39) and
statement B's static block (52-63) leave out. This closes the Puzzle #1 control
completely: the static compositions carry 51 of 64 characters, and the
one-frame flashes carry the bridge.

Statement B's flash at 1054 is a **6x5 grid of mirrored glyphs**, 30 characters.
Its bottom two rows are the static block already read (`07322E`, `A8BE35` =
positions 52-63). Its top three rows do **not** appear in the key in any
orientation or reading order -- the key contains no `F????F` substring at all,
while row 3 reads `F5084F` / `F4805F`. Those eighteen are decoys, which is
consistent with the author's use of a static decoy digit in Puzzle #2 part 1.

### Puzzle #2 has no flashes

The same detector, with four true positives on the control, applied to both
Puzzle #2 videos:

- **Part 2: zero.** Not one glyph-shaped single-frame event anywhere in 1800
  frames, at a threshold of 8 gray levels.
- **Part 1: nothing beyond the seams.** Its only hits are frames 1234, 1241,
  1475, 1476 -- inside the seam windows, where the payload glyph legitimately
  changes every 2-3 frames. Restricted to the quiet ranges (300-1215,
  1380-1452, 1615-1797) the detector returns **zero pixels above threshold**.
  The events at frames 1301/1303 and 1517/1519, which stood out before masking,
  resolve to the decoy's edge fragment shifting by a few pixels.
- Part 2's one large novelty event, frame 731, is the "PART 2" title card
  appearing.

This was the last carrier class that could have hidden characters from every
method used so far, precisely because it defeats all of them. It is not present
in Puzzle #2. The census stands at 18.

### The flash grid's extra rows are decoys, rigorously

Statement B's flash rows 1-3 look like 18 more key characters. They are not.
Taking the cleanest instance -- the frame-1040 flash, where row 3 is bright and
isolated -- classifying each of its six glyphs and enumerating **all 3^6 = 729
combinations of the top-3 candidates per position**, in both the upright and
mirrored orientation, forward and reversed:

    id    4/0/A  0/C/6  0/9/6  8/B/9  7/F/C  4/1/A   -> key substrings: NONE
    mirx  F/E/C  9/D/0  0/D/9  D/B/F  4/1/A  F/E/C   -> key substrings: NONE

Not one of those 2916 readings is a substring of the published answer. The key
also contains no `F????F` at all, which the mirrored reading requires. So the
author plants **decoy characters inside flashes** -- the same trick as Puzzle
#2 part 1's static decoy digit, moved into the flash channel. Any flash found in
future must be checked against a constraint, not trusted.

### The wide-baseline follow-up

A +-1 neighbour comparison cancels any event lasting 2-3 frames, and Puzzle #2's
source cadence is 20-24fps rendered at 60 (the period-3 bump in its temporal
frequency profile), so one source frame occupies 2-3 video frames there. That
gap is now closed:

- **Part 2, baselines +-4, +-8 and +-16, requiring 4+ glyph components sharing a
  baseline: empty at every one.**
- Part 1 at +-4 flags frames 1714-1717 with 78/76/67/57 components -- which
  resolve to the outro fade-to-black, the whole background plate crossing the
  threshold at once, not glyphs.
- The first and last frames of every video, which a two-sided detector can never
  test, carry no content either (frame 0 vs frame 3, and last vs last-3: zero
  pixels above 25 in all four videos).

### The control, fully closed

Statement A's flash column reads, bottom-up at magnification, all 22 characters
without ambiguity:

    4 8 2 B E 6 F B 9 C 2 4 5 1 0 0 7 3 2 2 E A

against the published answer's positions 37-58:

    ...A3DC 482BE6FB9C2451007322EA 8BE35F
             ^^^^^^^^^^^^^^^^^^^^^^

An exact 22-character match. Puzzle #1 is therefore accounted for end to end:

| carrier | positions |
|---|---|
| statement A, static line | 1-39 |
| statement A, flash at frame 1181 | 37-58 |
| statement B, static block | 52-63 |

The control has exactly **five** flashes in total -- statement A at 1181, and
statement B at 1025, 1040, 1054 and 1181 -- found at an amplitude threshold of 6
gray levels, so the set is complete rather than a sampling.

### What this settles about Puzzle #2

The detector that recovers 22 consecutive correct characters from a sixtieth of
a second returns **nothing** on Puzzle #2, across every variant:

| variant | part 1 | part 2 |
|---|---|---|
| +-1 baseline, bright | seam transitions only | zero |
| +-4 / +-8 / +-16 baseline, row-structured | outro fade only | zero, zero, zero |
| dark novelty | title blinks only | title blinks only |
| chroma novelty | title blinks only | title blinks only |
| first/last frames | clean | clean |

Every carrier class the author is demonstrably known to use is now tested
against a ground-truth positive control, and Puzzle #2 uses none of them beyond
the two seams, the static block and the column. The census stands at 18 of 64.

## The two videos share a background render, which gives the best noise floor available

Part 1 and part 2 are built on the **same background animation, frame
synchronised**. At matched timecodes their correlation is 0.992-0.998 with a
mean absolute difference of about **1.0 gray level** across frames 0-730 and
1660-1800; it drops to 0.45-0.70 only where their payload and title content
genuinely differs.

That makes each video a near-perfect background reference for the other -- a
cancellation no spatial high-pass can approach, because it removes the moving
cloud plate exactly rather than approximately.

Two tests on it, both clean:

- **Per-frame.** Scanning all 1800 inter-video differences for five or more
  glyph-shaped components sharing a baseline flags 777 frames, all at known
  content: the seams from 1220 on (amplitude 207, the payload glyphs
  themselves), and title-transition frames. Restricted to the *synchronised*
  ranges, where any structure would be unexplained, there are 13 row-events --
  every one at y 288-360 spanning x 195-1063, which is exactly the title
  letters, at frames 205-218, 300-307 and 714-721 where the two videos' title
  fades differ by a frame or two. Frames 1660-1800 produce nothing at all.
- **Deep-averaged.** Averaging the difference over the 730 synchronised early
  frames drives the noise floor from 1.0 to about 0.02 gray levels. The result
  (std 0.48, range -8.7 to +11.2) contains the title letters as faint timing
  ghosts, the large `2`, the diamond and square overlay edges, and compression
  blocking. **Nothing else.** A static layer present in one video and absent
  from the other, at even a tenth of a gray level, would be unmissable here.

Together with the flash work above, this closes the sensitivity question from
both ends: the flash detector covers content too brief for averaging to see,
and the background-cancelled deep average covers content too faint for anything
else to see. Neither finds a character beyond the 18.

Two further blind spots checked and closed:

- **Frame extraction.** Coded-frame counts (`ffmpeg -map 0:v:0 -f null`) are
  1800/1800/1200/1200, matching the extracted PNG counts exactly, and a
  frame-indexed re-extraction matches the stored frames to a mean absolute
  difference of 0.000. No frame was resampled away -- which matters, because a
  resampling extraction is exactly what would drop a one-frame flash.
- **Micro-text.** Every component filter used up to now required a height of at
  least 10-12px. A dedicated scan for rows of 16+ components in the 4-12px range,
  over the tile-stretched deep mean of every scene window of both videos, returns
  zero rows.

## The definitive census, with the background exactly cancelled

Using each video as the other's background reference removes the moving cloud
plate exactly. Measured off-column, the residual falls from **std 24.7** under
the blank-frame subtraction used everywhere above to **std 1.5** -- a 16-fold
improvement -- and deep-averaging each window drives the noise floor to
0.29-0.90 gray levels. At that sensitivity, every window of both videos:

**Part 1** (h2 as reference)

| frames | sigma | glyph components | what they are |
|---|---|---|---|
| 300-720 | 0.32 | **0** | -- |
| 760-1160 | 0.29 | 5 | "PART 1" title letters, y350 |
| 1220-1260 | 0.82 | **2** | seam A, x0 and x1214 |
| 1260-1380 | 0.64 | 5 | the decoy holding at the edges |
| 1380-1452 | 0.70 | **0** | -- |
| 1455-1500 | 0.90 | **2** | seam B, y0 x580 and y650 x583 |
| 1500-1615 | 0.64 | 6 | the decoy holding |
| 1615-1705 | 0.72 | **0** | -- |

**Part 2** (h1 as reference)

| frames | sigma | glyph components | what they are |
|---|---|---|---|
| 300-720 | 0.32 | **0** | -- |
| 760-1160 | 0.29 | 6 | title row, y350 |
| 1300-1500 | 0.55 | 8 | the `8` and `C` at y225, six MIRROR letters at y425 |
| 1551-1574 | ~1.1 | 3-5 | the column, merged |
| 1620-1705 | 0.76 | **0** | -- |

Two glyphs at each seam, the decoy, the static pair, MIRROR, the column, title
letters. **Nothing else exists in either file** at a third of a gray level with
the background removed exactly rather than approximately.

The census is 18 of 64 and it is now measured, not inferred.

### The column has exactly three states, confirmed at the new noise floor

The original clustering ran at correlation >0.97 on the blank-frame residual,
whose off-column noise is std 24.7 -- loose enough that genuinely distinct
states could have merged. Re-clustered on the h1-referenced difference (noise
std 1.5) at correlation **>0.995**, frames 1541-1630 resolve into exactly three
content states:

    ink 9374   frames 1551-1559, 1576-1582, 1599-1603   (state A, right parts)
    ink 8690   frames 1566-1573, 1589-1594, 1610-1619   (state C, left parts)
    ink 13752  the crossfade frames                      (their union)

Every other cluster is an ink-zero blank frame split by noise. There is no
fourth layer hiding under the old threshold. The column is two half-streams of
six characters, as read.
