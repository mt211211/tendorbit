import json
from pathlib import Path

import pytest

from inventory import (
    bridge_servers,
    detect_bridge,
    load_agent,
    summarise,
    validate_context,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "agents"


def fixture(name):
    return load_agent(FIXTURES / name)


def test_load_agent_accepts_every_shipped_fixture():
    for path in sorted(FIXTURES.glob("*.json")):
        spec = load_agent(path)
        assert spec["name"]


def test_load_agent_accepts_a_dict():
    spec = load_agent({"name": "x", "autonomy": "low", "tools": [], "mcp_servers": []})
    assert spec["autonomy"] == "low"


def test_load_agent_rejects_missing_name():
    with pytest.raises(ValueError, match="name"):
        load_agent({"autonomy": "low", "tools": []})


def test_load_agent_rejects_bad_autonomy():
    with pytest.raises(ValueError, match="autonomy"):
        load_agent({"name": "x", "autonomy": "godlike", "tools": []})


def test_load_agent_rejects_unknown_permission():
    with pytest.raises(ValueError, match="permission"):
        load_agent(
            {
                "name": "x",
                "autonomy": "low",
                "tools": [{"name": "t", "description": "", "permissions": ["sudo"]}],
            }
        )


def test_load_agent_rejects_bad_auth_type():
    with pytest.raises(ValueError, match="auth_type"):
        load_agent(
            {
                "name": "x",
                "autonomy": "low",
                "tools": [],
                "mcp_servers": [{"name": "s", "auth_type": "magic", "tools": []}],
            }
        )


def test_validate_context_rejects_unknown_value():
    with pytest.raises(ValueError, match="network"):
        validate_context(
            {
                "environment": "dev",
                "data_class": "internal",
                "network": "carrier-pigeon",
                "human_gate": "none",
            }
        )


def test_detect_bridge_true_for_single_tool_holding_both():
    assert detect_bridge(fixture("file_and_network_bridge.json")) is True


def test_detect_bridge_false_for_clean_agent():
    assert detect_bridge(fixture("clean_dev_agent.json")) is False


def test_detect_bridge_true_when_one_mcp_server_exposes_both_capabilities():
    spec = {
        "name": "split-bridge",
        "autonomy": "low",
        "tools": [
            {"name": "read_local", "description": "read", "permissions": ["read_files"]},
            {"name": "post_out", "description": "post", "permissions": ["network"]},
        ],
        "mcp_servers": [
            {"name": "combined", "auth_type": "oauth", "tools": ["read_local", "post_out"]}
        ],
    }
    assert detect_bridge(spec) is True
    assert bridge_servers(spec) == ["combined"]


def test_detect_bridge_false_when_capabilities_sit_on_separate_servers():
    spec = {
        "name": "separated",
        "autonomy": "low",
        "tools": [
            {"name": "read_local", "description": "read", "permissions": ["read_files"]},
            {"name": "post_out", "description": "post", "permissions": ["network"]},
        ],
        "mcp_servers": [
            {"name": "reader", "auth_type": "oauth", "tools": ["read_local"]},
            {"name": "poster", "auth_type": "oauth", "tools": ["post_out"]},
        ],
    }
    assert detect_bridge(spec) is False


def test_summarise_permission_union_is_sorted_and_deduplicated():
    spec = {
        "name": "many",
        "autonomy": "low",
        "tools": [
            {"name": "b", "description": "", "permissions": ["network", "read_files"]},
            {"name": "a", "description": "", "permissions": ["read_files", "shell"]},
        ],
        "mcp_servers": [],
    }
    summary = summarise(spec)
    assert summary["permission_union"] == ["network", "read_files", "shell"]
    assert [tool["name"] for tool in summary["tools"]] == ["a", "b"]


def test_summarise_of_clean_fixture_has_no_dangerous_permissions():
    summary = summarise(fixture("clean_dev_agent.json"))
    assert summary["permission_union"] == []
    assert summary["mcp_servers"][0]["auth_type"] == "oauth"
