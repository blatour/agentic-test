<<<<<<< HEAD
# Contract V1 — Frozen Specification

**Status:** Frozen  
**Version:** 1.0  
**Date:** 2026-06-23

This document defines the canonical V1 contracts for the ambient agent runtime.
All adapters, plugins, and registries implemented against this specification must
declare `plugin_major_version = 1`. The runtime rejects any component that declares
a different major version with an explicit `IncompatibleVersionError`.

---

## 1. Cycle Contract

The canonical agent cycle runs four ordered phases:

| Phase     | Responsibility                                        |
|-----------|-------------------------------------------------------|
| `ingest`  | Source adapters fetch raw events from external feeds. |
| `compare` | Analysis provider diffs current ingest against stored KnowledgeState. |
| `act`     | Policy adapters evaluate the ChangeSet and produce action candidates. |
| `persist` | Sink adapters write the ChangeSet and action candidates to storage.    |

Code reference: `src/ambient_agent/contracts/cycle.py`

---

## 2. KnowledgeState Contract

`KnowledgeState` is the normalized snapshot of what the agent knew at the end of
the previous cycle. It is read at the start of `compare` and written at the end of
`persist`.

Required fields:

| Field           | Type              | Description                                     |
|-----------------|-------------------|-------------------------------------------------|
| `state_id`      | `str`             | Deterministic or UUID identifier for this snapshot. |
| `cycle_id`      | `str`             | Cycle that produced this snapshot.              |
| `schema_version`| `int`             | Must equal `CONTRACT_MAJOR_VERSION` (1).        |
| `sources`       | `dict[str, Any]`  | Per-source latest event payload by source name. |
| `last_updated`  | `str \| None`     | ISO-8601 timestamp of the last update.          |

Code reference: `src/ambient_agent/contracts/knowledge_state.py`

---

## 3. ChangeSet Contract

`ChangeSet` carries all detected differences between consecutive `KnowledgeState`
snapshots. It is produced by `compare` and consumed by `act` and `persist`.

Required fields for `ChangeSet`:

| Field           | Type                | Description                                   |
|-----------------|---------------------|-----------------------------------------------|
| `changeset_id`  | `str`               | Unique identifier for this changeset.         |
| `cycle_id`      | `str`               | Owning cycle identifier.                      |
| `schema_version`| `int`               | Must equal `CONTRACT_MAJOR_VERSION` (1).      |
| `changes`       | `list[ChangeEntry]` | Ordered list of individual change entries.    |
| `severity`      | `str`               | Aggregate severity: `low`, `medium`, `high`, `critical`. |

Required fields for `ChangeEntry`:

| Field     | Type           | Description                                       |
|-----------|----------------|---------------------------------------------------|
| `source`  | `str`          | Source adapter name that produced the change.     |
| `kind`    | `str`          | Change kind: `new`, `updated`, or `removed`.      |
| `payload` | `dict[str, Any]` | Raw event data from the source adapter.         |

Code reference: `src/ambient_agent/contracts/changeset.py`

---

## 4. Plugin Interfaces

All plugin types inherit from `PluginBase` and must declare `plugin_major_version`.

### 4.1 SourceAdapter

Fetches raw events from an external feed.

```
name: str                         (read-only property)
plugin_major_version: int         (defaults to CONTRACT_MAJOR_VERSION)
fetch_events() -> list[dict]
```

### 4.2 AnalysisProvider

Produces a new `KnowledgeState` from a batch of raw events.

```
name: str
plugin_major_version: int
analyze(events: list[dict]) -> KnowledgeState
```

### 4.3 PolicyAdapter

Evaluates a `ChangeSet` and returns zero or more action candidates.

```
name: str
plugin_major_version: int
evaluate(changeset: ChangeSet) -> list[dict]
```

### 4.4 SinkAdapter

Persists a `ChangeSet` and its resulting action candidates.

```
name: str
plugin_major_version: int
persist(changeset: ChangeSet, action_candidates: list[dict]) -> None
```

Code reference: `src/ambient_agent/contracts/interfaces.py`

---

## 5. Registry Contract

`PluginRegistry` is the single composition root for all adapter types.
It validates `plugin_major_version` on every registration call and raises
`IncompatibleVersionError` immediately for any mismatch.

Registration methods:

```
register_source(adapter: SourceAdapter) -> None
register_analysis_provider(provider: AnalysisProvider) -> None
register_policy(policy: PolicyAdapter) -> None
register_sink(sink: SinkAdapter) -> None
```

Retrieval methods:

```
get_sources() -> dict[str, SourceAdapter]
get_analysis_providers() -> dict[str, AnalysisProvider]
get_policies() -> dict[str, PolicyAdapter]
get_sinks() -> dict[str, SinkAdapter]
```

Code reference: `src/ambient_agent/registry/registry.py`

---

## 6. Version and Compatibility

| Constant                 | Value | Meaning                                   |
|--------------------------|-------|-------------------------------------------|
| `CONTRACT_MAJOR_VERSION` | `1`   | Breaking change boundary.                 |
| `CONTRACT_MINOR_VERSION` | `0`   | Non-breaking additions allowed freely.    |

**Rule:** A plugin with `plugin_major_version != CONTRACT_MAJOR_VERSION` is rejected
at registration time with `IncompatibleVersionError` (error category:
`incompatible_major_version`). Minor version differences are always compatible.

Code reference: `src/ambient_agent/contracts/versions.py`

---

## 7. Onboarding Checklist

### Adding a new source

1. Create an adapter class that inherits `SourceAdapter`.
2. Implement `name` and `fetch_events()`.
3. Register with `registry.register_source(MyAdapter())`.
4. Add unit tests for `fetch_events()` and one contract test for registration.

### Adding a new sink

1. Create an adapter class that inherits `SinkAdapter`.
2. Implement `name` and `persist()`.
3. Register with `registry.register_sink(MySink())`.
4. Add config entry (source URL, credentials path, etc.).

Core orchestration files (`runtime.py`, `cycle.py`) remain **unchanged** when
adding a new source or sink.

---

## 8. References

- `IMPLEMENTATION_PLAN.md` — delivery phases and module ownership
- `AGENT_GUIDELINES.md` — coding standards and contract freeze policy
- `docs/adr/ADR-001-versioning-deprecation-policy.md` — versioning ADR
- `src/ambient_agent/contracts/` — code-level interface definitions
- `src/ambient_agent/registry/` — registry and bootstrap
=======
# Contract V1

This document defines the stable interfaces and delivery boundaries for the loop:

1. Ingest
2. Compare
3. Act
4. Persist

These contracts are the coordination boundary for parallel agent work. New sources, message types, and sinks must be additive against these contracts.

## Why This Contract Exists

1. Keep the runtime open for extension and closed for core flow rewrites.
2. Allow Agent A-F to work in parallel with low conflict.
3. Ensure each cycle has auditable, testable, and replayable outputs.

## Contract Scope

This contract covers:

1. Canonical loop stage ordering and stage inputs/outputs.
2. Artifact shape and behavior semantics.
3. Plugin interface behavior.
4. Versioning and compatibility rules.
5. Cross-agent acceptance tests.
6. Discrete implementation tasks per agent.

This contract does not prescribe:

1. Exact database engine beyond compatibility rules.
2. Specific model vendor.
3. Specific sink provider (email, webhook, ticketing).

## Canonical Loop Invariants

Every runtime cycle must satisfy all invariants below.

1. Stage order is fixed: Ingest -> Compare -> Act -> Persist.
2. Raw source payload is persisted before decision execution.
3. Compare stage runs against current KnowledgeState, not raw source text.
4. Policy and sink dispatch run on ChangeSet and ActionDecision artifacts only.
5. Every cycle emits explicit outcomes:
- Envelope batch outcome
- ChangeSet outcome
- ActionDecision outcome(s)
- Persist outcome
6. Any stage failure is classified and persisted with a typed status.

## Core Artifacts

All core artifacts are required for Contract V1.

### CanonicalEnvelope

Represents normalized input messages across all sources.

Required fields:

- `envelope_id`
- `envelope_type`
- `envelope_version`
- `tenant_id`
- `correlation_id`
- `causation_id`
- `occurred_at`
- `producer`
- `payload_schema_version`
- `payload`

Behavior semantics:

1. `envelope_id` is globally unique and idempotent for the event.
2. `tenant_id` is mandatory for retrieval and action isolation.
3. `payload` contains normalized fields, not source-native raw format.
4. `envelope_version` must be major-compatible with runtime.

### KnowledgeState

Represents what the system currently believes.

Required fields:

- `state_id`
- `tenant_id`
- `as_of`
- `open_items`
- `active_facts`
- `suppression_windows`
- `risk_score`

Behavior semantics:

1. Represents current belief snapshot or projection at cycle start/end.
2. Must be queryable by tenant and time anchor.
3. Open items must be traceable to facts and prior ChangeSets.

### ChangeSet

Represents the difference between newly ingested data and current KnowledgeState.

Required fields:

- `changeset_id`
- `tenant_id`
- `generated_at`
- `input_envelope_ids`
- `new_facts`
- `changed_facts`
- `resolved_facts`
- `risk_delta`
- `confidence_delta`
- `reason_codes`

Behavior semantics:

1. Must explicitly capture both change and no-change outcomes.
2. `reason_codes` explain why change classification occurred.
3. Must reference the exact input envelopes used for compare.

### ActionDecision

Represents actions produced by policy evaluation.

Required fields:

- `decision_id`
- `changeset_id`
- `policy_id`
- `action_type`
- `priority`
- `should_execute`
- `reason`
- `idempotency_key`
- `metadata`

Behavior semantics:

1. `idempotency_key` must prevent duplicate external side effects.
2. `should_execute=false` decisions are still persisted for auditability.
3. `metadata` may include routing hints and execution context.

### DeliveryReceipt

Represents sink execution result.

Required fields:

- `sink_type`
- `status`
- `external_reference`
- `metadata`

Behavior semantics:

1. Every executed ActionDecision should have at least one receipt.
2. Failed delivery attempts are persisted with classified status.

## Stage I/O Contract

1. Ingest
- Input: source configuration + source adapter registry
- Output: list of CanonicalEnvelope + raw payload persistence entries

2. Compare
- Input: list of CanonicalEnvelope + current KnowledgeState
- Output: one ChangeSet for the cycle scope

3. Act
- Input: ChangeSet + current KnowledgeState + policy registry + sink registry
- Output: list of ActionDecision + list of DeliveryReceipt

4. Persist
- Input: all cycle artifacts and outcomes
- Output: persisted state and cycle status record

## Plugin Interfaces

### SourceAdapter

- Input: source config
- Output: list of `CanonicalEnvelope`

Rules:

1. Must not call policy or sink logic.
2. Must provide stable source-specific dedupe input.
3. Must classify fetch failures into typed error categories.

### AnalysisProvider

- Input: `CanonicalEnvelope` and analysis policy
- Output: structured analysis payload with confidence and reason codes

Rules:

1. Must return schema-valid payload or explicit invalid-response error.
2. Must include confidence and reason codes consumable by compare/policy.

### CompareEngine

- Input: list of `CanonicalEnvelope`, current `KnowledgeState`
- Output: `ChangeSet`

Rules:

1. Must be deterministic for the same input set and baseline state.
2. Must support no-change outcomes with explicit reason codes.
3. Must never execute external side effects.

### PolicyEngine

- Input: `ChangeSet`, current `KnowledgeState`
- Output: list of `ActionDecision`

Rules:

1. Must not depend on source-specific payload shape.
2. Must preserve idempotency key strategy.
3. Must support suppression and escalation semantics.

### SinkAdapter

- Input: `ActionDecision`
- Output: delivery receipt with status and external reference

Rules:

1. Must be idempotent by `idempotency_key`.
2. Must never mutate core loop artifacts.
3. Must return typed receipt outcomes.

## Error Taxonomy (V1)

Minimum error classes that must be emitted and persisted:

1. `source.fetch_error`
2. `source.parse_error`
3. `compare.state_load_error`
4. `analysis.invalid_response`
5. `analysis.provider_timeout`
6. `policy.evaluation_error`
7. `sink.dispatch_error`
8. `persist.write_error`

## Versioning Policy

1. `v1.x`: backward-compatible field additions only.
2. `v2.0`: breaking changes require migration notes and compatibility tests.
3. Unknown major versions must fail fast with compatibility error classification.
4. Minor version additions must not break existing agent implementations.

## Required Cross-Agent Tests

1. Contract tests validating envelope, knowledge state, changeset, and action shapes.
2. Loop tests validating ingest -> compare -> act -> persist over 3+ cycles.
3. Compatibility tests for unknown major version handling.
4. Idempotency tests for repeated action dispatch.
5. Replay tests that confirm state convergence and open-item resolution.

## Discrete Tasks By Agent

Each agent should execute these tasks in sequence. Tasks are intentionally small and merge-friendly.

### Agent A: Runtime Orchestration

1. Implement cycle orchestrator that enforces stage order invariants.
2. Wire adapter registries into runtime startup.
3. Ensure every cycle emits explicit stage outcomes.
4. Preserve existing CLI compatibility while delegating to package runtime.
5. Add loop orchestration regression tests.

Definition of done for Agent A:

1. Runtime loop executes all four stages with typed artifacts.
2. No source-specific branching exists in orchestrator.

### Agent B: Persistence and State

1. Implement persistence schema for envelopes, changesets, decisions, receipts, and knowledge state.
2. Implement repository contract methods for load/save semantics.
3. Add idempotent write constraints for envelope and decision artifacts.
4. Add cycle status persistence and error classification persistence.
5. Add tests for state load/save and dedupe behavior.

Definition of done for Agent B:

1. Compare stage can load current KnowledgeState deterministically.
2. Persist stage stores all cycle artifacts with traceability.

### Agent C: Analysis and Compare Inputs

1. Implement analysis provider contract with structured outputs.
2. Validate analysis payloads and classify invalid responses.
3. Produce confidence and reason codes consumable by compare/policy.
4. Add contract tests for valid, partial, and invalid analysis responses.
5. Document provider behavior and fallback policy.

Definition of done for Agent C:

1. Compare and policy can consume analysis outputs without custom parsing per source.

### Agent D: Policy and Actions

1. Implement policy engine on ChangeSet + KnowledgeState inputs.
2. Add suppression and escalation logic with explicit reason codes.
3. Implement action generation with idempotency key strategy.
4. Integrate sink dispatch flow for at least one sink type.
5. Add tests for duplicate suppression, escalation, and resolution actions.

Definition of done for Agent D:

1. At least one open item can be resolved in a later cycle via policy output.

### Agent E: Operability and Diagnostics

1. Add structured telemetry for each loop stage.
2. Add health output for cycle success/failure and stage timings.
3. Add diagnostics for action delivery outcomes and retry behavior.
4. Extend operational scripts for loop health and replay visibility.
5. Add documentation for operations workflow.

Definition of done for Agent E:

1. Operators can identify where and why loop failures occur per stage.

### Agent F: Test and CI Quality Gates

1. Build contract test harness for JSON schemas and interfaces.
2. Build loop scenario tests across 3+ cycles.
3. Build compatibility tests for major version rejection.
4. Build replay tests for convergence and resolution behavior.
5. Integrate required checks into CI workflow.

Definition of done for Agent F:

1. CI blocks merge when loop contract or compatibility guarantees regress.

## Cross-Agent Integration Milestones

1. Milestone M0: Contract freeze
- Contract artifacts and schema files approved.

2. Milestone M1: End-to-end thin slice
- One source, one compare path, one policy, one sink, full persistence.

3. Milestone M2: Multi-source behavior
- At least two sources and meaningful ChangeSet outcomes.

4. Milestone M3: Replay and convergence
- Multi-cycle replay demonstrates open-item resolution and stable behavior.

## Merge Readiness Checklist

A change is merge-ready only if all apply:

1. Contract-compliant types/interfaces are used.
2. No orchestration stage-order violation.
3. Tests for changed behavior are included.
4. Documentation references remain current.
5. Issue scope and acceptance criteria are updated if needed.

>>>>>>> origin/main
