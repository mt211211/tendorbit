"""CISO red lines, as data plus one pure checking function.

DEFAULT_POLICY is v0.1 and hard-coded. It is expressed as data so a later
version can load an equivalent JSON document without changing the engine.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from inventory import bridge_servers, bridge_tools, detect_bridge, permissions_of

BLOCK = "block"
REVIEW = "review"

TRACE_WINDOW_DAYS = 7

DEFAULT_POLICY = {
    "version": "0.1",
    "name": "Aegis default CISO policy",
    "trace_window_days": TRACE_WINDOW_DAYS,
    "rules": [
        {
            "code": "BRIDGE",
            "severity": BLOCK,
            "title": "File read bridged to outbound network",
            "rationale": "A path that can read local files and call out is an exfiltration bridge.",
        },
        {
            "code": "SHELL_UNSCOPED",
            "severity": BLOCK,
            "title": "Unscoped shell in a sensitive context",
            "rationale": "Shell execution in prod, or over confidential/secret data, is unbounded.",
        },
        {
            "code": "AUTH_NONE_NETWORK",
            "severity": BLOCK,
            "title": "Unauthenticated MCP server off an isolated network",
            "rationale": "An unauthenticated tool server is impersonable unless network-isolated.",
        },
        {
            "code": "SECRET_DATA_UNRESTRICTED_NET",
            "severity": BLOCK,
            "title": "Sensitive data with unrestricted egress",
            "rationale": "Confidential or secret data must not sit behind unrestricted egress.",
        },
        {
            "code": "AUTONOMY_NO_GATE",
            "severity": BLOCK,
            "title": "High autonomy with no human gate",
            "rationale": "High autonomy without a human gate removes the last containment step.",
        },
        {
            "code": "DRIFT_AFTER_APPROVAL",
            "severity": BLOCK,
            "title": "Tool surface changed after approval",
            "rationale": "The approved snapshot no longer matches the running spec (rug-pull).",
        },
        {
            "code": "UNKNOWN_OWNER",
            "severity": BLOCK,
            "title": "No accountable owner",
            "rationale": "An agent with no named owner cannot be operationally governed.",
        },
        {
            "code": "STATIC_SECRET",
            "severity": REVIEW,
            "title": "MCP server authenticated by static secret",
            "rationale": "Static secrets do not rotate and are widely copied.",
        },
        {
            "code": "HIGH_AUTONOMY_CONFIDENTIAL",
            "severity": REVIEW,
            "title": "High autonomy over confidential data",
            "rationale": "High autonomy over confidential data warrants named sign-off.",
        },
        {
            "code": "NO_TRACE",
            "severity": REVIEW,
            "title": "Approved agent with no recent traces",
            "rationale": (
                "An approved agent with no tool-call evidence in the last "
                f"{TRACE_WINDOW_DAYS} days cannot be monitored."
            ),
        },
    ],
}

RULES_BY_CODE = {rule["code"]: rule for rule in DEFAULT_POLICY["rules"]}


def _finding(code: str, detail: str) -> dict:
    return {"code": code, "severity": RULES_BY_CODE[code]["severity"], "detail": detail}


def _parse_ts(value) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def recent_traces(traces, now=None, window_days: int = TRACE_WINDOW_DAYS) -> list:
    """Traces carrying a timestamp inside the window ending at ``now``."""
    reference = _parse_ts(now) if now else None
    if reference is None:
        reference = datetime.now(timezone.utc)
    cutoff = reference - timedelta(days=window_days)
    fresh = []
    for trace in traces or []:
        stamp = _parse_ts((trace or {}).get("ts")) if isinstance(trace, dict) else None
        if stamp is not None and cutoff <= stamp <= reference:
            fresh.append(trace)
    return fresh


def check_policy(spec, context, approved_digest, current_digest, traces, now=None) -> list[dict]:
    """Evaluate the default policy for one agent in one context.

    ``approved_digest`` is None when the agent has never been approved; drift is
    only meaningful against an approval.
    """
    findings: list[dict] = []

    environment = (context or {}).get("environment")
    data_class = (context or {}).get("data_class")
    network = (context or {}).get("network")
    human_gate = (context or {}).get("human_gate")
    autonomy = (spec or {}).get("autonomy")

    # BRIDGE
    if detect_bridge(spec):
        tools = bridge_tools(spec)
        servers = bridge_servers(spec)
        parts = []
        if tools:
            parts.append(f"tool(s) {', '.join(tools)} hold read_files and network")
        if servers:
            parts.append(f"MCP server(s) {', '.join(servers)} expose both capabilities")
        findings.append(_finding("BRIDGE", "; ".join(parts)))

    # SHELL_UNSCOPED
    shell_tools = sorted(
        name for name, permissions in permissions_of(spec).items() if "shell" in permissions
    )
    if shell_tools and (environment == "prod" or data_class in ("confidential", "secret")):
        findings.append(
            _finding(
                "SHELL_UNSCOPED",
                f"tool(s) {', '.join(shell_tools)} can execute shell in "
                f"environment={environment}, data_class={data_class}",
            )
        )

    # AUTH_NONE_NETWORK
    unauthenticated = sorted(
        str(server.get("name", ""))
        for server in (spec or {}).get("mcp_servers") or []
        if server.get("auth_type") == "none"
    )
    if unauthenticated and network != "isolated":
        findings.append(
            _finding(
                "AUTH_NONE_NETWORK",
                f"MCP server(s) {', '.join(unauthenticated)} use auth_type=none on "
                f"network={network}",
            )
        )

    # SECRET_DATA_UNRESTRICTED_NET
    if data_class in ("confidential", "secret") and network == "unrestricted":
        findings.append(
            _finding(
                "SECRET_DATA_UNRESTRICTED_NET",
                f"data_class={data_class} with unrestricted egress",
            )
        )

    # AUTONOMY_NO_GATE
    if autonomy == "high" and human_gate == "none":
        findings.append(
            _finding("AUTONOMY_NO_GATE", "autonomy=high with human_gate=none")
        )

    # DRIFT_AFTER_APPROVAL
    if approved_digest and current_digest and approved_digest != current_digest:
        findings.append(
            _finding(
                "DRIFT_AFTER_APPROVAL",
                f"current digest {current_digest[:12]} does not match approved "
                f"{approved_digest[:12]}",
            )
        )

    # UNKNOWN_OWNER
    if not str((spec or {}).get("owner") or "").strip():
        findings.append(_finding("UNKNOWN_OWNER", "agent.owner is empty"))

    # STATIC_SECRET
    static_secret = sorted(
        str(server.get("name", ""))
        for server in (spec or {}).get("mcp_servers") or []
        if server.get("auth_type") == "static_secret"
    )
    if static_secret:
        findings.append(
            _finding(
                "STATIC_SECRET",
                f"MCP server(s) {', '.join(static_secret)} authenticate with a static secret",
            )
        )

    # HIGH_AUTONOMY_CONFIDENTIAL
    if autonomy == "high" and data_class == "confidential":
        findings.append(
            _finding("HIGH_AUTONOMY_CONFIDENTIAL", "autonomy=high over confidential data")
        )

    # NO_TRACE
    if approved_digest and not recent_traces(traces, now=now):
        findings.append(
            _finding(
                "NO_TRACE",
                f"approved agent has no tool-call traces in the last {TRACE_WINDOW_DAYS} days",
            )
        )

    return findings
