import copy
from pathlib import Path

from assess import run_assess
from inventory import load_agent

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "agents"
NOW = "2026-08-31T12:00:00+00:00"

DEV_CONTEXT = {
    "environment": "dev",
    "data_class": "internal",
    "network": "allowlist",
    "human_gate": "in_the_loop",
}


def fixture(name):
    spec = load_agent(FIXTURES / name)
    spec.pop("_approved_v1", None)
    return spec


def codes(result):
    return {finding["code"] for finding in result["findings"]}


def assess(spec, context=None, approved=None, traces=None):
    return run_assess(spec, context or DEV_CONTEXT, approved, traces or [], now=NOW)


def test_clean_fixture_is_acceptable():
    result = assess(fixture("clean_dev_agent.json"))
    assert result["decision"] == "ACCEPTABLE"
    assert result["score"] == 100
    assert result["findings"] == []
    assert result["drift"]["detected"] is False
    assert result["audit"]["human_required"] is False


def test_block_bridge():
    result = assess(fixture("file_and_network_bridge.json"))
    assert "BRIDGE" in codes(result)
    assert result["decision"] == "UNACCEPTABLE"


def test_block_shell_unscoped():
    context = {
        "environment": "prod",
        "data_class": "confidential",
        "network": "allowlist",
        "human_gate": "on_the_loop",
    }
    result = assess(fixture("prod_shell_agent.json"), context)
    assert "SHELL_UNSCOPED" in codes(result)
    assert result["decision"] == "UNACCEPTABLE"


def test_shell_is_not_blocked_in_a_dev_sandbox_on_internal_data():
    result = assess(fixture("prod_shell_agent.json"), DEV_CONTEXT)
    assert "SHELL_UNSCOPED" not in codes(result)
    assert result["decision"] == "ACCEPTABLE"


def test_block_auth_none_network():
    result = assess(fixture("unauth_mcp_network.json"), DEV_CONTEXT)
    assert "AUTH_NONE_NETWORK" in codes(result)
    assert result["decision"] == "UNACCEPTABLE"


def test_auth_none_is_allowed_on_an_isolated_network():
    context = dict(DEV_CONTEXT, network="isolated")
    result = assess(fixture("unauth_mcp_network.json"), context)
    assert "AUTH_NONE_NETWORK" not in codes(result)


def test_block_secret_data_unrestricted_net():
    context = {
        "environment": "prod",
        "data_class": "secret",
        "network": "unrestricted",
        "human_gate": "in_the_loop",
    }
    result = assess(fixture("clean_dev_agent.json"), context)
    assert "SECRET_DATA_UNRESTRICTED_NET" in codes(result)
    assert result["decision"] == "UNACCEPTABLE"


def test_block_autonomy_no_gate():
    spec = fixture("clean_dev_agent.json")
    spec["autonomy"] = "high"
    context = dict(DEV_CONTEXT, human_gate="none")
    result = assess(spec, context)
    assert "AUTONOMY_NO_GATE" in codes(result)
    assert result["decision"] == "UNACCEPTABLE"


def test_block_drift_after_approval():
    raw = load_agent(FIXTURES / "drifted_after_approval.json")
    approved = raw["_approved_v1"]
    current = fixture("drifted_after_approval.json")
    result = assess(current, DEV_CONTEXT, approved=approved, traces=[{"tool": "format_text", "ts": NOW}])
    assert "DRIFT_AFTER_APPROVAL" in codes(result)
    assert result["decision"] == "UNACCEPTABLE"
    assert result["drift"]["detected"] is True
    assert result["drift"]["changed_tools"] == ["format_text"]


def test_no_drift_when_approved_spec_is_unchanged():
    spec = fixture("clean_dev_agent.json")
    result = assess(spec, approved=copy.deepcopy(spec), traces=[{"tool": "search_docs", "ts": NOW}])
    assert "DRIFT_AFTER_APPROVAL" not in codes(result)
    assert result["drift"]["detected"] is False


def test_block_unknown_owner():
    spec = fixture("clean_dev_agent.json")
    spec["owner"] = "   "
    result = assess(spec)
    assert "UNKNOWN_OWNER" in codes(result)
    assert result["decision"] == "UNACCEPTABLE"


def test_review_static_secret_gives_conditional():
    spec = fixture("clean_dev_agent.json")
    spec["mcp_servers"][0]["auth_type"] = "static_secret"
    result = assess(spec)
    assert codes(result) == {"STATIC_SECRET"}
    assert result["decision"] == "CONDITIONAL"
    assert result["score"] == 90
    assert result["audit"]["human_required"] is True


def test_review_high_autonomy_confidential():
    spec = fixture("clean_dev_agent.json")
    spec["autonomy"] = "high"
    context = dict(DEV_CONTEXT, data_class="confidential")
    result = assess(spec, context)
    assert "HIGH_AUTONOMY_CONFIDENTIAL" in codes(result)
    assert result["decision"] == "CONDITIONAL"


def test_review_no_trace_for_approved_agent_without_recent_calls():
    spec = fixture("clean_dev_agent.json")
    result = assess(spec, approved=copy.deepcopy(spec), traces=[])
    assert "NO_TRACE" in codes(result)
    assert result["decision"] == "CONDITIONAL"


def test_traces_older_than_the_window_do_not_count():
    spec = fixture("clean_dev_agent.json")
    stale = [{"tool": "search_docs", "ts": "2026-01-01T00:00:00+00:00"}]
    result = assess(spec, approved=copy.deepcopy(spec), traces=stale)
    assert "NO_TRACE" in codes(result)


def test_recent_traces_clear_the_no_trace_finding():
    spec = fixture("clean_dev_agent.json")
    fresh = [{"tool": "search_docs", "ts": "2026-08-30T09:00:00+00:00"}]
    result = assess(spec, approved=copy.deepcopy(spec), traces=fresh)
    assert result["decision"] == "ACCEPTABLE"


def test_score_floors_at_zero_and_penalties_stack():
    spec = fixture("file_and_network_bridge.json")
    spec["owner"] = ""
    spec["autonomy"] = "high"
    spec["tools"][0]["permissions"] = ["read_files", "network", "shell"]
    spec["mcp_servers"][0]["auth_type"] = "none"
    context = {
        "environment": "prod",
        "data_class": "secret",
        "network": "unrestricted",
        "human_gate": "none",
    }
    result = assess(spec, context)
    assert result["score"] == 0
    assert result["decision"] == "UNACCEPTABLE"


def test_output_shape_matches_the_api_contract():
    result = assess(fixture("clean_dev_agent.json"))
    assert set(result) == {"decision", "score", "findings", "inventory", "drift", "audit"}
    assert set(result["inventory"]) == {"tools", "mcp_servers", "permissions"}
    assert {"detected", "changed_tools"} <= set(result["drift"])
    assert {"assessment_id", "agent_id", "checked_at", "human_required"} <= set(result["audit"])
    assert result["audit"]["assessment_id"].startswith("asmt_")
