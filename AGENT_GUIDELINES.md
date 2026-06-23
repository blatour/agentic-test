# Agent Guidelines

This guide defines how all implementation agents work in this repository.

## Purpose

Ensure multiple agents can deliver in parallel without stepping on each other, while keeping main stable and deployable.

## Source of Truth

1. Architecture and milestones: `IMPLEMENTATION_PLAN.md`
2. Runtime contracts and schemas: `CONTRACT_V1.md`
3. Issue definitions and dependencies: `ISSUE_PACK.md`
4. Runtime behavior baseline: `README.md`

When conflicts arise, follow this precedence order:

1. `IMPLEMENTATION_PLAN.md`
2. Accepted ADRs
3. Existing code behavior

## Branching and PR Rules

1. One branch per issue.
2. One concern per PR.
3. Keep PRs small (target 200-500 lines).
4. Include tests in the same PR when behavior changes.
5. Do not mix refactor and feature logic unless required.

Branch naming format:

- `agent-a/<short-topic>`
- `agent-b/<short-topic>`
- `agent-c/<short-topic>`
- `agent-d/<short-topic>`
- `agent-e/<short-topic>`
- `agent-f/<short-topic>`

## Module Ownership

1. Agent A owns runtime modularization and CLI compatibility.
2. Agent B owns persistence schema and repository layer.
3. Agent C owns analysis schema and model gateway.
4. Agent D owns policy engine and notification dispatch.
5. Agent E owns observability and deployment automation extensions.
6. Agent F owns tests, replay fixtures, and CI workflows.

Cross-module changes require a short coordination note in the issue thread before implementation.

## Contract Freeze Policy

Before feature coding beyond scaffolding, freeze these contracts:

1. Canonical event schema.
2. Analysis response schema.
3. KnowledgeState model.
4. ChangeSet model.
5. Error taxonomy and cycle statuses.
6. Action payload schema.

Contract changes after freeze require:

1. ADR entry.
2. Changelog note in affected issues.
3. Follow-up updates to dependent tests.

## Coding Standards

1. Keep backward compatibility for existing CLI flags until formally deprecated.
2. Favor pure functions and explicit data contracts between modules.
3. Use structured logs (event name, source, cycle_id, status, latency_ms).
4. Prefer deterministic IDs and idempotent persistence operations.
5. Handle source and model failures explicitly with typed categories.
6. Do not add source-specific branching logic in orchestration code.
7. New sources and sinks must integrate via registry and plugin interfaces only.
8. New message types must be introduced through schema registration, not pipeline changes.
9. Compare and policy logic must operate on ChangeSet artifacts, not raw source payloads.

## Extensibility Guardrails

A pull request that adds a new source, sink, or message type is valid only if all are true:

1. Core pipeline stage order is unchanged.
2. No switch or if/elif chain is added to route by source name in runtime orchestration.
3. Adapter is discoverable through registry wiring.
4. Contract and compatibility tests are added or updated.
5. Configuration enables rollout without mandatory code edits in orchestration modules.

If a contribution cannot meet these, it requires architecture review before merge.

## Test Requirements

Minimum expectations per change set:

1. Unit tests for modified business logic.
2. Contract tests for source adapter payload normalization.
3. Failure-path tests for retries, parsing errors, and model timeouts where relevant.
4. Compatibility tests for schema and plugin interface version behavior when contracts change.
5. Loop tests proving ingest -> compare -> act -> persist over multiple cycles.

Definition of merge readiness:

1. Tests pass locally and in CI.
2. Docs updated when behavior changes.
3. No known regression in dry-run and one-shot modes.

## Coordination Cadence

1. Daily async update in issue comments:
- completed
- in progress
- blockers

2. Weekly architecture sync:
- contract changes
- dependency updates
- merge conflict hotspots

## Escalation Path

If blocked for more than one business day:

1. Post blocker details in issue comments.
2. Tag affected agent owners.
3. Propose one fallback path and one preferred path.

## Anti-Patterns to Avoid

1. Long-lived branches with large unreviewed diffs.
2. Silent schema changes without ADR and issue update.
3. Reformat-only churn across unrelated files.
4. Tight coupling of policy logic to source adapter code.
5. Swallowing exceptions without classification or telemetry.
