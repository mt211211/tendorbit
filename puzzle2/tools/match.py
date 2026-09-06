"""
match.py -- classify segmented glyphs against the labelled hex library.

Every reading this produces carries a confidence and a truncation flag. A glyph
that `edge_report` called cut is reported with `trusted=False` no matter how
high its correlation climbs: correlating an incomplete character against a
complete template caps out around 0.57 (tested.md row 9) and the ranking it
produces is not stable across orientations. Those readings are diagnostics, not
characters.
"""
from __future__ import annotations

import numpy as np

import glyphlib as gl
from templates import normalize_patch

TRUST_MIN = 0.70    # below this a reading is not a character, it is a guess
MARGIN_MIN = 0.08   # and it must also beat the runner-up by this much


def classify(patch, lib, orientations=None, topk=3):
    """Best hex digit for one patch, searched over the dihedral group."""
    chars = sorted(lib)
    M = np.stack([lib[c] for c in chars])
    orientations = gl.ORIENTATIONS if orientations is None else orientations
    best = []
    for rot, mirror in orientations:
        v = normalize_patch(gl.orient(patch, rot, mirror))
        if v is None:
            continue
        scores = M @ v
        for i in np.argsort(scores)[::-1][:topk]:
            best.append({
                "char": chars[i],
                "score": float(scores[i]),
                "rot": rot,
                "mirror": mirror,
                "orientation": gl.orientation_name(rot, mirror),
            })
    best.sort(key=lambda d: -d["score"])
    return best[:topk] if best else []


def read_glyphs(glyphs, lib, stretched=None, orientations=None,
                trust_min=TRUST_MIN, margin_min=MARGIN_MIN):
    """Classify a sequence of glyphs already in reading order."""
    out = []
    for i, g in enumerate(glyphs):
        cands = classify(g.patch, lib, orientations, topk=4)
        rep = gl.edge_report(g, stretched) if stretched is not None else {"cut": bool(g.touches)}
        top = cands[0] if cands else {"char": "?", "score": 0.0, "orientation": "n/a"}
        runner = next((c for c in cands[1:] if c["char"] != top["char"]), None)
        margin = top["score"] - runner["score"] if runner else top["score"]
        # A piece produced by splitting a merged component sits on an ESTIMATED
        # cut, not an observed gap, so a few columns of its neighbour may be
        # attached or a few of its own missing. It classifies like a slightly
        # wrong glyph, which is exactly the regime where lookalikes ('D' vs '1',
        # 'A' vs '2') win narrowly. Such a piece has to clear a higher bar to be
        # called a character.
        derived = bool(getattr(g, "meta", None) and g.meta.get("split_from"))
        need_score = trust_min + (0.08 if derived else 0.0)
        need_margin = margin_min * (2.5 if derived else 1.0)
        out.append({
            "index": i,
            "box": g.box,
            "ink": g.ink,
            "char": top["char"],
            "score": top["score"],
            "margin": float(margin),
            "runner_up": runner["char"] if runner else None,
            "orientation": top.get("orientation", "n/a"),
            "alternatives": cands[1:],
            "cut": rep["cut"],
            "edge": rep,
            "derived": derived,
            # Three independent conditions. Absolute score alone is not enough:
            # a serif '8' and 'B' both correlate highly with each other's
            # template, so a 0.70 winner that beat its runner-up by 0.03 is a
            # coin flip wearing a confident number. Such a position must reach
            # the assembler as a 2-way ambiguity, not as a wrong character.
            "trusted": ((not rep["cut"])
                        and top["score"] >= need_score
                        and margin >= need_margin),
        })
    return out


def consensus_orientation(readings):
    """Which single orientation explains the most trusted glyphs? The video
    applies ONE transform to the whole block, so a per-glyph orientation
    free-for-all is a sign the matching is chasing noise."""
    votes = {}
    for r in readings:
        if r["trusted"]:
            votes[r["orientation"]] = votes.get(r["orientation"], 0) + 1
    if not votes:
        return None, {}
    return max(votes, key=votes.get), votes


def best_global_orientation(glyphs, lib, orientations=None):
    """Pick ONE orientation for the whole block.

    The video applies a single transform to a whole block of glyphs, so letting
    each glyph choose its own rotation is not a read -- it is 8 chances per
    character to find something that correlates, which is how noise gets voted
    into a string. Score each orientation by the mean best-correlation it gives
    across all glyphs and take the winner.
    """
    chars = sorted(lib)
    M = np.stack([lib[c] for c in chars])
    orientations = gl.ORIENTATIONS if orientations is None else orientations
    table = {}
    for rot, mirror in orientations:
        scores = []
        for g in glyphs:
            v = normalize_patch(gl.orient(g.patch, rot, mirror))
            scores.append(float((M @ v).max()) if v is not None else 0.0)
        table[(rot, mirror)] = float(np.mean(scores)) if scores else 0.0
    best = max(table, key=table.get)
    return best, table


def read_block(glyphs, lib, stretched, shape=None, trust_min=TRUST_MIN,
               orientations=None):
    """Full read of one block: choose a global orientation, order the glyphs in
    that corrected frame, then classify each under that single transform."""
    if not glyphs:
        return {"text": "", "readings": [], "orientation": None, "scores": {}}
    (rot, mirror), table = best_global_orientation(glyphs, lib, orientations)
    shape = shape if shape is not None else stretched.shape
    ordered = gl.reading_order_oriented(glyphs, shape, rot, mirror)
    readings = read_glyphs(ordered, lib, stretched=stretched,
                           orientations=[(rot, mirror)], trust_min=trust_min)
    return {
        "text": "".join(r["char"] for r in readings),
        "readings": readings,
        "glyphs": ordered,
        "orientation": gl.orientation_name(rot, mirror),
        "rot": rot,
        "mirror": mirror,
        "orientation_scores": {gl.orientation_name(r, m): v for (r, m), v in table.items()},
        "trusted_text": "".join(r["char"] if r["trusted"] else "?" for r in readings),
    }


def group_blocks(glyphs, shape, rot=0, mirror=False, row_tol=0.9):
    """Split glyphs into spatially separate blocks (rows) in the corrected frame.

    Part 2 puts the payload and the word MIRROR in the same frame. Reading them
    as one string splices instruction text into the key. Hex-only templates will
    happily force 'M', 'I', 'R' onto hex classes, so the separation has to be
    geometric -- done before classification, not cleaned up after.
    """
    if not glyphs:
        return []
    H, W = shape
    keyed = []
    for g in glyphs:
        cy = (g.box[0] + g.box[1]) / 2.0
        cx = (g.box[2] + g.box[3]) / 2.0
        ty, tx, _, _ = gl.transform_point(cy, cx, H, W, rot, mirror)
        keyed.append((ty, tx, g))
    spans = [max(g.height, g.width) for g in glyphs]
    tol = max(4.0, float(np.median(spans)) * row_tol)
    rows = []
    for ty, tx, g in sorted(keyed, key=lambda t: t[0]):
        if rows and abs(ty - rows[-1][0]) <= tol:
            rows[-1][1].append((tx, g))
            rows[-1][0] = (rows[-1][0] + ty) / 2.0
        else:
            rows.append([ty, [(tx, g)]])
    return [[g for _, g in sorted(r[1], key=lambda t: t[0])] for r in rows]


def read_blocks(glyphs, lib, stretched, shape=None, trust_min=TRUST_MIN):
    """Choose one global orientation, then read each spatial block separately."""
    if not glyphs:
        return {"orientation": None, "blocks": []}
    (rot, mirror), table = best_global_orientation(glyphs, lib)
    shape = shape if shape is not None else stretched.shape
    glyphs = refine_splits(glyphs, lib, rot, mirror)
    blocks = []
    for bi, blk in enumerate(group_blocks(glyphs, shape, rot, mirror)):
        slots = pitch_align(blk, shape, rot, mirror, lib)
        present = [g for _, g in slots if g is not None]
        rd_present = read_glyphs(present, lib, stretched=stretched,
                                 orientations=[(rot, mirror)], trust_min=trust_min)
        # Re-interleave, so a slot with no component stays a hole at its own
        # position instead of the string closing up around it.
        rd, it = [], iter(rd_present)
        for pos, (_slot, g) in enumerate(slots):
            if g is None:
                rd.append({"index": pos, "box": None, "ink": 0, "char": "?",
                           "score": 0.0, "margin": 0.0, "runner_up": None,
                           "orientation": gl.orientation_name(rot, mirror),
                           "alternatives": [], "cut": False, "edge": {"cut": False},
                           "trusted": False, "empty_slot": True})
            else:
                r = next(it)
                r["index"] = pos
                rd.append(r)
        # Keep the glyph list slot-aligned with the readings (None for a hole),
        # so debug overlays label the component they actually describe.
        blk = [g for _, g in slots]
        # Mean score is what discriminates a payload block from instruction text,
        # so it is computed over components that exist -- empty slots are missing
        # evidence, not evidence of a bad match.
        scores = [r["score"] for r in rd if not r.get("empty_slot")]
        blocks.append({
            "index": bi,
            "text": "".join(r["char"] for r in rd),
            "trusted_text": "".join(r["char"] if r["trusted"] else "?" for r in rd),
            "readings": rd,
            "glyphs": blk,
            "n": len(rd),
            "mean_score": float(np.mean(scores)) if scores else 0.0,
            "n_trusted": sum(1 for r in rd if r["trusted"]),
            "n_cut": sum(1 for r in rd if r["cut"]),
        })
    return {
        "orientation": gl.orientation_name(rot, mirror),
        "rot": rot, "mirror": mirror,
        "orientation_scores": {gl.orientation_name(r, m): v for (r, m), v in table.items()},
        "blocks": blocks,
    }


def _best_score(patch, M, rot, mirror):
    v = normalize_patch(gl.orient(patch, rot, mirror))
    return float((M @ v).max()) if v is not None else 0.0


def refine_splits(glyphs, lib, rot, mirror, min_gain=0.05):
    """Break up merged components, but only on evidence.

    A component that is unusually wide is a *suspect*, not a verdict. The test
    applied here is whether splitting it makes the reading better: every piece
    must classify more confidently than the whole did. That rejects the case
    that geometry gets wrong -- a legitimately wide glyph like 'A', whose patchy
    mask at small sizes shows a notch that looks exactly like two characters
    touching -- while still catching real merges.
    """
    if len(glyphs) < 3:
        return glyphs
    chars = sorted(lib)
    M = np.stack([lib[c] for c in chars])
    mw, mh = gl.median_extents(glyphs)
    out = []
    for g in glyphs:
        pieces = gl.split_candidates(g, mw, mh)
        if not pieces:
            out.append(g)
            continue
        whole = _best_score(g.patch, M, rot, mirror)
        scores = [_best_score(p.patch, M, rot, mirror) for p in pieces]
        if scores and min(scores) >= whole + min_gain:
            out.extend(pieces)
        else:
            out.append(g)
    return out


# ------------------------------------------------------------ pitch alignment

def estimate_pitch(centres):
    """Robust character pitch from consecutive centre spacings."""
    if len(centres) < 2:
        return None
    d = np.diff(np.sort(np.asarray(centres, float)))
    d = d[d > 0]
    if d.size == 0:
        return None
    # Merged pairs contribute roughly 2x the true pitch and over-splits roughly
    # 0.5x; both are outliers around a dominant mode, so the median holds as
    # long as clean neighbours are the majority.
    return float(np.median(d))


def pitch_align(glyphs, shape, rot, mirror, lib, tol=0.45):
    """Assign glyphs to regularly spaced character slots.

    Alignment, not classification, is what a positional key cannot survive
    losing. A merged pair left unsplit drops a character and shifts every
    position after it; an over-split inserts one. Either way the string is
    wrong from that point on, no matter how well each individual glyph is
    classified.

    Characters in a rendered line sit on a near-regular pitch, which pins the
    slot each glyph belongs to independently of how segmentation went. A
    component covering two slots is split at the slot boundary; a slot with no
    component is reported as a hole rather than silently closed up.

    Returns a list of (slot_index, glyph_or_None).
    """
    if len(glyphs) < 3:
        return [(i, g) for i, g in enumerate(glyphs)]
    H, W = shape
    info = []
    for g in glyphs:
        cy = (g.box[0] + g.box[1]) / 2.0
        cx = (g.box[2] + g.box[3]) / 2.0
        ty, tx, _, _ = gl.transform_point(cy, cx, H, W, rot, mirror)
        info.append((tx, g))
    info.sort(key=lambda t: t[0])
    centres = [t[0] for t in info]
    pitch = estimate_pitch(centres)
    if not pitch or pitch <= 0:
        return [(i, g) for i, (_, g) in enumerate(info)]

    origin = centres[0]
    slotted = {}
    for tx, g in info:
        # extent along the flow axis, in the corrected frame
        span = g.height if (rot // 90) % 2 else g.width
        k = max(1, int(round(span / pitch)))
        base = int(round((tx - origin) / pitch))
        if k == 1:
            slotted.setdefault(base, []).append(g)
            continue
        pieces = gl.split_candidates(g, pitch, pitch, max_ratio=1.0, max_valley=1.01)
        if pieces and len(pieces) == k:
            # Order the pieces in the CORRECTED frame, not in raw image order.
            # split_candidates cuts along a raw axis, and under a rotation or a
            # mirror that axis runs opposite to the reading direction -- which
            # silently transposes each split pair ('A5' -> '5A').
            keyed = []
            for pc in pieces:
                pcy = (pc.box[0] + pc.box[1]) / 2.0
                pcx = (pc.box[2] + pc.box[3]) / 2.0
                _, ptx, _, _ = gl.transform_point(pcy, pcx, H, W, rot, mirror)
                keyed.append((ptx, pc))
            keyed.sort(key=lambda t: t[0])
            for j, (_, pc) in enumerate(keyed):
                slotted.setdefault(base - (k - 1) // 2 + j, []).append(pc)
        else:
            slotted.setdefault(base, []).append(g)

    out = []
    if slotted:
        for s in range(min(slotted), max(slotted) + 1):
            here = slotted.get(s, [])
            if not here:
                out.append((s, None))
            elif len(here) == 1:
                out.append((s, here[0]))
            else:
                # Two components in one slot means one character arrived in
                # pieces (a broken stroke, or an over-split). Dropping the extras
                # would throw away ink that belongs to this character; rejoining
                # them reconstructs it.
                out.append((s, _merge_glyphs(here)))
    return out


def _merge_glyphs(parts):
    """Rejoin components that belong to a single character slot."""
    if len(parts) == 1:
        return parts[0]
    y0 = min(g.box[0] for g in parts)
    y1 = max(g.box[1] for g in parts)
    x0 = min(g.box[2] for g in parts)
    x1 = max(g.box[3] for g in parts)
    h, w = y1 - y0, x1 - x0
    patch = np.zeros((h, w), np.float32)
    mask = np.zeros((h, w), bool)
    for g in parts:
        gy, gx = g.box[0] - y0, g.box[2] - x0
        sub = patch[gy:gy + g.patch.shape[0], gx:gx + g.patch.shape[1]]
        np.maximum(sub, g.patch, out=sub)
        mask[gy:gy + g.mask.shape[0], gx:gx + g.mask.shape[1]] |= g.mask
    touches = tuple(sorted({t for g in parts for t in g.touches}))
    return gl.Glyph(box=(y0, y1, x0, x1), patch=patch, mask=mask,
                    ink=int(mask.sum()), touches=touches,
                    meta={"merged_from": [g.box for g in parts]})
