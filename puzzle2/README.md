# Crypto Puzzles 2018, Puzzle #2 — glyph reading pipeline

A pipeline that background-subtracts video frames, contrast-stretches the faint
serif glyphs, auto-locates their bounding boxes, applies the mirror/rotation the
video encodes, template-matches each glyph against a hex library built from
Puzzle #1's published solution, assembles 64-hex candidates, and sweeps them
against the certified oracle.

It is validated end to end on synthetic footage with a planted key. **It has not
been run on the real videos, because the frames are not in this repository.**
See "Status" below before using any output from it.

## Status

Two things a reader needs before trusting anything here.

**1. The frames are absent.** The task this was built for referred to `f1/` and
`f2/` holding 1800 PNGs each at 1280x720. No such folders exist in this
container or this repository, so no real read has been performed. Every number
in this README comes from synthetic footage.

**2. The premises conflict with the upstream project's own later findings.**
The pipeline was specified against `floflo777/open-crypto-puzzles`, whose puzzle
folder contains a README and, dated later and explicitly superseding it, an
`analysis/` ledger. They disagree, and the ledger wins on its own terms:

| Premise | Upstream README | Upstream `analysis/` (later, supersedes) |
|---|---|---|
| Source resolution | "read cleanly at 1280x720/60fps" | "only itag 18 (640x360, 30fps) is served for all five videos" |
| Frame count | — | part 1 = 900 frames, part 2 = 901 |
| Fragment `6A6B0860B4` | "part 1's seam yields 10 hex characters" | row 9: "**No reading is claimed**" for seam 1 |
| Characters legible | "about 40 to 50 of 64" | "**2 of the 64**" — `C` and `8` only |
| `C` and `8` | — | row 11: confirmed, 0.771 and 0.849 |

The ledger's "Correction" section is specifically about how the 10-character
fragment class of result was produced: a circular roll joined a right-edge glyph
to an unrelated left-edge object and "manufactures a chimera, which is what
produced earlier readings containing `R` and `U` — shapes that are not hex digits
and were never really there."

So `6A6B0860B4` should be treated as a **hypothesis to test, not a constraint to
assume**. `apply_fragment` therefore returns every placement consistent with the
read rather than pinning it at a fixed offset, and reports when none fits.

## Why "assemble candidates and test until MATCH" cannot be the plan

Each fully-unknown position multiplies the search by 16:

| Unknown chars | Candidates | Single-core sweep at ~20k/s |
|---|---|---|
| 4 | 6.55e4 | 3 seconds |
| 6 | 1.68e7 | 14 minutes |
| 8 | 4.29e9 | ~3 days |
| 10 | 1.10e12 | ~2 years |
| 12 | 2.82e14 | ~450 years |
| 52 (fragment + `C8` known) | 4.11e62 | longer than the universe has existed, by 1e52 |
| 62 (upstream's measured position) | 4.52e74 | — |

Even granting the disputed fragment *and* `C` and `8`, 52 positions remain open
and the sweep is not reachable. `assemble.plan()` computes this and
`assemble.sweep()` refuses to start an infeasible run, because a sweep that
cannot finish yields no information. The sweep closes a gap of about 8
characters; everything else has to come from the reading.

## Install and verify

```bash
pip install numpy pillow scipy ecdsa pycryptodome
python3 tools/oracle.py --selftest        # -> SELFTEST OK
python3 tools/selftest_synthetic.py       # -> SELFTEST OK (~4 min, generates frames)
```

## Use

```bash
# 1. Build the hex template library from Puzzle #1's solution screen.
python3 tools/templates_cli.py --screen solution.png \
    --answer 4487FC620AD0C4C67E80BE342B2EA1F5A3DC482BE6FB9C2451007322EA8BE35F \
    --out hexlib.json

# 2. Read each video's frames. Debug crops land in --out.
python3 tools/run_pipeline.py --frames f1/ --templates hexlib.json --out out/p1
python3 tools/run_pipeline.py --frames f2/ --templates hexlib.json --out out/p2

# 3. Assemble and sweep (refuses if the gap is too wide).
python3 tools/solve.py --read out/p1/read.json out/p2/read.json \
    --fragment 6A6B0860B4 --templates hexlib.json
```

`run_pipeline.py` writes, per window and block:

- `w<N>_b<M>_overview.png` — the stretched residual, every component boxed:
  **green** trusted, **orange** low-confidence, **red** truncated
- `w<N>_b<M>_sheet.png` — every crop in reading order, labelled
- `w<N>_b<M>_orient.png` — one glyph in all 8 dihedral views
- `activity.txt` — per-frame ink and the derived windows
- `read.json` — the machine-readable read

## Design decisions that matter

**No hard threshold on the payload.** Glyphs are faint anti-aliased serif strokes
a few levels above the background. Everything downstream consumes a
contrast-stretched *grayscale* residual; a binary mask is derived only to decide
*where* components are, never what gets matched.

**The noise scale is measured before clipping.** Clipping a residual's negatives
to zero leaves a half-normal whose MAD is a small fraction of the true sigma, so
a z-score computed after the clip is inflated several-fold and ordinary noise
sails past any cutoff — which makes every frame look like it holds a payload.
`normalized_residual` takes its scale from the signed difference.

**Truncation is measured, and truncated glyphs are never read.** `edge_report`
compares ink in a component's outermost row/column against its own interior
maximum: a complete serif character tapers to a stroke terminal, one sliced by a
boundary carries full-strength ink right up to the cut. Edge contact is tested
with a 2px tolerance, because the outermost column of a cut glyph is
anti-aliased and often falls below the mask — requiring exact contact silently
reclassifies truncated glyphs as complete. On synthetic truncated footage the
pipeline returns **0 trusted characters, 8 flagged truncated, mean correlation
0.538**, closely reproducing the upstream measured 0.570, and emits no string.
Matching incomplete glyphs against complete templates produces a ranking, not a
character, and that is how the phantom `R`/`U` readings arose.

**One orientation for the whole block.** Letting each glyph pick its own
rotation gives every character 8 chances to correlate with something, which is
how noise gets voted into a string.

**Reading order is computed after the transform.** A block rotated 90 degrees
reads bottom-to-top in raw frame coordinates. This applies to split pieces too:
`split_candidates` cuts along a raw axis, and under a rotation or mirror that
axis runs opposite to the reading direction, which silently transposes each
split pair (`A5` → `5A`).

**Alignment is protected by pitch, not by segmentation luck.** A merged pair
left unsplit drops a character and shifts every position after it; an over-split
inserts one. Either way the string is wrong from that point on however well each
glyph is classified. `pitch_align` assigns glyphs to regularly spaced character
slots, splits a component covering two slots at the slot boundary, and reports a
slot with no component as a hole rather than closing up around it.

**Splitting requires evidence, not just geometry.** Hex glyphs legitimately
differ in extent by nearly 2x (`1` vs `D`), and at small sizes a patchy mask puts
a false notch inside a perfectly good `A`. A split is accepted only if every
piece classifies more confidently than the whole did.

**Confidence needs a margin, and split pieces need more.** A serif `8` and `B`
correlate strongly with each other; in testing a true `8` scored `B=0.701`
against `8=0.665` — a 0.036 margin, while every correct read had a margin above
0.20. Trust requires: not truncated, score >= 0.70, and margin >= 0.08. A piece
produced by splitting sits on an *estimated* cut, so it must clear a higher bar
(+0.08 score, 2.5x margin) — that is what turned the last two confident errors
into honest `?`s.

**A declined position opens; it never pins.** A position the reader declined is
exactly where its top choice is least reliable. Collapsing it to that choice
bakes the likely error into every candidate and makes the sweep test one wrong
string very fast.

**The sweep escalates.** `sweep_ladder` tries the tight reading first (nearly
free), then relaxes one assumption per rung: that declined positions' top
guesses were close, then that the least-confident *accepted* calls were right.
Confidence is not proof — a lookalike can clear the trust bar and be wrong, and
widening elsewhere never recovers from that. The ladder stops when the next rung
would exceed budget.

**Blocks are separated geometrically before classification.** Part 2 shows the
payload and the word MIRROR in the same frame, and hex-only templates will
happily force `M`, `I`, `R` onto hex classes. In testing the payload block
scored 0.946 mean against the hint block's 0.409.

**Background mode adapts to duty cycle.** A median background outvotes a
transient payload but absorbs one held across much of the clip and subtracts it
to nothing — indistinguishable from "no payload here". When no window is found
under a median background the pipeline retries with a low-percentile one. On a
synthetic 50%-duty static block, median finds nothing and percentile recovers
the window.

## Synthetic validation results

`tools/selftest_synthetic.py` plants a known 64-hex key, runs the whole chain,
and requires the oracle to report MATCH.

| Stage | Result |
|---|---|
| Template library from a solution screen | 64/64 components, all 16 digits, 100% self-classification |
| Part 1 (rotated, seam-revealed, 32 chars) | 32/32 positions, 30 trusted, 2 declined, **0 confident errors** |
| Part 2 (mirrored block, 32 chars) | 32/32 positions, all trusted, **0 confident errors**; hint block rejected at 0.409 vs 0.946 |
| Fragment placement | consistent at offset 0 |
| Oracle sweep | **MATCH** on the planted key after 15 candidates, rung "alternatives" |
| Truncated clip (negative case) | 0 trusted, 8 truncated, sweep REFUSED |

The acceptance criterion is *no confident errors*, not *no unknowns*: a `?` is
the pipeline declining a position it cannot support, which is correct behaviour.
A wrong character presented confidently is the failure that matters.

This validates the code. It says nothing about the real videos.

## What would actually move this puzzle

Per the upstream ledger, the missing piece is not processing but pixels: the
glyphs are cut off in both videos, and those pixels were never published at the
only resolution served (640x360). What would close it is a higher-resolution or
differently-cropped source — the original uploads at native resolution, an
archive predating the current transcode, a 2018 mirror, or any still frame
published by the author or a contemporary solver.

If such a source appears, this pipeline is ready to run against it.
