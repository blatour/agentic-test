# Agent Execution Waves

This file defines ordered kickoff waves aligned to CONTRACT_V1.

## Wave 1 (Start Now)

1. Issue #8 - Phase 0: Contracts and Registries Guardrails
2. Issue #2 - Agent A: Core Runtime Refactor (skeleton/orchestration wiring only)
3. Issue #3 - Agent B: Data and Persistence (schema + repository skeleton)
4. Issue #7 - Agent F: Test and CI Quality Gates (contract and loop harness skeleton)

Wave 1 objective:

- Reach end-to-end thin slice readiness with contract-compliant scaffolding and tests.

## Wave 2 (After Wave 1 Contract Freeze)

1. Issue #4 - Agent C: Analysis Contract and Model Gateway
2. Issue #5 - Agent D: Policy and Notification Engine

Wave 2 objective:

- Produce meaningful compare-and-act behavior with structured analysis and policy decisions.

## Wave 3 (After Wave 2 Integration)

1. Issue #6 - Agent E: Operability and Deployment

Wave 3 objective:

- Harden run operations, observability, replay diagnostics, and deployment confidence.

## Completion Gate

Do not start a later wave until the prior wave has:

1. Contract-consistent artifacts merged.
2. Required tests passing in CI.
3. No unresolved blocking dependencies in issue comments.
