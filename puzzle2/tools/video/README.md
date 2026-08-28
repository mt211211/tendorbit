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
