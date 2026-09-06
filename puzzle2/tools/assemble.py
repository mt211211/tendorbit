"""
assemble.py -- turn a per-position reading into 64-hex candidates and sweep them.

The gate in `space_size`/`plan` is the point of this module. "Assemble candidates
consistent with the known fragment and test until MATCH" is only a strategy when
the visual read has pinned nearly every position: each fully-unknown position
multiplies the work by 16.

    unknown  candidates      single-core secp256k1 sweep (~20k/s)
     4       6.55e4          3 seconds
     6       1.68e7          14 minutes
     8       4.29e9          ~3 days
    10       1.10e12         ~2 years
    12       2.82e14         ~450 years
    52       4.11e62         longer than the universe has existed, by 1e52

So the sweep closes a gap of about 8 characters and nothing beyond it. If the
read leaves more than that open, the missing piece is the reading, not compute,
and this module says so instead of starting a run that cannot finish.
"""
from __future__ import annotations

import itertools
import sys

import numpy as np

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from oracle import TARGET, eth_address  # noqa: E402  (certified derivation)

HEX = "0123456789ABCDEF"
DEFAULT_BUDGET = 5_000_000_000  # ~8 fully-unknown characters


def constraints_from_readings(readings, length=64, alt_margin=0.25,
                              min_alts=4, widen=False):
    """Per-position allowed-character sets.

    A trusted glyph pins its position to one character. Anything else must
    OPEN the position, never pin it to a best guess: a position the reader
    declined to call is precisely where its top choice is least reliable, and
    collapsing it to that choice bakes the likely error into every candidate
    and makes the sweep test one wrong string very quickly.

    - trusted            -> the single character
    - truncated / empty  -> all 16; there is no evidence at that position
    - low confidence     -> its plausible alternatives (at least `min_alts`),
                            or all 16 when `widen` is set
    """
    slots = []
    for r in readings:
        if r.get("trusted"):
            slots.append({r["char"]})
            continue
        if widen or r.get("cut") or r.get("empty_slot") or not r.get("score"):
            slots.append(set(HEX))
            continue
        top = r["score"]
        ranked = [r["char"]] + [a["char"] for a in r.get("alternatives", [])]
        near = {r["char"]} | {a["char"] for a in r.get("alternatives", [])
                              if a["score"] >= top - alt_margin}
        # Never let a declined position become a single character.
        for c in ranked:
            if len(near) >= min_alts:
                break
            near.add(c)
        slots.append(near if len(near) > 1 else set(HEX))
    while len(slots) < length:
        slots.append(set(HEX))
    return slots[:length]


def apply_fragment(slots, fragment, position=None):
    """Constrain with a known substring. With `position=None` this returns every
    placement of the fragment that is compatible with the existing slots, rather
    than assuming where it goes."""
    frag = fragment.strip().upper()
    n, L = len(frag), len(slots)
    starts = range(L - n + 1) if position is None else [position]
    out = []
    for s in starts:
        if all(frag[i] in slots[s + i] for i in range(n)):
            variant = [set(x) for x in slots]
            for i, ch in enumerate(frag):
                variant[s + i] = {ch}
            out.append((s, variant))
    return out


def space_size(slots):
    total = 1
    for s in slots:
        total *= max(len(s), 1)
    return total


def plan(slots, budget=DEFAULT_BUDGET):
    """Report feasibility. `feasible` False means: do not start this sweep."""
    size = space_size(slots)
    pinned = sum(1 for s in slots if len(s) == 1)
    wide = sum(1 for s in slots if len(s) == 16)
    return {
        "positions": len(slots),
        "pinned": pinned,
        "open": len(slots) - pinned,
        "fully_unknown": wide,
        "candidates": size,
        "budget": budget,
        "feasible": size <= budget,
        "eta_seconds_single_core": size / 20000.0,
    }


def iter_candidates(slots, limit=None):
    """Enumerate the product. Sorted per-slot so the ordering is deterministic."""
    pools = [sorted(s) for s in slots]
    for i, combo in enumerate(itertools.product(*pools)):
        if limit is not None and i >= limit:
            return
        yield "".join(combo)


def sweep(slots, budget=DEFAULT_BUDGET, target=TARGET, progress=None,
          force=False):
    """Test every candidate against the certified derivation.

    Refuses to start an infeasible run unless `force=True`, because a sweep that
    cannot finish produces no information and burns whatever it is given.
    """
    p = plan(slots, budget)
    if not p["feasible"] and not force:
        return {"status": "REFUSED", "plan": p, "reason":
                f"{p['candidates']:.3e} candidates exceeds the {budget:.3e} budget; "
                f"{p['fully_unknown']} positions are still fully unknown. "
                "Close the gap by reading, not by sweeping."}
    tested = 0
    for cand in iter_candidates(slots):
        tested += 1
        if eth_address(cand) == target:
            return {"status": "MATCH", "candidate": cand, "tested": tested, "plan": p}
        if progress and tested % progress == 0:
            print(f"  tested {tested:,} / {p['candidates']:,}", flush=True)
    return {"status": "EXHAUSTED", "tested": tested, "plan": p}


def widen_lowest_margin(readings, slots, k):
    """Open the `k` trusted positions that were called by the slimmest margin.

    Widening only the declined positions assumes every confident call was right.
    Confidence is not proof: a lookalike pair ('8'/'B', 'D'/'0') can clear the
    trust bar and still be wrong, and no amount of widening elsewhere recovers
    from that. When budget remains, the cheapest places to buy back that risk
    are the trusted calls that won by the least.
    """
    out = [set(s) for s in slots]
    ranked = sorted(
        (i for i, r in enumerate(readings)
         if r.get("trusted") and i < len(out) and len(out[i]) == 1),
        key=lambda i: readings[i].get("margin", 1.0),
    )
    for i in ranked[:k]:
        out[i] = set(HEX)
    return out


def sweep_ladder(readings, fragment=None, fragment_at=None, target=TARGET,
                 budget=DEFAULT_BUDGET, length=64, progress=None, verbose=True):
    """Sweep progressively wider constraint sets until MATCH or budget exhausted.

    The tight reading is tried first because it is nearly free. Each rung after
    it relaxes an assumption that could be wrong -- first that a declined
    position's top guesses were close, then that the least-confident accepted
    calls were right -- and stops as soon as the next rung would exceed budget.
    """
    def _apply(slots):
        if not fragment:
            return [(None, slots)]
        return apply_fragment(slots, fragment, fragment_at)

    rungs = [("alternatives", constraints_from_readings(readings, length)),
             ("all-16 on declined positions",
              constraints_from_readings(readings, length, widen=True))]
    base_wide = rungs[1][1]
    for k in (1, 2, 3, 4, 6, 8):
        rungs.append((f"+{k} lowest-margin trusted position(s)",
                      widen_lowest_margin(readings, base_wide, k)))

    attempted = 0
    for name, slots in rungs:
        for offset, sl in _apply(slots):
            p = plan(sl, budget)
            if not p["feasible"]:
                if verbose:
                    print(f"  [{name}] {p['candidates']:.3e} candidates "
                          f"exceeds budget -- ladder stops here")
                return {"status": "BUDGET", "tested": attempted, "plan": p,
                        "rung": name}
            if verbose:
                print(f"  [{name}] sweeping {p['candidates']:.3e} candidates"
                      + (f" (fragment at {offset})" if offset is not None else ""))
            res = sweep(sl, budget=budget, target=target, progress=progress)
            attempted += res.get("tested", 0)
            if res["status"] == "MATCH":
                res["rung"] = name
                res["tested_total"] = attempted
                return res
    return {"status": "EXHAUSTED", "tested": attempted}
