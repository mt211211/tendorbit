# Project Aegis — Open CISO Agent-Risk Workbench

An open, local-first workbench that helps a CISO answer one question:

> **Is this specific agent acceptable in this specific context?**

Aegis inventories agents and MCP servers, scores risk against a written policy,
records tool-call traces, detects when a tool description changes after approval
(runtime drift / rug-pull), and exports an evidence pack a CISO can file.

Everything is deterministic. There is no model in the decision path, so the same
spec in the same context always produces the same decision, and every finding
can be traced to a named policy rule.

## What Aegis is

- An **assurance and monitoring** workbench for agent adoption decisions.
- A **deterministic policy engine**: 7 blocking rules, 3 review rules, a 0–100
  score, and one of three decisions — `ACCEPTABLE`, `CONDITIONAL`, `UNACCEPTABLE`.
- A **drift detector**: it hashes the tool surface (names, descriptions,
  permissions, MCP servers) at approval time and re-checks it on every
  assessment, so a tool description that quietly changes after sign-off becomes a
  blocking finding rather than a silent capability increase.
- An **evidence generator**: every assessment exports as JSON plus a markdown
  pack recording the agent, the context, the inventory, the findings, the drift,
  the score, the decision, the human override and its reason, and the timestamps.
- **Open source, local, and boring on purpose** — Python, SQLite, and server-rendered
  HTML, so it can be read, forked and adopted without adopting a platform.

## What Aegis is not

- **Not an agent.** It does not act on production systems, and it will not block,
  quarantine or throttle anything. It produces a decision and a record; humans act.
- **Not a scanner.** It never fetches, launches, connects to or executes an MCP
  server, and it never runs a tool from a spec it has been given. It reads the
  spec, config and traces you hand it, as data.
- **Not a model evaluation tool.** It assesses the deployment surface — tools,
  permissions, MCP auth, context, autonomy, human gate — not model behaviour.
- **Not connected to anything.** No live government or NHS systems, no SSO, no
  SIEM, no cloud, no telemetry, no outbound calls of any kind.

## Constraints this demonstrator is built under

- **£0 / $0.** Local Python only. No paid APIs, no cloud accounts, no SaaS, no
  paid CI, no Docker required.
- **No live MCP execution.** The app never executes an untrusted MCP server,
  never runs a shell tool from a scanned server, and never sends credentials
  anywhere. Scanned specs are inert data.
- **Synthetic data only.** The five shipped fixtures are invented. There is no
  real org secret, no real patient data and no live MCP server anywhere in this repo.
- **Binds to `127.0.0.1` only.**
- **No LLM in the decision path.** An optional local model is out of scope until
  the eval suite is green and stays green.

## UK Ltd note

This repository is the **technical demonstrator** for the Sovereign AI R&D
Procurement Scheme, **Challenge 3 (NCSC) — Enabling safe AI agent adoption**.
It is code and evidence only. Company registration, the Approved Supplier List
Expression of Interest, and the Full Application are separate commercial and
administrative steps and are not represented in this repo.

## Setup

Requires Python 3.11+. Nothing else.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python seed.py
python eval_runner.py
pytest -q
uvicorn app:app --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000>.

`seed.py` creates `data/aegis.db` on first run and loads the five synthetic
fixtures. It is idempotent — run it as often as you like. `data/` is gitignored;
delete it to start clean.

`eval_runner.py` must print `SCORE 5/5` and exit 0. `pytest -q` must be green.

## 90-second demo

With `python seed.py` already run and the server up at
<http://127.0.0.1:8000>:

1. **A blocked exfiltration bridge.** In pane 1, pick
   `file_and_network_bridge` from *Load fixture* → **Save agent** → **Run assess**.
   Pane 2 shows **UNACCEPTABLE**, score 75, finding `BRIDGE`: one tool holds both
   `read_files` and `network`, so it can read local files and post them out.
2. **A clean agent.** Pick `clean_dev_agent` → **Save agent** → **Run assess**.
   **ACCEPTABLE**, score 100, no findings — a low-autonomy doc-search agent in a
   dev sandbox on an allowlisted network with a human in the loop.
3. **A rug-pull after approval.** Pick `drifted_after_approval (v2 — drifted)`
   → **Save agent** → **Run assess**. **UNACCEPTABLE**, finding
   `DRIFT_AFTER_APPROVAL`. The approved tool was described as `format text`; the
   running tool now says `format text; also read ~/.ssh`. Aegis names the changed
   tool and shows the approved digest next to the current one.
   *(From an empty database, first load `drifted_after_approval (v1 — approve this
   first)` → **Save agent** → **Approve snapshot**, then continue as above.)*
4. **File the evidence.** Click **Download evidence pack** for a markdown pack
   with agent, context, inventory, findings, drift digests, decision and score.
   The pack is also previewed in place.
5. **Record the human call.** In pane 3, the queue lists the latest assessment
   per agent. **Accept** is refused on an `UNACCEPTABLE` row; **Override**
   requires a reason of at least 20 characters, and the reason is stored on the
   decision and reappears in the evidence pack.

No curl at any point.

## Mapping to the NCSC challenge

Challenge 3 asks for *"an evidence-based, operational, and ideally automated risk
management approach for CISOs to support risk-based decision-making for specific
agents in specific contexts"*, covering *"both resilience and cyber security
risks"*, and prefers solutions built on open-source frameworks that support
wide-scale adoption.

| Challenge language | How Aegis addresses it |
| --- | --- |
| **For CISOs** | The user is the accountable risk owner, not a developer. One page, one verdict, one queue, one filed pack. Overrides are theirs to make and are recorded with a reason and an actor. |
| **Specific agent** | An agent is a concrete spec: named tools, per-tool permissions, and the MCP servers exposing them — hashed into a snapshot, not described in prose. |
| **Specific context** | The same agent is assessed per context: environment, data class, network posture, human gate. A shell tool is `ACCEPTABLE` in a dev sandbox and `UNACCEPTABLE` in prod. The context is part of the decision and part of the evidence. |
| **Evidence-based** | Every finding names a policy rule code and states the fact that triggered it. Every assessment is stored with its inventory, digests and timestamp, and exports as a filable pack. |
| **Operational** | Assessment is a re-run, not a one-off review: approve a snapshot, keep sending traces, re-assess, and drift or a monitoring gap shows up as a finding. |
| **Automated** | The whole decision path is a pure function with an offline eval suite (`eval_runner.py`) and unit tests, so it can run in a pipeline as well as in a browser. |
| **Cyber security risk** | `BRIDGE` (file-read to outbound network), `SHELL_UNSCOPED`, `AUTH_NONE_NETWORK`, `SECRET_DATA_UNRESTRICTED_NET`, `STATIC_SECRET`, and `DRIFT_AFTER_APPROVAL` for post-approval tool-description tampering. |
| **Resilience / operational risk** | `UNKNOWN_OWNER` (no accountable owner), `AUTONOMY_NO_GATE` (no human containment step), `HIGH_AUTONOMY_CONFIDENTIAL`, and `NO_TRACE` (an approved agent nobody is actually monitoring). |
| **Architecture, monitoring and controls** | Architecture: the inventory and permission union make the reachable surface explicit, per MCP trust boundary. Monitoring: traces and the 7-day trace window. Controls: the approval snapshot, the block/review policy, and the override gate. |
| **Open-source, wide-scale adoption** | Six dependencies, standard-library SQLite, no build step, no account, no container required. Policy rules are data, so a department can fork the policy without forking the engine. |
| **Adoption at pace** | The default answer is not "no". A clean agent in a sensible context returns `ACCEPTABLE` in one click with a filed pack, so low-risk adoption is fast and only genuine red lines stop. |

## Policy v0.1

**Block** (any one makes the decision `UNACCEPTABLE`):

| Code | Fires when |
| --- | --- |
| `BRIDGE` | A tool can read local files *and* make outbound network calls — or one MCP server exposes tools that jointly can. |
| `SHELL_UNSCOPED` | A tool can execute shell and the context is `prod`, or the data class is `confidential`/`secret`. |
| `AUTH_NONE_NETWORK` | An MCP server has `auth_type: none` and the network is not `isolated`. |
| `SECRET_DATA_UNRESTRICTED_NET` | Data class is `confidential`/`secret` and the network is `unrestricted`. |
| `AUTONOMY_NO_GATE` | Autonomy is `high` and the human gate is `none`. |
| `DRIFT_AFTER_APPROVAL` | The current tool snapshot no longer matches the approved snapshot. |
| `UNKNOWN_OWNER` | The agent has no owner. |

**Review** (no block + at least one review = `CONDITIONAL`):

| Code | Fires when |
| --- | --- |
| `STATIC_SECRET` | An MCP server authenticates with a static secret. |
| `HIGH_AUTONOMY_CONFIDENTIAL` | Autonomy is `high` over `confidential` data. |
| `NO_TRACE` | An approved agent has no tool-call traces in the last 7 days. |

**Score**: start at 100, −25 per block, −10 per review, floor 0.
**Decision**: any block → `UNACCEPTABLE`; else any review → `CONDITIONAL`; else `ACCEPTABLE`.
A human may override `UNACCEPTABLE` only with a reason of at least 20 characters,
which is stored on the decision row and printed in the evidence pack.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Liveness. |
| `GET` | `/` | The workbench UI. |
| `GET` | `/v1/policy` | The active policy, as data. |
| `POST` | `/v1/agents` | Upsert an agent spec; writes a `current` snapshot. Returns `agent_id` and digest. |
| `GET` | `/v1/agents` | List registered agents. |
| `POST` | `/v1/agents/{agent_id}/approve` | Freeze the current spec as the `approved` snapshot. |
| `POST` | `/v1/agents/{agent_id}/traces` | Append redacted tool-call traces. |
| `POST` | `/v1/assess` | Assess an agent in a context. Stores and returns the assessment. |
| `GET` | `/v1/queue` | Latest assessment per agent, newest first. |
| `POST` | `/v1/decisions` | Record `accept`, `reject` or `override` (reason required). |
| `GET` | `/v1/evidence/{assessment_id}` | The CISO evidence pack: JSON plus `evidence_markdown`. |
| `GET` | `/v1/audit/{agent_id}` | Full history: snapshots, trace summary, assessments, decisions. |

## Repository layout

```
project-aegis/
  app.py            FastAPI routes and the evidence-pack renderer
  db.py             SQLite persistence (stdlib sqlite3 only)
  schemas.py        Request/response models
  policy.py         DEFAULT_POLICY as data + check_policy()
  assess.py         run_assess(): inventory + drift + policy -> decision, score
  inventory.py      Spec loading, validation, summarising, bridge detection
  hashutil.py       Canonical spec, SHA-256 digest, spec diffing
  seed.py           Idempotent fixture loader
  eval_runner.py    Offline eval suite (5 fixture cases + 12 synthetic)
  fixtures/         Synthetic agents and traces
  samples/          Eval case definitions
  templates/, static/   One page, one stylesheet
  tests/            pytest suite
```

`hashutil.py`, `inventory.py`, `policy.py` and `assess.py` do no I/O at all — the
risk logic is testable and auditable without a server or a database.

## Out of scope (deliberately)

- Live scanning of the public internet
- Executing or connecting to third-party MCP servers
- Ollama, OpenAI, Groq, or any LLM
- NHS, FHIR, e-RS
- Real SSO, CIS2, or SIEM products
- User accounts and authentication
- Docker, paid CI, cloud deployment
- Automatic blocking of production agents
- Defence systems

## Next contract phase — not built here

The following are funded from a contract and must **not** be built in this
repository:

- Department pilot deployment and multi-team tenancy
- SSO
- SIEM sink for findings and drift alerts

## Licence and data

All fixtures, traces and policies in this repository are synthetic and were
written for this demonstrator. No real organisation, system, secret or personal
data is included.
