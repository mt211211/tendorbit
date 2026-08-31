"""Canonical serialisation, digests and diffing for agent specs.

Pure functions only: no file, network or database access. The digest is the
anchor for drift detection (rug-pull) -- an approved snapshot is compared
against the current spec by hashing the same canonical form.
"""

from __future__ import annotations

import hashlib
import json

CANONICAL_SEPARATORS = (",", ":")


def _canonical_tools(spec: dict) -> list[dict]:
    tools = spec.get("tools") or []
    canon = [
        {
            "name": str(tool.get("name", "")),
            "description": str(tool.get("description", "")),
            "permissions": sorted(str(p) for p in (tool.get("permissions") or [])),
        }
        for tool in tools
    ]
    return sorted(canon, key=lambda t: t["name"])


def _canonical_servers(spec: dict) -> list[dict]:
    servers = spec.get("mcp_servers") or []
    canon = [
        {
            "name": str(server.get("name", "")),
            "auth_type": str(server.get("auth_type", "")),
            "tools": sorted(str(t) for t in (server.get("tools") or [])),
        }
        for server in servers
    ]
    return sorted(canon, key=lambda s: s["name"])


def canonical_spec(spec: dict) -> str:
    """Stable JSON string covering only the risk-bearing surface of a spec.

    Owner, purpose and autonomy are deliberately excluded: they are governance
    metadata, not the tool surface an agent can actually reach. Changing them
    must not look like a rug-pull.
    """
    payload = {
        "tools": _canonical_tools(spec),
        "mcp_servers": _canonical_servers(spec),
    }
    return json.dumps(payload, sort_keys=True, separators=CANONICAL_SEPARATORS)


def digest(spec: dict) -> str:
    """SHA-256 hex digest of the canonical spec."""
    return hashlib.sha256(canonical_spec(spec).encode("utf-8")).hexdigest()


def _tool_index(spec: dict) -> dict[str, dict]:
    return {tool["name"]: tool for tool in _canonical_tools(spec)}


def diff_specs(old: dict, new: dict) -> list[str]:
    """Tool names that were added, removed, or had description/permissions change."""
    old_tools = _tool_index(old)
    new_tools = _tool_index(new)
    changed: set[str] = set()

    changed.update(set(old_tools) ^ set(new_tools))
    for name in set(old_tools) & set(new_tools):
        before, after = old_tools[name], new_tools[name]
        if before["description"] != after["description"]:
            changed.add(name)
        elif before["permissions"] != after["permissions"]:
            changed.add(name)

    return sorted(changed)
