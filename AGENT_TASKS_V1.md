# Agent Tasks V1

This is the execution checklist extracted from CONTRACT_V1.

## Agent A: Runtime Orchestration

- [ ] Enforce fixed stage order: ingest -> compare -> act -> persist.
- [ ] Wire source, analysis, policy, and sink registries into runtime startup.
- [ ] Emit per-stage outcomes each cycle.
- [ ] Preserve CLI compatibility with existing flags.
- [ ] Add orchestration regression tests.

## Agent B: Persistence and State

- [ ] Implement schema for envelopes, changesets, decisions, receipts, and knowledge state.
- [ ] Implement repository contract methods for load/save.
- [ ] Add idempotent constraints for envelope and decision writes.
- [ ] Persist cycle statuses and error classes.
- [ ] Add persistence tests for dedupe and state projection behavior.

## Agent C: Analysis and Compare Inputs

- [ ] Implement analysis provider contract with structured output.
- [ ] Validate analysis response schema and classify invalid outputs.
- [ ] Emit confidence and reason codes for compare/policy.
- [ ] Add contract tests for valid/partial/invalid responses.
- [ ] Document provider fallback behavior.

## Agent D: Policy and Actions

- [ ] Implement policy evaluation from changeset + knowledge state.
- [ ] Implement suppression and escalation rules.
- [ ] Generate idempotent action decisions.
- [ ] Implement sink dispatch for at least one sink type.
- [ ] Add tests for suppression, escalation, and resolution actions.

## Agent E: Operability and Diagnostics

- [ ] Add structured telemetry for each stage.
- [ ] Add health output for stage timings and cycle status.
- [ ] Add action delivery diagnostics and retry visibility.
- [ ] Extend scripts for health and replay diagnostics.
- [ ] Update operations docs.

## Agent F: Test and CI Quality Gates

- [ ] Build contract tests for schemas and interfaces.
- [ ] Build multi-cycle loop tests.
- [ ] Build compatibility tests for major-version rejection.
- [ ] Build replay tests for convergence and resolution behavior.
- [ ] Add CI required checks for contract/loop/compatibility suites.

## Shared Integration Milestones

- [ ] M0: Contract and schema freeze.
- [ ] M1: One-source thin slice end-to-end.
- [ ] M2: Multi-source compare-and-act behavior.
- [ ] M3: Replay-driven convergence and resolution.
