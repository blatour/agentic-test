# Enterprise Implementation Plan

This document turns the current ambient agent prototype into a realistic enterprise-style implementation roadmap that can be executed in parallel by multiple agents.

## Goals

1. Evolve from a single-process demo to a reliable, observable, policy-driven system.
2. Keep delivery incremental so each merge to main adds real capability.
3. Split work so multiple agents can contribute in parallel with low merge conflict risk.
4. Make new sources, message types, and action sinks additive changes with no core orchestration rewrites.
5. Maximize test value by proving a meaningful closed-loop behavior, not just source polling and summarization.

## Current Baseline

The current repo has these strengths:

- Reliable local loop for periodic polling and summary output.
- Podman automation for build, setup, run, and logs.
- Persistent state and history files that survive restarts.

Known depth gaps:

- Tight coupling in one runtime script (ingest, model call, state, and reporting).
- Flat JSON state rather than normalized event and cycle history.
- No queueing, policy engine, notification pipeline, or health API.
- Minimal test harness around source adapters and failure modes.

## Loop-First Architecture Principles

This project optimizes for a useful closed loop:

1. Ingest data from multiple sources.
2. Compare with what we already know.
3. Decide and execute actions.
4. Persist updated state so the next cycle learns.

If a change does not improve one of those four steps, it is lower priority.

## Enterprise Architecture Principles

1. Open-closed runtime core
- Core pipeline stages are stable and do not branch on source-specific logic.
- New capabilities are added through plugins and configuration, not core flow edits.

2. Contract-first boundaries (pragmatic)
- Every stage communicates through versioned contracts.
- Runtime rejects unknown major versions and routes incompatible payloads to quarantine.
- Versioning should be lightweight early: stabilize loop semantics first, then expand formal compatibility controls.

3. Control plane over code edits
- Source enablement, polling behavior, suppression windows, and routing rules are configuration-driven.
- Most operational changes should require config updates, not deploys.

4. Idempotent and replayable processing
- All ingestion and actions are idempotent by design.
- Replay mode can safely reprocess historical data without side effects.

5. Backward compatibility by default
- Contract changes follow semantic versioning and compatibility windows.
- Deprecation policy is explicit and time-bounded.

## Target Architecture (Incremental)

### Canonical Runtime Loop (Source of Truth)

Each cycle must execute this sequence:

1. Ingest
- Pull or receive payloads from enabled sources.
- Persist raw payloads immediately for audit and replay.

2. Compare
- Normalize payloads to canonical events.
- Compare against current knowledge state (dedupe, trend deltas, open questions, unresolved actions).
- Produce a ChangeSet object that explicitly states what changed and why.

3. Act
- Evaluate policies against the ChangeSet.
- Produce zero or more actions (notify, open task, raise priority, trigger follow-up workflow).
- Execute through sink adapters with idempotency keys.

4. Persist and Learn
- Persist canonical events, ChangeSet, decisions, action outcomes, and updated knowledge state.
- Update source health and loop telemetry.
- Feed open questions into next-cycle prioritization.

### Stable Pipeline Invariant

The orchestration flow is fixed:

1. Receive source message.
2. Normalize to canonical envelope.
3. Build ChangeSet by comparing to known state.
4. Persist raw and canonical forms.
5. Analyze significance (model or deterministic evaluator).
6. Evaluate policy and generate actions.
7. Emit actions to sinks.
8. Persist outcomes and updated knowledge state.
9. Record telemetry and state transitions.

New sources or message classes must plug into this invariant without changing stage order.

### Extension Contracts

1. SourceAdapter plugin contract
- Input: source-specific client config.
- Output: list of CanonicalEvent envelopes.
- Required metadata: source_id, source_event_id, occurred_at, tenant_id, correlation_id, schema_version.

2. MessageType mapper contract
- Maps raw payloads to canonical message families.
- Supports independent schema versioning per message family.

3. AnalysisProvider contract
- Accepts canonical envelope and analysis policy.
- Returns validated AnalysisResult envelope.

4. PolicyPlugin contract
- Stateless evaluation preferred; state access only via repository interface.
- Emits ActionDecision objects with deterministic reasons.

5. SinkAdapter contract
- Consumes ActionDecision and performs delivery.
- Must be idempotent and return delivery receipt metadata.

### Canonical Envelope Model

All inter-stage payloads share a common envelope:

- envelope_id
- envelope_type
- envelope_version
- tenant_id
- correlation_id
- causation_id
- occurred_at
- producer
- payload
- payload_schema_version

This allows adding message families without altering transport or storage primitives.

### ChangeSet and Knowledge State Model

To make the loop valuable, add two first-class artifacts:

1. KnowledgeState
- What the system currently believes.
- Includes active facts, open questions, unresolved actions, trend baselines, and suppression windows.

2. ChangeSet
- The computed difference between new canonical events and current KnowledgeState.
- Includes: `new_facts`, `changed_facts`, `resolved_facts`, `risk_delta`, `confidence_delta`, `reason_codes`.

Policies and action generation run on ChangeSet, not raw events.

### Registry-Driven Discovery

Use registries for runtime composition:

1. Source registry: maps source type to SourceAdapter.
2. Message schema registry: maps message family/version to validator.
3. Policy registry: maps policy IDs to evaluators.
4. Sink registry: maps sink type to dispatch adapter.

Adding a new source should be:

1. Implement SourceAdapter.
2. Register adapter.
3. Add source config row.
4. Add contract tests.

No orchestration edits required.

### Core Components

1. Ingestion Layer
- One adapter per source (GitHub, USGS, NASA, plus future sources).
- Canonical event contract before persistence.

2. Analysis Layer
- Structured LLM output contract (JSON schema, not freeform markdown).
- Model gateway abstraction (Ollama now, cloud providers later).

3. Decision Layer
- Policy engine for escalation, suppression, retry, and follow-up actions.
- Action records for notifications or internal tasks.
- Policy pack loading model so new policies can ship independently from core runtime.

4. Persistence Layer
- Start with SQLite for local realism.
- Design schema and data access to be Postgres-compatible.
- Store raw payload, canonical envelope, and decision artifacts separately for schema evolution.
- Store KnowledgeState snapshots or projections so compare logic is explicit and testable.

5. Operability Layer
- Structured logs, metrics, health checks, and startup diagnostics.
- Source-specific failure taxonomy and retry/backoff telemetry.
- Contract-version metrics and plugin health metrics per adapter.

### Data Platform Shape (Postgres-Compatible)

Recommended logical tables:

1. envelopes
- canonical envelope metadata and payload reference.

2. raw_messages
- immutable source payload archive and checksum.

3. analyses
- analysis envelope, provider metadata, latency, and validation outcome.

4. knowledge_state
- current state projections used by compare logic.

5. change_sets
- explicit diff artifacts produced each cycle.

6. decisions
- policy decisions, reasons, and versioned policy references.

7. action_deliveries
- sink attempts, idempotency keys, status, and receipt metadata.

8. source_configs
- source enablement, cadence, auth reference, and backoff settings.

9. schema_registry
- active and deprecated schema versions per envelope family.

## Delivery Phases

## Phase 0: Loop Contract and Data Semantics (3-5 days)

Outcomes:

- Canonical cycle contract (Ingest, Compare, Act, Persist).
- ChangeSet and KnowledgeState definitions.
- Plugin contracts for sources, analysis providers, policies, and sinks.
- Minimal registry bootstrapping pattern.

Acceptance criteria:

- Contract test suite validates adapters and ChangeSet generation.
- At least one source and one sink run through registry wiring.
- One end-to-end cycle proves non-trivial compare-and-act behavior.

## Phase 1: Foundation Hardening (1-2 weeks)

Outcomes:

- Modular package structure under `src/ambient_agent/`.
- SQLite-backed persistence with migrations.
- Structured analysis schema and validation.
- Expanded failure classification and latency recording.
- Registry-driven plugin loading for at least one source adapter.
- Compare engine that produces persisted ChangeSet output every cycle.

Acceptance criteria:

- Agent can run end-to-end with SQLite only (no JSON state required).
- Every cycle persists source checks, errors, and timings.
- Analysis output is validated against schema before save.
- Existing `--dry-run` mode continues to work.
- New source onboarding requires no core orchestration file edits.
- At least one action type is triggered from ChangeSet results.

## Phase 2: Reactive Runtime (1-2 weeks)

Outcomes:

- Policy engine for escalation and duplicate suppression windows.
- Notification adapters (start with console + webhook sink).
- Source health model with adaptive backoff.
- Configuration-driven source enable/disable and routing behavior.
- Open-question tracking and risk trend deltas integrated into compare step.

Acceptance criteria:

- At least one policy can trigger a notification action.
- Repeated duplicate events are suppressed within configured windows.
- Source failures increase backoff according to config.
- At least one new sink can be added via adapter and registry only.
- Compare step can resolve previously open items when new evidence arrives.

## Phase 3: Enterprise Readiness (2+ weeks)

Outcomes:

- Health/status API and summarized operational dashboard output.
- Replay test mode for historical fixture ingestion.
- CI quality gates (unit, contract, lint, smoke).
- Security and governance basics (secrets policy, audit fields).
- Multi-tenant guardrails in envelope metadata and policy evaluation context.
- Optional workflow actions (for example code-change proposal generation) behind explicit policy controls.

Acceptance criteria:

- CI gates run on pull requests.
- Replay mode can run deterministic fixture scenarios.
- Health endpoint exposes cycle, source, and model readiness.
- Compatibility dashboard reports schema and plugin version status.
- Replay run demonstrates loop convergence over multiple cycles.

## Parallel Agent Work Allocation

Use these as named workstreams. Each workstream should be delivered as a sequence of small pull requests.

## Agent A: Core Runtime Refactor

Scope:

- Split `samples/ambient_agent.py` into modules:
  - `runtime.py`
  - `sources/`
  - `analysis/`
  - `persistence/`
  - `policies/`
- Preserve CLI behavior and flags during refactor.

Deliverables:

- New package structure and imports.
- Backward-compatible CLI entry point.
- Regression tests for cycle loop behavior.

## Agent B: Data and Persistence

Scope:

- Introduce SQLite schema and migration bootstrap.
- Add repository layer for cycles, events, analyses, and actions.
- Add deterministic IDs and dedupe helpers.

Deliverables:

- `src/ambient_agent/persistence/schema.sql`
- `src/ambient_agent/persistence/repository.py`
- Migration/bootstrap command and tests.

## Agent C: Analysis Contract and Model Gateway

Scope:

- Define strict JSON analysis schema.
- Add model gateway abstraction and structured response parsing.
- Add fallback behavior for invalid model responses.

Deliverables:

- `src/ambient_agent/analysis/schema.py`
- `src/ambient_agent/analysis/gateway.py`
- Contract tests with mock model responses.

## Agent D: Policy and Notification Engine

Scope:

- Build configurable policy evaluation.
- Add action creation and notification dispatch.
- Add duplicate suppression and escalation thresholds.

Deliverables:

- `src/ambient_agent/policies/engine.py`
- `src/ambient_agent/notifications/dispatcher.py`
- Policy tests for severity and suppression rules.

## Agent E: Operability and Deployment

Scope:

- Add structured logging fields and cycle correlation IDs.
- Add metrics and health summary command/API.
- Extend `scripts/podman-ambient.ps1` for health checks and replay runs.

Deliverables:

- `src/ambient_agent/observability/`
- Extended podman script options for diagnostics.
- Runtime docs for operations.

## Agent F: Test and CI Quality Gates

Scope:

- Build unit, contract, and smoke test suites.
- Add replay fixtures and failure injection tests.
- Add CI workflow for lint + test + container smoke run.

Deliverables:

- `tests/unit/`, `tests/contract/`, `tests/replay/`
- CI workflow file under `.github/workflows/`
- Updated developer test commands in docs.

## Pull Request Slicing Strategy

Each agent should create small, composable PRs in this order:

1. Skeleton and interfaces (minimal behavior change).
2. Data model or contract implementation.
3. Runtime integration.
4. Tests and docs updates.

PR size target:

- 200-500 lines preferred.
- Avoid mixed concerns in one PR.
- Core orchestration edits require architecture reviewer sign-off.

## Shared Contracts to Freeze Early

These must be agreed before parallel implementation proceeds:

1. Canonical Event schema.
2. Analysis JSON schema.
3. KnowledgeState model.
4. ChangeSet model.
5. Cycle status and error taxonomy.
6. Action and notification payload shape.
7. Plugin interfaces and registry behavior.
8. Envelope versioning and compatibility rules.

If these contracts change late, merge conflicts and rework will spike.

## Proposed Repository Layout (Target)

```text
src/
  ambient_agent/
    runtime.py
    cli.py
    config.py
    contracts/
      envelopes.py
      schemas.py
      compatibility.py
      changeset.py
      knowledge_state.py
    registries/
      sources.py
      analysis.py
      policies.py
      sinks.py
    sources/
      base.py
      github.py
      usgs.py
      nasa.py
      factory.py
    analysis/
      gateway.py
      schema.py
      parser.py
      providers/
        ollama.py
    persistence/
      schema.sql
      repository.py
      migrations.py
    policies/
      engine.py
      rules.py
      evaluators/
        baseline.py
    notifications/
      dispatcher.py
      sinks.py
      adapters/
        webhook.py
        console.py
    observability/
      logging.py
      metrics.py
      health.py
    compare/
      engine.py
      resolvers.py
tests/
  unit/
  contract/
  replay/
  compatibility/
  loop/
```

## Definition of Done for Main Branch

Work is considered done only when all are true:

1. Functionality merged with tests.
2. Podman deploy path still works.
3. Docs updated for run and debug flow.
4. Health output includes failure classification and timings.
5. No regression in dry-run and one-shot modes.
6. Adding one new source requires only adapter, registration, and tests.
7. Adding one new message type requires schema registration and mapper only.
8. At least one production-like scenario demonstrates meaningful compare-and-act behavior over multiple cycles.

## Milestone Backlog (Check-In Ready)

M0 - Loop semantics and contracts

- [ ] Define canonical cycle contract with KnowledgeState and ChangeSet models.
- [ ] Implement source, policy, analysis, and sink registries.
- [ ] Add loop and contract tests for interface conformance and change semantics.

M1 - Refactor and SQLite foundation

- [ ] Create `src/ambient_agent/` package and preserve CLI compatibility.
- [ ] Add SQLite schema + repository + migration bootstrap.
- [ ] Store cycles/events/analyses in DB.
- [ ] Store raw and canonical payload forms with version metadata.
- [ ] Persist KnowledgeState and ChangeSet for each cycle.

M2 - Structured analysis and policy engine

- [ ] Introduce analysis JSON contract and validation.
- [ ] Add policy engine and action creation.
- [ ] Add duplicate suppression and escalation rules.
- [ ] Add compare resolvers that can open, update, and close tracked items.

M3 - Operability and CI

- [ ] Add health command/API and structured logs.
- [ ] Add replay fixtures and fault-injection tests.
- [ ] Add CI workflow with lint, tests, and container smoke run.
- [ ] Add multi-cycle replay proving stateful loop value and convergence.

## Coordination Cadence

1. Weekly architecture sync (contracts + dependency updates).
2. Daily async status in PR threads by each agent owner.
3. Contract changes require a short ADR note before merge.

## Risks and Mitigations

1. Risk: Over-refactor stalls delivery.
- Mitigation: Keep CLI behavior stable and merge in thin slices.

2. Risk: LLM output drift breaks parsers.
- Mitigation: Enforce schema validation and fallback handling.

3. Risk: Source API instability creates noisy alerts.
- Mitigation: Per-source backoff, suppression windows, and health scoring.

4. Risk: Merge conflicts across parallel agents.
- Mitigation: Freeze contracts first and assign ownership by module boundaries.

## Immediate Next Actions

1. Freeze `CONTRACT_V1.md` and schema files as implementation baseline.
2. Approve this plan and assign agent owners for A-F.
3. Keep issue templates and live issues synced to contract updates.
