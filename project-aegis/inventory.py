"""Agent spec loading, validation and inventory summarisation.

No HTTP and no SQLite here on purpose: a CISO must be able to reason about the
inventory logic in isolation, and the eval suite exercises it without a server.
"""

from __future__ import annotations

import json
from pathlib import Path

VALID_AUTONOMY = ("low", "medium", "high")
VALID_PERMISSIONS = ("read_files", "write_files", "network", "shell", "credentials")
VALID_AUTH_TYPES = ("none", "static_secret", "oauth")

VALID_ENVIRONMENTS = ("dev", "test", "prod")
VALID_DATA_CLASSES = ("public", "internal", "confidential", "secret")
VALID_NETWORKS = ("isolated", "allowlist", "unrestricted")
VALID_HUMAN_GATES = ("none", "on_the_loop", "in_the_loop")


def load_agent(source) -> dict:
    """Load and validate an agent spec from a path, a JSON string, or a dict.

    Raises ValueError with a message naming the offending field.
    """
    if isinstance(source, dict):
        spec = dict(source)
    elif isinstance(source, (str, Path)):
        text = Path(source).read_text(encoding="utf-8")
        try:
            spec = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"agent spec at {source} is not valid JSON: {exc}") from exc
        if not isinstance(spec, dict):
            raise ValueError(f"agent spec at {source} must be a JSON object")
    else:
        raise ValueError(f"cannot load agent spec from {type(source).__name__}")

    _validate(spec)
    return spec


def _validate(spec: dict) -> None:
    if not str(spec.get("name") or "").strip():
        raise ValueError("agent spec requires a non-empty 'name'")

    autonomy = spec.get("autonomy")
    if autonomy not in VALID_AUTONOMY:
        raise ValueError(f"agent 'autonomy' must be one of {VALID_AUTONOMY}, got {autonomy!r}")

    tools = spec.get("tools")
    if not isinstance(tools, list):
        raise ValueError("agent spec requires 'tools' to be a list")
    seen_tools: set[str] = set()
    for index, tool in enumerate(tools):
        if not isinstance(tool, dict):
            raise ValueError(f"tools[{index}] must be an object")
        name = str(tool.get("name") or "").strip()
        if not name:
            raise ValueError(f"tools[{index}] requires a non-empty 'name'")
        if name in seen_tools:
            raise ValueError(f"duplicate tool name {name!r}")
        seen_tools.add(name)
        permissions = tool.get("permissions")
        if not isinstance(permissions, list):
            raise ValueError(f"tool {name!r} requires 'permissions' to be a list")
        for permission in permissions:
            if permission not in VALID_PERMISSIONS:
                raise ValueError(
                    f"tool {name!r} has unknown permission {permission!r}; "
                    f"allowed: {VALID_PERMISSIONS}"
                )

    servers = spec.get("mcp_servers")
    if servers is None:
        servers = []
    if not isinstance(servers, list):
        raise ValueError("agent spec requires 'mcp_servers' to be a list")
    for index, server in enumerate(servers):
        if not isinstance(server, dict):
            raise ValueError(f"mcp_servers[{index}] must be an object")
        name = str(server.get("name") or "").strip()
        if not name:
            raise ValueError(f"mcp_servers[{index}] requires a non-empty 'name'")
        if server.get("auth_type") not in VALID_AUTH_TYPES:
            raise ValueError(
                f"mcp server {name!r} 'auth_type' must be one of {VALID_AUTH_TYPES}, "
                f"got {server.get('auth_type')!r}"
            )
        if not isinstance(server.get("tools") or [], list):
            raise ValueError(f"mcp server {name!r} requires 'tools' to be a list")


def validate_context(context: dict) -> dict:
    """Validate a deployment context. Returns the normalised context."""
    if not isinstance(context, dict):
        raise ValueError("context must be an object")
    checks = (
        ("environment", VALID_ENVIRONMENTS),
        ("data_class", VALID_DATA_CLASSES),
        ("network", VALID_NETWORKS),
        ("human_gate", VALID_HUMAN_GATES),
    )
    for field, allowed in checks:
        if context.get(field) not in allowed:
            raise ValueError(
                f"context '{field}' must be one of {allowed}, got {context.get(field)!r}"
            )
    return {field: context[field] for field, _ in checks}


def permissions_of(spec: dict) -> dict[str, set[str]]:
    """Map of tool name -> permission set."""
    return {
        str(tool.get("name", "")): {str(p) for p in (tool.get("permissions") or [])}
        for tool in (spec.get("tools") or [])
    }


def summarise(spec: dict) -> dict:
    """Flat inventory: tools, MCP servers, and the union of permissions held."""
    by_tool = permissions_of(spec)
    tools = [
        {
            "name": str(tool.get("name", "")),
            "description": str(tool.get("description", "")),
            "permissions": sorted(by_tool.get(str(tool.get("name", "")), set())),
        }
        for tool in (spec.get("tools") or [])
    ]
    servers = [
        {
            "name": str(server.get("name", "")),
            "auth_type": str(server.get("auth_type", "")),
            "tools": list(server.get("tools") or []),
        }
        for server in (spec.get("mcp_servers") or [])
    ]
    union: set[str] = set()
    for permissions in by_tool.values():
        union |= permissions
    return {
        "tools": sorted(tools, key=lambda t: t["name"]),
        "mcp_servers": sorted(servers, key=lambda s: s["name"]),
        "permission_union": sorted(union),
    }


def bridge_tools(spec: dict) -> list[str]:
    """Names of tools that on their own can read local files and reach the network."""
    return sorted(
        name
        for name, permissions in permissions_of(spec).items()
        if {"read_files", "network"} <= permissions
    )


def bridge_servers(spec: dict) -> list[str]:
    """MCP servers whose exposed tools jointly cover read_files and network.

    A single trust boundary that can both read local files and call out is an
    exfiltration bridge even when no individual tool holds both permissions.
    """
    by_tool = permissions_of(spec)
    bridging = []
    for server in spec.get("mcp_servers") or []:
        union: set[str] = set()
        for tool_name in server.get("tools") or []:
            union |= by_tool.get(str(tool_name), set())
        if {"read_files", "network"} <= union:
            bridging.append(str(server.get("name", "")))
    return sorted(bridging)


def detect_bridge(spec: dict) -> bool:
    """True if any one tool, or the agent as a whole via an MCP server, bridges
    local file reads to outbound network calls."""
    return bool(bridge_tools(spec)) or bool(bridge_servers(spec))
