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
| Part 1 seam B (1454-1560) | ~8 | 0 -- glyphs are halves; top-edge content shows character bottoms, bottom-edge content shows different characters' tops |
| Part 2 static block | 2 | **2** -- `C`, `8` |
| Part 2 column (2 layers) | ~16 | 0 -- truncated to ~half width, several merged |
| Everything else | 0 | title cards, the `4` decoy, and background fog |

**Total slots present: about 36. Total confidently read: 12.**

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
