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
  are the two separate layers. Each layer holds ~7-9 characters.
- The column window is hard-cut: x 622-656 (34px) per state, widening to 47px
  when all states are combined, against a ~65px character width. Partial
  (masked) matching against the labelled library gives best scores of 0.3-0.7
  with coverage 0.20-0.85 and margins under 0.1 -- not a readable result.
- The column does not scroll, and rotating it does not produce a text line.

## The blocking result: there are not 64 character-slots in these videos

Exhaustive per-frame scans of both videos (glyph-shaped components, all frames)
find payload in only these places:

| Source | Character slots | Readable |
|---|---|---|
| Part 1 seam A (1219-1260) | 10 | **10** -- `6A6B0860B4` |
| Part 1 seam B (1454-1475) | ~6 | 0 confident -- glyphs are bottom halves only (ink spans y0-56 of a ~100px character, tops off-frame, no wrap counterpart). Visible sequence reads `0 A 0 D 0 D` before the decoy takes over, but a bottom half does not separate 0/8/6/9/D |
| Part 2 static block | 2 | **2** -- `C`, `8` |
| Part 2 column (2 layers) | ~16 | 0 -- truncated to ~half width, several merged |
| Everything else | 0 | title cards, the `4` decoy, and background fog |

**Total slots present: about 34. Total confidently read: 12.**

Exhaustively verified: every remaining edge-activity burst in part 1 (frames
147-193, 800-855, 996-1007, 1104-1136) and every glyph-component run in part 2
(12-102, 110-172, 288-306, 716-726) contains only title cards, the static `4`
decoy, or background fog -- no payload.

Even a perfect read of every glyph that physically exists in these two files
recovers about 36 of the 64 characters. The remaining ~28 are not in the
published footage at any resolution, because there is nowhere in either video
that they appear.

With 52 characters unknown the search space is 16^52 = 4.1e62, and with a
perfect read of everything present it would still be 16^28 = 5.2e33. Neither is
reachable. `assemble.sweep()` refuses both.

## What this means

The reading is no longer the bottleneck for what is *present*; the bottleneck is
that the footage does not contain the whole key. Puzzle #2 as published does not
appear to be solvable from these two videos alone. What would change that is a
source showing more than these files do, or a mechanism (not visible in the
frames) that expands the ~36 recovered characters into 64.

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

matching the published answer. Statement video `hX-pOBj8VsI` additionally
flashes the same key, reversed and rotated 90 degrees, as a small vertical
column for a **single frame** (frame 1180).

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
