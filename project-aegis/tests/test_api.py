import copy
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import db
from app import app

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "agents"
NOW = "2026-08-31T12:00:00+00:00"

DEV_CONTEXT = {
    "environment": "dev",
    "data_class": "internal",
    "network": "allowlist",
    "human_gate": "in_the_loop",
}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("AEGIS_DB", str(tmp_path / "aegis-test.db"))
    db.init_db()
    with TestClient(app) as test_client:
        yield test_client


def fixture_spec(name):
    spec = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    spec.pop("_approved_v1", None)
    return spec


def approved_v1(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))["_approved_v1"]


def save(client, spec):
    response = client.post("/v1/agents", json=spec)
    assert response.status_code == 200, response.text
    return response.json()


def assess(client, agent_id, context=None):
    response = client.post(
        "/v1/assess",
        json={"agent_id": agent_id, "context": context or DEV_CONTEXT, "now": NOW},
    )
    assert response.status_code == 200, response.text
    return response.json()


def codes(result):
    return {finding["code"] for finding in result["findings"]}


def test_health(client):
    assert client.get("/health").json() == {"ok": True}


def test_index_page_renders_with_fixture_options(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Project Aegis" in response.text
    assert "file_and_network_bridge" in response.text


def test_save_then_assess_clean_agent_is_acceptable(client):
    saved = save(client, fixture_spec("clean_dev_agent.json"))
    assert saved["agent_id"].startswith("agt_")
    assert len(saved["digest"]) == 64

    result = assess(client, saved["agent_id"])
    assert result["decision"] == "ACCEPTABLE"
    assert result["score"] == 100
    assert result["findings"] == []
    assert result["audit"]["agent_id"] == saved["agent_id"]
    assert result["audit"]["human_required"] is False


def test_bridge_agent_is_unacceptable(client):
    saved = save(client, fixture_spec("file_and_network_bridge.json"))
    result = assess(client, saved["agent_id"])
    assert result["decision"] == "UNACCEPTABLE"
    assert "BRIDGE" in codes(result)
    assert result["score"] == 75


def test_saving_an_invalid_spec_is_rejected(client):
    bad = fixture_spec("clean_dev_agent.json")
    bad["tools"][0]["permissions"] = ["sudo"]
    assert client.post("/v1/agents", json=bad).status_code == 422


def test_assess_unknown_agent_is_404(client):
    response = client.post(
        "/v1/assess", json={"agent_id": "agt_missing", "context": DEV_CONTEXT}
    )
    assert response.status_code == 404


def test_approve_then_change_spec_then_assess_detects_drift(client):
    v1 = approved_v1("drifted_after_approval.json")
    saved = save(client, v1)
    agent_id = saved["agent_id"]

    approved = client.post(f"/v1/agents/{agent_id}/approve")
    assert approved.status_code == 200
    assert approved.json()["snapshot_id"].startswith("snap_")

    clean = assess(client, agent_id)
    assert "DRIFT_AFTER_APPROVAL" not in codes(clean)

    save(client, fixture_spec("drifted_after_approval.json"))
    drifted = assess(client, agent_id)

    assert drifted["decision"] == "UNACCEPTABLE"
    assert "DRIFT_AFTER_APPROVAL" in codes(drifted)
    assert drifted["drift"]["detected"] is True
    assert drifted["drift"]["changed_tools"] == ["format_text"]


def test_traces_clear_the_no_trace_finding(client):
    spec = approved_v1("drifted_after_approval.json")
    agent_id = save(client, spec)["agent_id"]
    client.post(f"/v1/agents/{agent_id}/approve")

    assert "NO_TRACE" in codes(assess(client, agent_id))

    stored = client.post(
        f"/v1/agents/{agent_id}/traces",
        json=[{"tool": "format_text", "args_redacted": {"text": "<redacted>"}, "ts": "2026-08-30T09:00:00+00:00"}],
    )
    assert stored.status_code == 200
    assert stored.json()["stored"] == 1

    assert "NO_TRACE" not in codes(assess(client, agent_id))


def test_queue_lists_latest_assessment_per_agent(client):
    clean_id = save(client, fixture_spec("clean_dev_agent.json"))["agent_id"]
    bridge_id = save(client, fixture_spec("file_and_network_bridge.json"))["agent_id"]
    assess(client, clean_id)
    assess(client, bridge_id)
    assess(client, bridge_id)

    queue = client.get("/v1/queue").json()["queue"]
    assert len(queue) == 2
    by_agent = {row["agent_id"]: row for row in queue}
    assert by_agent[bridge_id]["decision"] == "UNACCEPTABLE"
    assert by_agent[clean_id]["decision"] == "ACCEPTABLE"


def test_override_without_reason_on_unacceptable_is_400(client):
    agent_id = save(client, fixture_spec("file_and_network_bridge.json"))["agent_id"]
    result = assess(client, agent_id)
    response = client.post(
        "/v1/decisions",
        json={"assessment_id": result["audit"]["assessment_id"], "action": "override"},
    )
    assert response.status_code == 400
    assert "20 characters" in response.json()["detail"]


def test_override_with_short_reason_is_400(client):
    agent_id = save(client, fixture_spec("file_and_network_bridge.json"))["agent_id"]
    result = assess(client, agent_id)
    response = client.post(
        "/v1/decisions",
        json={
            "assessment_id": result["audit"]["assessment_id"],
            "action": "override",
            "override_reason": "fine",
        },
    )
    assert response.status_code == 400


def test_override_with_reason_is_200_and_is_recorded(client):
    agent_id = save(client, fixture_spec("file_and_network_bridge.json"))["agent_id"]
    result = assess(client, agent_id)
    assessment_id = result["audit"]["assessment_id"]
    reason = "Time-boxed pilot on a synthetic repo only; egress allowlisted to the review service."
    response = client.post(
        "/v1/decisions",
        json={
            "assessment_id": assessment_id,
            "action": "override",
            "override_reason": reason,
            "actor": "ciso@example.gov.uk",
        },
    )
    assert response.status_code == 200
    record = response.json()["decision_record"]
    assert record["action"] == "override"
    assert record["override_reason"] == reason
    assert record["actor"] == "ciso@example.gov.uk"

    evidence = client.get(f"/v1/evidence/{assessment_id}").json()
    assert evidence["human_decisions"][0]["override_reason"] == reason
    assert reason in evidence["evidence_markdown"]


def test_accepting_an_unacceptable_assessment_is_400(client):
    agent_id = save(client, fixture_spec("file_and_network_bridge.json"))["agent_id"]
    result = assess(client, agent_id)
    response = client.post(
        "/v1/decisions",
        json={"assessment_id": result["audit"]["assessment_id"], "action": "accept"},
    )
    assert response.status_code == 400


def test_accept_and_reject_on_an_acceptable_assessment(client):
    agent_id = save(client, fixture_spec("clean_dev_agent.json"))["agent_id"]
    result = assess(client, agent_id)
    assessment_id = result["audit"]["assessment_id"]
    assert (
        client.post(
            "/v1/decisions", json={"assessment_id": assessment_id, "action": "accept"}
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/v1/decisions", json={"assessment_id": assessment_id, "action": "reject"}
        ).status_code
        == 200
    )


def test_evidence_endpoint_contains_findings_and_digest(client):
    saved = save(client, fixture_spec("file_and_network_bridge.json"))
    result = assess(client, saved["agent_id"])
    evidence = client.get(f"/v1/evidence/{result['audit']['assessment_id']}").json()

    assert evidence["decision"] == "UNACCEPTABLE"
    assert any(f["code"] == "BRIDGE" for f in evidence["findings"])
    assert evidence["drift"]["current_digest"] == saved["digest"]
    assert evidence["context"]["environment"] == "dev"

    markdown = evidence["evidence_markdown"]
    assert "# Aegis evidence pack" in markdown
    assert "BRIDGE" in markdown
    assert saved["digest"] in markdown
    assert "## Findings" in markdown


def test_evidence_for_unknown_assessment_is_404(client):
    assert client.get("/v1/evidence/asmt_missing").status_code == 404


def test_audit_endpoint_reports_snapshots_traces_and_decisions(client):
    v1 = approved_v1("drifted_after_approval.json")
    agent_id = save(client, v1)["agent_id"]
    client.post(f"/v1/agents/{agent_id}/approve")
    client.post(
        f"/v1/agents/{agent_id}/traces",
        json=[{"tool": "format_text", "args_redacted": {}, "ts": "2026-08-30T09:00:00+00:00"}],
    )
    save(client, fixture_spec("drifted_after_approval.json"))
    result = assess(client, agent_id)
    client.post(
        "/v1/decisions",
        json={
            "assessment_id": result["audit"]["assessment_id"],
            "action": "override",
            "override_reason": "Sandboxed replay only; tool surface reverted before any prod use.",
        },
    )

    audit = client.get(f"/v1/audit/{agent_id}").json()
    kinds = [snapshot["kind"] for snapshot in audit["snapshots"]]
    assert "approved" in kinds and "current" in kinds
    assert audit["traces_summary"]["count"] == 1
    assert audit["traces_summary"]["tools_seen"] == ["format_text"]
    assert audit["assessments"][0]["decision"] == "UNACCEPTABLE"
    assert audit["decisions"][0]["action"] == "override"


def test_policy_endpoint_exposes_every_rule_code(client):
    policy = client.get("/v1/policy").json()
    codes_seen = {rule["code"] for rule in policy["rules"]}
    assert "DRIFT_AFTER_APPROVAL" in codes_seen
    assert len(codes_seen) == 10
