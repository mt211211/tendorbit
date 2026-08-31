"""Load the five synthetic fixtures into SQLite. Idempotent: run it as often as you like.

For drifted_after_approval the v1 spec is stored as the approved snapshot and the
v2 (drifted) spec becomes the agent's current spec -- so the rug-pull is visible
in the UI on a fresh database without any curl.

Trace timestamps are rebased onto the last few synthetic days relative to today,
so the 7-day NO_TRACE window behaves the same whenever you run the demo.

Usage: python seed.py
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import db
from hashutil import digest
from inventory import load_agent

ROOT = Path(__file__).resolve().parent
AGENT_FIXTURES = ROOT / "fixtures" / "agents"
TRACE_FIXTURES = ROOT / "fixtures" / "traces"

# fixture file -> trace file to attach
TRACE_MAP = {
    "clean_dev_agent.json": "clean_trace.json",
    "drifted_after_approval.json": "drift_trace.json",
}


def rebase_traces(calls: list[dict]) -> list[dict]:
    """Move fixture timestamps into the last few days so the demo never goes stale."""
    now = datetime.now(timezone.utc)
    rebased = []
    for offset, call in enumerate(reversed(calls), start=1):
        rebased.append(dict(call, ts=(now - timedelta(days=offset)).isoformat()))
    return list(reversed(rebased))


def seed_agent(path: Path) -> dict:
    raw = load_agent(path)
    approved_variant = raw.pop("_approved_v1", None)

    agent_id = db.upsert_agent(raw)
    current_digest = digest(raw)
    latest_current = db.latest_snapshot(agent_id, "current")
    if not latest_current or latest_current["digest"] != current_digest:
        db.add_snapshot(agent_id, "current", raw, current_digest)

    approved_digest = None
    if approved_variant:
        approved_spec = load_agent(approved_variant)
        approved_digest = digest(approved_spec)
        latest_approved = db.latest_snapshot(agent_id, "approved")
        if not latest_approved or latest_approved["digest"] != approved_digest:
            db.add_snapshot(agent_id, "approved", approved_spec, approved_digest)

    trace_file = TRACE_MAP.get(path.name)
    trace_count = db.count_traces(agent_id)
    if trace_file and trace_count == 0:
        calls = json.loads((TRACE_FIXTURES / trace_file).read_text(encoding="utf-8"))
        db.add_traces(agent_id, rebase_traces(calls))
        trace_count = len(calls)

    return {
        "fixture": path.name,
        "agent_id": agent_id,
        "name": raw["name"],
        "current_digest": current_digest,
        "approved_digest": approved_digest,
        "traces": trace_count,
    }


def main() -> int:
    db.init_db()
    print(f"database: {db.db_path()}")
    for path in sorted(AGENT_FIXTURES.glob("*.json")):
        row = seed_agent(path)
        approved = row["approved_digest"][:12] + "…" if row["approved_digest"] else "(not approved)"
        print(
            f"  {row['fixture']:<32} {row['agent_id']}  current={row['current_digest'][:12]}…  "
            f"approved={approved}  traces={row['traces']}"
        )
    print(f"seeded {len(db.list_agents())} agents")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
