"""Project Aegis -- CISO Agent-Risk Workbench.

Local-first FastAPI service. It reads agent specs, MCP server configs and
tool-call traces that you give it. It never fetches, executes or connects to an
MCP server, never runs a scanned tool, and makes no outbound calls of its own.
"""

from __future__ import annotations

import json
from pathlib import Path

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import db
from assess import run_assess
from hashutil import digest
from inventory import load_agent
from policy import DEFAULT_POLICY
from schemas import (
    AgentSaved,
    AgentSpecIn,
    AssessRequest,
    DecisionRequest,
    SnapshotSaved,
    TraceCall,
    TracesSaved,
)

ROOT = Path(__file__).resolve().parent
FIXTURE_DIR = ROOT / "fixtures" / "agents"

MIN_OVERRIDE_REASON = 20

@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()
    yield


app = FastAPI(
    title="Project Aegis — CISO Agent-Risk Workbench",
    version="0.1.0",
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
templates = Jinja2Templates(directory=str(ROOT / "templates"))


def _spec_from_row(row: dict) -> dict:
    return json.loads(row["spec_json"])


def _require_agent(agent_id: str) -> dict:
    agent = db.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"unknown agent_id {agent_id}")
    return agent


def _save_spec(spec: dict) -> tuple[str, str, str | None]:
    """Upsert an agent and record a current snapshot. Returns (id, digest, snapshot_id)."""
    agent_id = db.upsert_agent(spec)
    spec_digest = digest(spec)
    latest = db.latest_snapshot(agent_id, "current")
    snapshot_id = None
    if not latest or latest["digest"] != spec_digest:
        snapshot_id = db.add_snapshot(agent_id, "current", spec, spec_digest)
    return agent_id, spec_digest, snapshot_id


def load_fixtures() -> list[dict]:
    """Fixture specs for the UI dropdown, including the drift v1/v2 pair.

    Read from disk at render time; these are local files that ship with the repo.
    """
    entries: list[dict] = []
    for path in sorted(FIXTURE_DIR.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        approved_variant = raw.pop("_approved_v1", None)
        if approved_variant:
            entries.append(
                {
                    "key": f"{path.stem}__v1",
                    "label": f"{path.stem} (v1 — approve this first)",
                    "spec": approved_variant,
                }
            )
            entries.append(
                {
                    "key": f"{path.stem}__v2",
                    "label": f"{path.stem} (v2 — drifted)",
                    "spec": raw,
                }
            )
        else:
            entries.append({"key": path.stem, "label": path.stem, "spec": raw})
    return entries


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "index.html",
        {"fixtures": load_fixtures(), "policy": DEFAULT_POLICY},
    )


@app.get("/v1/policy")
def get_policy() -> dict:
    return DEFAULT_POLICY


@app.post("/v1/agents", response_model=AgentSaved)
def save_agent(payload: AgentSpecIn) -> AgentSaved:
    spec = payload.model_dump()
    try:
        load_agent(spec)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    agent_id, spec_digest, snapshot_id = _save_spec(spec)
    return AgentSaved(agent_id=agent_id, digest=spec_digest, snapshot_id=snapshot_id)


@app.get("/v1/agents")
def get_agents() -> dict:
    agents = [
        {
            "agent_id": row["id"],
            "name": row["name"],
            "owner": row["owner"],
            "purpose": row["purpose"],
            "autonomy": row["autonomy"],
            "spec": _spec_from_row(row),
        }
        for row in db.list_agents()
    ]
    return {"agents": agents}


@app.post("/v1/agents/{agent_id}/approve", response_model=SnapshotSaved)
def approve_agent(agent_id: str) -> SnapshotSaved:
    agent = _require_agent(agent_id)
    spec = _spec_from_row(agent)
    spec_digest = digest(spec)
    snapshot_id = db.add_snapshot(agent_id, "approved", spec, spec_digest)
    return SnapshotSaved(snapshot_id=snapshot_id, agent_id=agent_id, digest=spec_digest)


@app.post("/v1/agents/{agent_id}/traces", response_model=TracesSaved)
def add_traces(agent_id: str, calls: list[TraceCall]) -> TracesSaved:
    _require_agent(agent_id)
    stored = db.add_traces(agent_id, [call.model_dump() for call in calls])
    return TracesSaved(agent_id=agent_id, stored=len(stored), trace_ids=stored)


@app.post("/v1/assess")
def assess_agent(payload: AssessRequest) -> dict:
    agent = _require_agent(payload.agent_id)
    spec = _spec_from_row(agent)
    context = payload.context.model_dump()

    approved = db.latest_snapshot(payload.agent_id, "approved")
    approved_spec = json.loads(approved["spec_json"]) if approved else None
    traces = db.list_traces(payload.agent_id)

    result = run_assess(
        spec,
        context,
        approved_spec,
        traces,
        agent_id=payload.agent_id,
        now=payload.now,
    )

    context_id = db.add_context(payload.agent_id, context)
    db.save_assessment(result, payload.agent_id, context_id)
    result["audit"]["context_id"] = context_id
    result["agent_name"] = agent["name"]
    result["context"] = context
    return result


@app.get("/v1/queue")
def queue() -> dict:
    items = []
    for row in db.latest_assessment_per_agent():
        decisions = db.list_decisions(row["id"])
        items.append(
            {
                "assessment_id": row["id"],
                "agent_id": row["agent_id"],
                "agent_name": row["agent_name"],
                "owner": row["agent_owner"],
                "decision": row["decision"],
                "score": row["score"],
                "checked_at": row["checked_at"],
                "findings": json.loads(row["findings_json"]),
                "drift": json.loads(row["drift_json"]),
                "context": {
                    "environment": row["environment"],
                    "data_class": row["data_class"],
                    "network": row["network"],
                    "human_gate": row["human_gate"],
                },
                "last_action": decisions[-1]["action"] if decisions else None,
                "last_actor": decisions[-1]["actor"] if decisions else None,
            }
        )
    return {"queue": items}


@app.post("/v1/decisions")
def record_decision(payload: DecisionRequest) -> dict:
    assessment = db.get_assessment(payload.assessment_id)
    if not assessment:
        raise HTTPException(
            status_code=404, detail=f"unknown assessment_id {payload.assessment_id}"
        )

    decision = assessment["decision"]
    reason = (payload.override_reason or "").strip()

    if payload.action == "accept" and decision == "UNACCEPTABLE":
        raise HTTPException(
            status_code=400,
            detail="cannot accept an UNACCEPTABLE assessment; use action=override with a reason",
        )
    if payload.action == "override":
        if decision != "UNACCEPTABLE":
            raise HTTPException(
                status_code=400,
                detail=f"override only applies to an UNACCEPTABLE assessment (this one is {decision})",
            )
        if len(reason) < MIN_OVERRIDE_REASON:
            raise HTTPException(
                status_code=400,
                detail=f"override_reason must be at least {MIN_OVERRIDE_REASON} characters",
            )

    record = db.add_decision(
        payload.assessment_id, payload.action, reason or None, payload.actor
    )
    return {"decision_record": record, "assessment_decision": decision}


def _markdown(agent: dict, assessment: dict, context: dict, decisions: list[dict]) -> str:
    findings = json.loads(assessment["findings_json"])
    inventory = json.loads(assessment["inventory_json"])
    drift = json.loads(assessment["drift_json"])

    lines = [
        f"# Aegis evidence pack — {agent['name']}",
        "",
        f"- Assessment ID: `{assessment['id']}`",
        f"- Agent ID: `{agent['id']}`",
        f"- Owner: {agent['owner'] or '(none recorded)'}",
        f"- Purpose: {agent['purpose'] or '(none recorded)'}",
        f"- Autonomy: {agent['autonomy']}",
        f"- Checked at: {assessment['checked_at']}",
        f"- Policy: {DEFAULT_POLICY['name']} v{DEFAULT_POLICY['version']}",
        "",
        "## Decision",
        "",
        f"**{assessment['decision']}** — score {assessment['score']}/100",
        "",
        "## Context",
        "",
        f"- Environment: {context.get('environment')}",
        f"- Data class: {context.get('data_class')}",
        f"- Network: {context.get('network')}",
        f"- Human gate: {context.get('human_gate')}",
        "",
        "## Inventory",
        "",
        "| Tool | Permissions | Description |",
        "| --- | --- | --- |",
    ]
    for tool in inventory["tools"]:
        permissions = ", ".join(tool["permissions"]) or "(none)"
        lines.append(f"| {tool['name']} | {permissions} | {tool['description']} |")

    lines += ["", "| MCP server | Auth | Tools |", "| --- | --- | --- |"]
    for server in inventory["mcp_servers"]:
        lines.append(f"| {server['name']} | {server['auth_type']} | {', '.join(server['tools'])} |")

    lines += [
        "",
        f"Permission union: {', '.join(inventory['permissions']) or '(none)'}",
        "",
        "## Findings",
        "",
    ]
    if findings:
        lines += ["| Code | Severity | Detail |", "| --- | --- | --- |"]
        lines += [f"| {f['code']} | {f['severity']} | {f['detail']} |" for f in findings]
    else:
        lines.append("No policy findings.")

    lines += [
        "",
        "## Drift",
        "",
        f"- Detected: {drift['detected']}",
        f"- Changed tools: {', '.join(drift['changed_tools']) or '(none)'}",
        f"- Approved digest: `{drift.get('approved_digest') or '(never approved)'}`",
        f"- Current digest: `{drift.get('current_digest')}`",
        "",
        "## Human decisions",
        "",
    ]
    if decisions:
        lines += ["| Decided at | Actor | Action | Override reason |", "| --- | --- | --- | --- |"]
        for record in decisions:
            lines.append(
                f"| {record['decided_at']} | {record['actor']} | {record['action']} | "
                f"{record['override_reason'] or ''} |"
            )
    else:
        lines.append("No human decision recorded yet.")

    lines += [
        "",
        "---",
        "",
        "Generated by Project Aegis, an open local-first CISO agent-risk workbench. "
        "Findings are produced by a deterministic policy engine over the spec and traces "
        "supplied to it; no MCP server was contacted or executed.",
        "",
    ]
    return "\n".join(lines)


@app.get("/v1/evidence/{assessment_id}")
def evidence(assessment_id: str) -> dict:
    assessment = db.get_assessment(assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail=f"unknown assessment_id {assessment_id}")
    agent = db.get_agent(assessment["agent_id"])
    if not agent:
        raise HTTPException(status_code=404, detail="agent for this assessment is missing")
    context = db.get_context(assessment["context_id"]) or {}
    decisions = db.list_decisions(assessment_id)

    return {
        "assessment_id": assessment_id,
        "agent": {
            "agent_id": agent["id"],
            "name": agent["name"],
            "owner": agent["owner"],
            "purpose": agent["purpose"],
            "autonomy": agent["autonomy"],
        },
        "context": {
            key: context.get(key)
            for key in ("environment", "data_class", "network", "human_gate")
        },
        "decision": assessment["decision"],
        "score": assessment["score"],
        "findings": json.loads(assessment["findings_json"]),
        "inventory": json.loads(assessment["inventory_json"]),
        "drift": json.loads(assessment["drift_json"]),
        "checked_at": assessment["checked_at"],
        "policy": {"name": DEFAULT_POLICY["name"], "version": DEFAULT_POLICY["version"]},
        "human_decisions": decisions,
        "evidence_markdown": _markdown(agent, assessment, context, decisions),
    }


@app.get("/v1/audit/{agent_id}")
def audit(agent_id: str) -> dict:
    agent = _require_agent(agent_id)
    traces = db.list_traces(agent_id)
    tools_seen = sorted({str(trace.get("tool", "")) for trace in traces if trace.get("tool")})
    assessments = [
        {
            "assessment_id": row["id"],
            "context_id": row["context_id"],
            "decision": row["decision"],
            "score": row["score"],
            "checked_at": row["checked_at"],
            "findings": json.loads(row["findings_json"]),
            "drift": json.loads(row["drift_json"]),
        }
        for row in db.list_assessments(agent_id)
    ]
    return {
        "agent": {
            "agent_id": agent["id"],
            "name": agent["name"],
            "owner": agent["owner"],
            "purpose": agent["purpose"],
            "autonomy": agent["autonomy"],
            "created_at": agent["created_at"],
            "spec": _spec_from_row(agent),
        },
        "snapshots": [
            {
                "snapshot_id": row["id"],
                "kind": row["kind"],
                "digest": row["digest"],
                "created_at": row["created_at"],
            }
            for row in db.list_snapshots(agent_id)
        ],
        "traces_summary": {
            "count": len(traces),
            "tools_seen": tools_seen,
            "first_ts": traces[0].get("ts") if traces else None,
            "last_ts": traces[-1].get("ts") if traces else None,
        },
        "assessments": assessments,
        "decisions": db.decisions_for_agent(agent_id),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
