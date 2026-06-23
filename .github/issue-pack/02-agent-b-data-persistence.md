## Objective

Introduce a normalized SQLite persistence layer for cycles, events, analyses, actions, KnowledgeState, and ChangeSet artifacts.

## Scope

1. Define schema with migration/bootstrap path.
2. Implement repository/data-access methods.
3. Add idempotent insert and dedupe-friendly keys.
4. Support state projection reads for compare logic.

## Deliverables

1. `schema.sql` and migration/bootstrap support.
2. Repository layer with typed operations.
3. Tests for persistence and dedupe behavior.
4. Persistence support for KnowledgeState and ChangeSet entities.

## Acceptance Criteria

1. Runtime can operate with DB-backed state only.
2. Cycle and event records are persisted each run.
3. Failure statuses and latencies can be queried.
4. Compare step can load current KnowledgeState and persist ChangeSet outputs every cycle.

## Dependencies

1. Coordinate runtime integration points with Agent A.
2. Provide action persistence contracts to Agent D.

## References

1. `IMPLEMENTATION_PLAN.md`
2. `CONTRACT_V1.md`
3. `AGENT_GUIDELINES.md`
