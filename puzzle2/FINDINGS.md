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
