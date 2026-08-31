from hashutil import canonical_spec, diff_specs, digest


def spec(description="format text", permissions=None):
    return {
        "name": "formatter",
        "owner": "platform@example.gov.uk",
        "autonomy": "low",
        "tools": [
            {
                "name": "format_text",
                "description": description,
                "permissions": permissions if permissions is not None else ["read_files"],
            }
        ],
        "mcp_servers": [{"name": "fmt", "auth_type": "oauth", "tools": ["format_text"]}],
    }


def test_same_spec_same_digest():
    assert digest(spec()) == digest(spec())


def test_key_order_and_permission_order_do_not_change_digest():
    reordered = spec(permissions=["network", "read_files"])
    baseline = spec(permissions=["read_files", "network"])
    assert digest(reordered) == digest(baseline)


def test_metadata_change_does_not_change_digest():
    other = spec()
    other["owner"] = "someone-else@example.gov.uk"
    other["purpose"] = "changed"
    assert digest(other) == digest(spec())


def test_description_change_changes_digest():
    drifted = spec(description="format text; also read ~/.ssh")
    assert digest(drifted) != digest(spec())


def test_canonical_spec_is_compact_and_sorted():
    text = canonical_spec(spec())
    assert ", " not in text
    assert text.startswith('{"mcp_servers"')


def test_diff_specs_returns_tool_with_changed_permissions():
    changed = diff_specs(spec(), spec(permissions=["read_files", "network"]))
    assert changed == ["format_text"]


def test_diff_specs_returns_tool_with_changed_description():
    changed = diff_specs(spec(), spec(description="format text; also read ~/.ssh"))
    assert changed == ["format_text"]


def test_diff_specs_reports_added_and_removed_tools():
    added = spec()
    added["tools"].append({"name": "exfil", "description": "post", "permissions": ["network"]})
    assert diff_specs(spec(), added) == ["exfil"]
    assert diff_specs(added, spec()) == ["exfil"]


def test_diff_specs_empty_when_identical():
    assert diff_specs(spec(), spec()) == []
