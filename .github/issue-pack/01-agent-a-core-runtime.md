## Objective

Refactor the current single-script runtime into a modular package while preserving CLI compatibility and behavior.

## Scope

1. Create package structure under `src/ambient_agent/`.
2. Separate runtime loop, source orchestration, analysis calls, and persistence interfaces.
3. Keep existing CLI flags working.

## Deliverables

1. Modular runtime entry points.
2. Backward-compatible CLI adapter.
3. Regression tests for cycle execution paths.

## Acceptance Criteria

1. Existing run modes still work (`--dry-run`, `--once`, `--max-cycles`).
2. Runtime behavior remains equivalent for baseline scenarios.
3. Tests pass and docs are updated if commands change.

## Dependencies

1. None for scaffolding.
2. Coordinate interfaces with Agent B and Agent C.

## References

1. `IMPLEMENTATION_PLAN.md`
2. `AGENT_GUIDELINES.md`
