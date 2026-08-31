"""SQLite persistence for Aegis. Standard-library sqlite3 only.

The database is created on first use at data/aegis.db (override with AEGIS_DB).
Nothing here makes network calls or executes anything from a scanned spec.
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_DB_PATH = ROOT / "data" / "aegis.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS agents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    owner TEXT,
    purpose TEXT,
    autonomy TEXT NOT NULL,
    spec_json TEXT NOT NULL,
    created_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_agents_name ON agents(name);

CREATE TABLE IF NOT EXISTS contexts (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    environment TEXT NOT NULL,
    data_class TEXT NOT NULL,
    network TEXT NOT NULL,
    human_gate TEXT NOT NULL,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS snapshots (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    digest TEXT NOT NULL,
    spec_json TEXT NOT NULL,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS traces (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS assessments (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    context_id TEXT NOT NULL,
    decision TEXT NOT NULL,
    score INTEGER NOT NULL,
    findings_json TEXT NOT NULL,
    inventory_json TEXT NOT NULL,
    drift_json TEXT NOT NULL,
    checked_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS decisions (
    id TEXT PRIMARY KEY,
    assessment_id TEXT NOT NULL,
    action TEXT NOT NULL,
    override_reason TEXT,
    actor TEXT NOT NULL DEFAULT 'ciso',
    decided_at TEXT NOT NULL
);
"""


def db_path() -> Path:
    override = os.environ.get("AEGIS_DB")
    return Path(override) if override else DEFAULT_DB_PATH


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)


# --- agents -----------------------------------------------------------------


def upsert_agent(spec: dict) -> str:
    """Insert or update an agent, keyed on name. Returns the agent id."""
    name = str(spec.get("name") or "").strip()
    payload = json.dumps(spec, sort_keys=True)
    with connect() as conn:
        row = conn.execute("SELECT id FROM agents WHERE name = ?", (name,)).fetchone()
        if row:
            agent_id = row["id"]
            conn.execute(
                "UPDATE agents SET owner = ?, purpose = ?, autonomy = ?, spec_json = ? "
                "WHERE id = ?",
                (spec.get("owner", ""), spec.get("purpose", ""), spec.get("autonomy"), payload, agent_id),
            )
        else:
            agent_id = new_id("agt")
            conn.execute(
                "INSERT INTO agents (id, name, owner, purpose, autonomy, spec_json, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    agent_id,
                    name,
                    spec.get("owner", ""),
                    spec.get("purpose", ""),
                    spec.get("autonomy"),
                    payload,
                    now_iso(),
                ),
            )
    return agent_id


def get_agent(agent_id: str) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM agents WHERE id = ?", (agent_id,)).fetchone()
    return dict(row) if row else None


def list_agents() -> list[dict]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM agents ORDER BY name").fetchall()
    return [dict(row) for row in rows]


def agent_spec(agent_id: str) -> dict | None:
    agent = get_agent(agent_id)
    return json.loads(agent["spec_json"]) if agent else None


# --- contexts ---------------------------------------------------------------


def add_context(agent_id: str, context: dict) -> str:
    context_id = new_id("ctx")
    with connect() as conn:
        conn.execute(
            "INSERT INTO contexts (id, agent_id, environment, data_class, network, human_gate, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                context_id,
                agent_id,
                context["environment"],
                context["data_class"],
                context["network"],
                context["human_gate"],
                now_iso(),
            ),
        )
    return context_id


def get_context(context_id: str) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM contexts WHERE id = ?", (context_id,)).fetchone()
    return dict(row) if row else None


# --- snapshots --------------------------------------------------------------


def add_snapshot(agent_id: str, kind: str, spec: dict, spec_digest: str) -> str:
    snapshot_id = new_id("snap")
    with connect() as conn:
        conn.execute(
            "INSERT INTO snapshots (id, agent_id, kind, digest, spec_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (snapshot_id, agent_id, kind, spec_digest, json.dumps(spec, sort_keys=True), now_iso()),
        )
    return snapshot_id


def latest_snapshot(agent_id: str, kind: str) -> dict | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM snapshots WHERE agent_id = ? AND kind = ? "
            "ORDER BY created_at DESC, rowid DESC LIMIT 1",
            (agent_id, kind),
        ).fetchone()
    return dict(row) if row else None


def list_snapshots(agent_id: str) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM snapshots WHERE agent_id = ? ORDER BY created_at ASC, rowid ASC",
            (agent_id,),
        ).fetchall()
    return [dict(row) for row in rows]


# --- traces -----------------------------------------------------------------


def add_traces(agent_id: str, calls: list[dict]) -> list[str]:
    ids = []
    with connect() as conn:
        for call in calls:
            trace_id = new_id("trc")
            ids.append(trace_id)
            conn.execute(
                "INSERT INTO traces (id, agent_id, payload_json, created_at) VALUES (?, ?, ?, ?)",
                (trace_id, agent_id, json.dumps(call, sort_keys=True), now_iso()),
            )
    return ids


def list_traces(agent_id: str) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT payload_json FROM traces WHERE agent_id = ? ORDER BY created_at ASC, rowid ASC",
            (agent_id,),
        ).fetchall()
    return [json.loads(row["payload_json"]) for row in rows]


def count_traces(agent_id: str) -> int:
    with connect() as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM traces WHERE agent_id = ?", (agent_id,)).fetchone()
    return int(row["n"])


# --- assessments ------------------------------------------------------------


def save_assessment(result: dict, agent_id: str, context_id: str) -> str:
    assessment_id = result["audit"]["assessment_id"]
    with connect() as conn:
        conn.execute(
            "INSERT INTO assessments (id, agent_id, context_id, decision, score, findings_json, "
            "inventory_json, drift_json, checked_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                assessment_id,
                agent_id,
                context_id,
                result["decision"],
                result["score"],
                json.dumps(result["findings"]),
                json.dumps(result["inventory"]),
                json.dumps(result["drift"]),
                result["audit"]["checked_at"],
            ),
        )
    return assessment_id


def get_assessment(assessment_id: str) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM assessments WHERE id = ?", (assessment_id,)).fetchone()
    return dict(row) if row else None


def list_assessments(agent_id: str) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM assessments WHERE agent_id = ? ORDER BY checked_at DESC, rowid DESC",
            (agent_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def latest_assessment_per_agent() -> list[dict]:
    """Newest assessment for each agent, newest first."""
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT a.*, ag.name AS agent_name, ag.owner AS agent_owner,
                   c.environment, c.data_class, c.network, c.human_gate
            FROM assessments a
            JOIN agents ag ON ag.id = a.agent_id
            LEFT JOIN contexts c ON c.id = a.context_id
            WHERE a.rowid IN (
                SELECT rowid FROM assessments b
                WHERE b.agent_id = a.agent_id
                ORDER BY b.checked_at DESC, b.rowid DESC LIMIT 1
            )
            ORDER BY a.checked_at DESC, a.rowid DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


# --- decisions --------------------------------------------------------------


def add_decision(assessment_id: str, action: str, override_reason: str | None, actor: str) -> dict:
    decision_id = new_id("dec")
    decided_at = now_iso()
    with connect() as conn:
        conn.execute(
            "INSERT INTO decisions (id, assessment_id, action, override_reason, actor, decided_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (decision_id, assessment_id, action, override_reason, actor, decided_at),
        )
    return {
        "id": decision_id,
        "assessment_id": assessment_id,
        "action": action,
        "override_reason": override_reason,
        "actor": actor,
        "decided_at": decided_at,
    }


def list_decisions(assessment_id: str) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM decisions WHERE assessment_id = ? ORDER BY decided_at ASC, rowid ASC",
            (assessment_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def decisions_for_agent(agent_id: str) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT d.* FROM decisions d JOIN assessments a ON a.id = d.assessment_id "
            "WHERE a.agent_id = ? ORDER BY d.decided_at ASC, d.rowid ASC",
            (agent_id,),
        ).fetchall()
    return [dict(row) for row in rows]
