"""Request and response models for the Aegis API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Permission = Literal["read_files", "write_files", "network", "shell", "credentials"]
Autonomy = Literal["low", "medium", "high"]
AuthType = Literal["none", "static_secret", "oauth"]
Environment = Literal["dev", "test", "prod"]
DataClass = Literal["public", "internal", "confidential", "secret"]
Network = Literal["isolated", "allowlist", "unrestricted"]
HumanGate = Literal["none", "on_the_loop", "in_the_loop"]
Action = Literal["accept", "reject", "override"]


class ToolSpec(BaseModel):
    name: str
    description: str = ""
    permissions: list[Permission] = Field(default_factory=list)


class McpServerSpec(BaseModel):
    name: str
    auth_type: AuthType
    tools: list[str] = Field(default_factory=list)


class AgentSpecIn(BaseModel):
    name: str
    owner: str = ""
    purpose: str = ""
    autonomy: Autonomy
    tools: list[ToolSpec] = Field(default_factory=list)
    mcp_servers: list[McpServerSpec] = Field(default_factory=list)


class ContextIn(BaseModel):
    environment: Environment
    data_class: DataClass
    network: Network
    human_gate: HumanGate


class TraceCall(BaseModel):
    tool: str
    args_redacted: dict = Field(default_factory=dict)
    ts: str


class AssessRequest(BaseModel):
    agent_id: str
    context: ContextIn
    now: str | None = None


class DecisionRequest(BaseModel):
    assessment_id: str
    action: Action
    override_reason: str | None = None
    actor: str = "ciso"


class AgentSaved(BaseModel):
    agent_id: str
    digest: str
    snapshot_id: str | None = None


class SnapshotSaved(BaseModel):
    snapshot_id: str
    agent_id: str
    digest: str


class TracesSaved(BaseModel):
    agent_id: str
    stored: int
    trace_ids: list[str]
