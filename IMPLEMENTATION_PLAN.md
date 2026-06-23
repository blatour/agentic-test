# Enterprise Implementation Plan

This document turns the current ambient agent prototype into a realistic enterprise-style implementation roadmap that can be executed in parallel by multiple agents.

## Goals

1. Evolve from a single-process demo to a reliable, observable, policy-driven system.
2. Keep delivery incremental so each merge to main adds real capability.
3. Split work so multiple agents can contribute in parallel with low merge conflict risk.

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

## Target Architecture (Incremental)

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

4. Persistence Layer
- Start with SQLite for local realism.
- Design schema and data access to be Postgres-compatible.

5. Operability Layer
- Structured logs, metrics, health checks, and startup diagnostics.
- Source-specific failure taxonomy and retry/backoff telemetry.

## Delivery Phases

## Phase 1: Foundation Hardening (1-2 weeks)

Outcomes:

- Modular package structure under `src/ambient_agent/`.
- SQLite-backed persistence with migrations.
- Structured analysis schema and validation.
- Expanded failure classification and latency recording.

Acceptance criteria:

- Agent can run end-to-end with SQLite only (no JSON state required).
- Every cycle persists source checks, errors, and timings.
- Analysis output is validated against schema before save.
- Existing `--dry-run` mode continues to work.

## Phase 2: Reactive Runtime (1-2 weeks)

Outcomes:

- Policy engine for escalation and duplicate suppression windows.
- Notification adapters (start with console + webhook sink).
- Source health model with adaptive backoff.

Acceptance criteria:

- At least one policy can trigger a notification action.
- Repeated duplicate events are suppressed within configured windows.
- Source failures increase backoff according to config.

## Phase 3: Enterprise Readiness (2+ weeks)

Outcomes:

- Health/status API and summarized operational dashboard output.
- Replay test mode for historical fixture ingestion.
- CI quality gates (unit, contract, lint, smoke).
- Security and governance basics (secrets policy, audit fields).

Acceptance criteria:

- CI gates run on pull requests.
- Replay mode can run deterministic fixture scenarios.
- Health endpoint exposes cycle, source, and model readiness.

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

## Shared Contracts to Freeze Early

These must be agreed before parallel implementation proceeds:

1. Canonical Event schema.
2. Analysis JSON schema.
3. Cycle status and error taxonomy.
4. Action and notification payload shape.

If these contracts change late, merge conflicts and rework will spike.

## Proposed Repository Layout (Target)

```text
src/
  ambient_agent/
    runtime.py
    cli.py
    config.py
    sources/
      base.py
      github.py
      usgs.py
      nasa.py
    analysis/
      gateway.py
      schema.py
      parser.py
    persistence/
      schema.sql
      repository.py
      migrations.py
    policies/
      engine.py
      rules.py
    notifications/
      dispatcher.py
      sinks.py
    observability/
      logging.py
      metrics.py
tests/
  unit/
  contract/
  replay/
```

## Definition of Done for Main Branch

Work is considered done only when all are true:

1. Functionality merged with tests.
2. Podman deploy path still works.
3. Docs updated for run and debug flow.
4. Health output includes failure classification and timings.
5. No regression in dry-run and one-shot modes.

## Milestone Backlog (Check-In Ready)

M1 - Refactor and SQLite foundation

- [ ] Create `src/ambient_agent/` package and preserve CLI compatibility.
- [ ] Add SQLite schema + repository + migration bootstrap.
- [ ] Store cycles/events/analyses in DB.

M2 - Structured analysis and policy engine

- [ ] Introduce analysis JSON contract and validation.
- [ ] Add policy engine and action creation.
- [ ] Add duplicate suppression and escalation rules.

M3 - Operability and CI

- [ ] Add health command/API and structured logs.
- [ ] Add replay fixtures and fault-injection tests.
- [ ] Add CI workflow with lint, tests, and container smoke run.

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

1. Approve this plan and assign agent owners for A-F.
2. Create six tracking issues aligned to workstreams.
3. Start Phase 1 with shared contract definitions before feature coding.
