"""Offline eval harness for the Aegis decision engine.

Calls run_assess directly -- no HTTP, no database -- so the risk logic can be
regression-tested on its own. Two suites run:

  1. the five shipped fixture cases in samples/eval_cases.json (must be 5/5)
  2. twelve synthetic cases generated in-code (must be at least 90% accurate)

Usage: python eval_runner.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from assess import run_assess
from inventory import load_agent

ROOT = Path(__file__).resolve().parent
AGENT_FIXTURES = ROOT / "fixtures" / "agents"
TRACE_FIXTURES = ROOT / "fixtures" / "traces"
CASES_PATH = ROOT / "samples" / "eval_cases.json"

# Fixed clock so trace-freshness checks are deterministic across runs.
EVAL_NOW = "2026-08-31T12:00:00+00:00"
RECENT_TS = "2026-08-30T09:00:00+00:00"

SYNTHETIC_MIN_ACCURACY = 0.90

HEADER = f"{'id':<26} {'expected':<14} {'got':<14} {'codes':<26} result"


def load_spec(filename: str) -> dict:
    spec = load_agent(AGENT_FIXTURES / filename)
    spec.pop("_approved_v1", None)
    return spec


def approved_spec(filename: str) -> dict:
    raw = load_agent(AGENT_FIXTURES / filename)
    variant = raw.get("_approved_v1")
    if variant:
        return load_agent(variant)
    return load_spec(filename)


def load_traces(filename: str) -> list:
    return json.loads((TRACE_FIXTURES / filename).read_text(encoding="utf-8"))


def evaluate(case: dict) -> dict:
    """Run one case and compare against its expectation."""
    spec = case["spec"]
    approved = case.get("approved_snapshot")
    traces = case.get("traces") or []
    result = run_assess(spec, case["context"], approved, traces, now=EVAL_NOW)
    codes = [finding["code"] for finding in result["findings"]]
    missing = [code for code in case["expected_codes"] if code not in codes]
    passed = result["decision"] == case["expected"] and not missing
    return {
        "id": case["id"],
        "expected": case["expected"],
        "got": result["decision"],
        "codes": codes,
        "missing": missing,
        "passed": passed,
    }


def print_row(outcome: dict) -> None:
    codes = ",".join(outcome["codes"]) or "(none)"
    if len(codes) > 25:
        codes = codes[:22] + "..."
    status = "OK" if outcome["passed"] else "MISS"
    print(
        f"{outcome['id']:<26} {outcome['expected']:<14} {outcome['got']:<14} "
        f"{codes:<26} {status}"
    )


def fixture_cases() -> list[dict]:
    raw_cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    cases = []
    for raw in raw_cases:
        filename = raw["agent_fixture"]
        case = {
            "id": raw["id"],
            "spec": load_spec(filename),
            "context": raw["context"],
            "expected": raw["expected"],
            "expected_codes": raw["expected_codes"],
            "approved_snapshot": approved_spec(filename) if raw["approved"] else None,
            "traces": load_traces("drift_trace.json") if raw["approved"] else load_traces("clean_trace.json"),
        }
        cases.append(case)
    return cases


def _agent(name, owner, autonomy, tools, servers) -> dict:
    return {
        "name": name,
        "owner": owner,
        "purpose": "synthetic eval case",
        "autonomy": autonomy,
        "tools": tools,
        "mcp_servers": servers,
    }


def synthetic_cases() -> list[dict]:
    """Twelve generated cases: 3 bridge, 3 shell-in-prod, 3 clean, 3 missing owner."""
    dev = {
        "environment": "dev",
        "data_class": "internal",
        "network": "allowlist",
        "human_gate": "in_the_loop",
    }
    prod = {
        "environment": "prod",
        "data_class": "internal",
        "network": "allowlist",
        "human_gate": "on_the_loop",
    }
    cases: list[dict] = []

    # 3 x bridge: one tool holding both, one MCP server exposing both, one via a
    # credentials-holding reader that also calls out.
    bridge_variants = [
        [{"name": "read_and_send", "description": "read then send", "permissions": ["read_files", "network"]}],
        [
            {"name": "read_local", "description": "read", "permissions": ["read_files"]},
            {"name": "post_out", "description": "post", "permissions": ["network"]},
        ],
        [
            {"name": "load_secrets", "description": "read", "permissions": ["read_files", "credentials"]},
            {"name": "sync_remote", "description": "sync", "permissions": ["network"]},
        ],
    ]
    for index, tools in enumerate(bridge_variants, start=1):
        servers = [{"name": "combined", "auth_type": "oauth", "tools": [t["name"] for t in tools]}]
        cases.append(
            {
                "id": f"syn-bridge-{index}",
                "spec": _agent(f"syn-bridge-{index}", "owner@example.gov.uk", "low", tools, servers),
                "context": dev,
                "expected": "UNACCEPTABLE",
                "expected_codes": ["BRIDGE"],
            }
        )

    # 3 x shell in a sensitive context.
    shell_variants = [
        ("syn-shell-1", prod, "medium"),
        ("syn-shell-2", dict(prod, data_class="confidential"), "low"),
        ("syn-shell-3", dict(dev, data_class="secret"), "low"),
    ]
    for name, context, autonomy in shell_variants:
        tools = [{"name": "run_cmd", "description": "run a command", "permissions": ["shell"]}]
        servers = [{"name": "exec", "auth_type": "oauth", "tools": ["run_cmd"]}]
        cases.append(
            {
                "id": name,
                "spec": _agent(name, "sre@example.gov.uk", autonomy, tools, servers),
                "context": context,
                "expected": "UNACCEPTABLE",
                "expected_codes": ["SHELL_UNSCOPED"],
            }
        )

    # 3 x clean.
    clean_variants = [
        ("syn-clean-1", [{"name": "search_docs", "description": "search", "permissions": []}], dev),
        (
            "syn-clean-2",
            [{"name": "summarise", "description": "summarise supplied text", "permissions": []}],
            dict(dev, environment="test"),
        ),
        (
            "syn-clean-3",
            [{"name": "read_notes", "description": "read notes", "permissions": ["read_files"]}],
            dict(dev, network="isolated"),
        ),
    ]
    for name, tools, context in clean_variants:
        servers = [{"name": "safe", "auth_type": "oauth", "tools": [t["name"] for t in tools]}]
        cases.append(
            {
                "id": name,
                "spec": _agent(name, "owner@example.gov.uk", "low", tools, servers),
                "context": context,
                "expected": "ACCEPTABLE",
                "expected_codes": [],
            }
        )

    # 3 x missing owner.
    for index, owner in enumerate(["", "   ", None], start=1):
        tools = [{"name": "search_docs", "description": "search", "permissions": []}]
        servers = [{"name": "safe", "auth_type": "oauth", "tools": ["search_docs"]}]
        spec = _agent(f"syn-owner-{index}", owner, "low", tools, servers)
        cases.append(
            {
                "id": f"syn-owner-{index}",
                "spec": spec,
                "context": dev,
                "expected": "UNACCEPTABLE",
                "expected_codes": ["UNKNOWN_OWNER"],
            }
        )

    return cases


def run_suite(title: str, cases: list[dict]) -> tuple[int, int]:
    print(title)
    print(HEADER)
    passes = 0
    for case in cases:
        outcome = evaluate(case)
        print_row(outcome)
        passes += 1 if outcome["passed"] else 0
    print(f"SCORE {passes}/{len(cases)}")
    return passes, len(cases)


def main() -> int:
    fixture_passes, fixture_total = run_suite("Fixture suite (samples/eval_cases.json)", fixture_cases())
    print()
    synth_passes, synth_total = run_suite("Synthetic suite (generated in-code)", synthetic_cases())

    accuracy = synth_passes / synth_total if synth_total else 1.0
    print(f"SYNTHETIC ACCURACY {accuracy:.0%} (threshold {SYNTHETIC_MIN_ACCURACY:.0%})")

    failed = False
    if fixture_passes != fixture_total:
        print("FAIL: fixture suite must be 5/5", file=sys.stderr)
        failed = True
    if accuracy < SYNTHETIC_MIN_ACCURACY:
        print("FAIL: synthetic accuracy below threshold", file=sys.stderr)
        failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
