## Objective

Establish loop contracts and registry guardrails before deeper feature work so extensibility remains additive and loop behavior is explicit.

## Scope

1. Define canonical cycle contract: ingest, compare, act, persist.
2. Define KnowledgeState and ChangeSet contracts.
2. Define plugin interfaces for source, analysis provider, policy, and sink adapters.
3. Implement registry composition for runtime discovery and wiring.
4. Add compatibility test harness and fail-fast behavior for incompatible major versions.

## Deliverables

1. Contract specification docs and code-level interface definitions.
2. Registry modules wired into runtime bootstrap.
3. Compatibility test suite for schema and plugin versions.
4. ADR documenting versioning and deprecation policy.

## Acceptance Criteria

1. New source onboarding requires adapter + registration + tests only.
2. New sink onboarding requires adapter + registration + config only.
3. Runtime rejects incompatible major versions with explicit error category.
4. Core orchestration files remain unchanged for one example new source and one example new sink.
5. One end-to-end scenario produces a persisted ChangeSet and resulting action candidate.

## Dependencies

1. Should complete before major delivery from Agent C and Agent D.
2. Agent A and Agent B should co-own initial integration.

## References

1. IMPLEMENTATION_PLAN.md
2. CONTRACT_V1.md
3. AGENT_GUIDELINES.md
