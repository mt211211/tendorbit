"""Assessment engine: inventory + drift + policy -> decision, score, findings.

Pure: no file, network or database access. app.py persists what this returns.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from hashutil import diff_specs, digest
from inventory import summarise
from policy import check_policy

BLOCK_PENALTY = 25
REVIEW_PENALTY = 10

ACCEPTABLE = "ACCEPTABLE"
CONDITIONAL = "CONDITIONAL"
UNACCEPTABLE = "UNACCEPTABLE"


def score_findings(findings) -> int:
    blocks = sum(1 for f in findings if f["severity"] == "block")
    reviews = sum(1 for f in findings if f["severity"] == "review")
    return max(0, 100 - BLOCK_PENALTY * blocks - REVIEW_PENALTY * reviews)


def decide(findings) -> str:
    if any(f["severity"] == "block" for f in findings):
        return UNACCEPTABLE
    if any(f["severity"] == "review" for f in findings):
        return CONDITIONAL
    return ACCEPTABLE


def run_assess(
    spec: dict,
    context: dict,
    approved_snapshot: dict | None,
    traces: list,
    agent_id: str = "",
    assessment_id: str | None = None,
    now: str | None = None,
) -> dict:
    """Assess one agent spec in one deployment context.

    ``approved_snapshot`` is the previously approved spec (not a digest) or None.
    """
    inventory = summarise(spec)
    current_digest = digest(spec)

    approved_digest = digest(approved_snapshot) if approved_snapshot else None
    changed_tools = diff_specs(approved_snapshot, spec) if approved_snapshot else []
    drift_detected = bool(approved_digest and approved_digest != current_digest)

    checked_at = now or datetime.now(timezone.utc).isoformat()
    findings = check_policy(
        spec, context, approved_digest, current_digest, traces, now=checked_at
    )
    decision = decide(findings)

    return {
        "decision": decision,
        "score": score_findings(findings),
        "findings": findings,
        "inventory": {
            "tools": inventory["tools"],
            "mcp_servers": inventory["mcp_servers"],
            "permissions": inventory["permission_union"],
        },
        "drift": {
            "detected": drift_detected,
            "changed_tools": changed_tools,
            "approved_digest": approved_digest,
            "current_digest": current_digest,
        },
        "audit": {
            "assessment_id": assessment_id or f"asmt_{uuid.uuid4().hex}",
            "agent_id": agent_id,
            "checked_at": checked_at,
            "human_required": decision != ACCEPTABLE,
        },
    }
