# Video analysis tools (real footage)

Used against the real 720p60 renditions of Puzzle #2's two videos
(`TRUUTryah70`, `U_0DtYHDPy0`), 1800 frames each at 1280x720.

    ffmpeg -i part1.mp4 -vsync 0 f1/frame_%05d.png

- `cluster_glyphs.py FOLDER LO HI ROLLX,ROLLY ROT y0,y1,x0,x1 OUT`
  Extracts one glyph per frame, clusters them by correlation, prints the
  run-length sequence of cluster ids, and writes a labelled sheet of the
  distinct glyphs. `ROLLX,ROLLY` applies a circular roll before cropping,
  which is what rejoins a glyph split across a frame edge.
- `dedupe_glyphs.py` collapses consecutive near-identical frames into one
  entry per displayed character.

## Findings against the real footage

Both videos are 1280x720 at 60fps, 1800 frames, 30.00s. The upstream note
that "only itag 18 (640x360, 30fps) is served" does not hold.

Part 1 hides its payload at the frame edges and each glyph is split across
the left/right (seam A) or top/bottom (seam B) boundary. A circular roll of
half the frame rejoins them, and the strokes align exactly across the join --
the wrap is real, not the "chimera" the upstream ledger concluded at 360p.
Seam A glyphs are rotated 90 degrees (correct with `np.rot90(k=3)`); seam B
is upright.

A static `4` occupies the seam for hundreds of frames after each reveal --
this is the decoy the author's own README mentions, not a payload character.

## decode_real.py

Reproduces the three real reads from the 720p60 footage:

```bash
python3 decode_real.py --frames1 f1/ --frames2 f2/ --out out/
```

Writes `seamA.png`, `seamB.png` (ten characters each, `6A6B0860B4`) and
`column.png` (six characters, `723504`), and prints the cut-column agreement
that decides whether the column halves actually meet -- 0.930 at a vertical
offset of -1 px on the real frames. Below 0.8 it warns and the strip should not
be read.

All three carriers are the same trick: a glyph cut in half, with the halves
separated in space (part 1's frame edges) or in time (part 2's alternating
column). Rejoining them is what makes the characters readable; matching the
halves against whole-glyph templates is what produced the earlier "not readable"
results.

## flash_scan.py

Finds single-frame flashes -- content on screen for one frame at 60fps, which
every averaging method destroys.

```bash
python3 flash_scan.py --frames f1/ --min-glyphs 4 --dump out/
```

On Puzzle #1's statement B it returns frames 1054 (21 glyph components), 1181
(18) and 1040 (9). Statement A's flash at 1181, rotated and read bottom-up,
gives `482BE6FB9C2` -- positions 37-47 of that puzzle's published answer, the
span its static line omits. On both Puzzle #2 videos it returns nothing outside
the known seam windows.
