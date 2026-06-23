# ADR-001: Versioning and Deprecation Policy

**Status:** Accepted  
**Date:** 2026-06-23  
**Authors:** Phase 0 contract owners (Agent A + Agent B)  
**Closes:** Phase 0 — Contracts and Registries Guardrails  

---

## Context

The ambient agent implementation plan requires multiple agents (A–F) to deliver
in parallel.  Without an explicit versioning policy, a contract change by one
agent can silently break adapters developed by another.

The repository is moving from a single-script prototype to a modular,
plugin-based architecture.  Contracts must be **stable** enough that parallel
delivery can proceed with low merge-conflict risk, yet **evolvable** enough that
new capabilities can be added without requiring a full ecosystem upgrade.

---

## Decision

### 1. Contract major versions are breaking boundaries

The runtime declares `CONTRACT_MAJOR_VERSION = 1` in
`src/ambient_agent/contracts/versions.py`.

A plugin or adapter is **incompatible** if its `plugin_major_version` attribute
differs from `CONTRACT_MAJOR_VERSION`.  The runtime calls `check_compatibility()`
at every registration point and raises `IncompatibleVersionError` immediately,
before the first cycle begins.

This is a fail-fast policy: no partially-wired registries, no silent degradation.

### 2. Minor versions are always backwards-compatible

`CONTRACT_MINOR_VERSION` tracks non-breaking additions (new optional fields,
new interface methods with default implementations, new phase constants).
Plugins do not need to track the minor version.  A plugin built against `1.0`
will work with a `1.3` runtime without any changes.

### 3. How a major version increment is authorized

A major version increment requires:

1. A new ADR entry (this file becomes `ADR-001`; the next would be `ADR-002`).
2. A migration note in `CONTRACT_V1.md` (or a new `CONTRACT_V2.md`).
3. A changelog note in every issue tracking adapters that must be updated.
4. A 30-day deprecation window during which both versions run in parallel (where
   feasible) before the old version is removed.

No single agent may unilaterally increment the major version.  The change
requires a PR that includes the ADR and is reviewed by at least two agent owners.

### 4. Deprecation process for individual interface methods

When a method on a plugin interface needs to be removed:

1. Mark it `@deprecated` (comment or decorator) in the same PR that adds the
   replacement.
2. Keep the old signature for at least one minor version cycle.
3. Remove the deprecated method only in the next major version.

### 5. Schema fields in KnowledgeState and ChangeSet

`schema_version` fields in `KnowledgeState` and `ChangeSet` default to
`CONTRACT_MAJOR_VERSION`.  Persistence layers must reject objects whose
`schema_version` differs from the runtime's contract major version.

---

## Consequences

### Positive

- Parallel agents can develop adapters independently without coordination
  overhead until a breaking change is actually needed.
- Integration failures are surfaced at registration time (startup), not deep
  inside a running cycle.
- Onboarding a new source or sink requires only: adapter class, registration
  call, and tests.  No changes to core orchestration files.

### Negative / Trade-offs

- Strict major-version matching means all plugins must be updated together
  when a breaking change is needed.  This is intentional — it forces the team
  to plan breaking changes rather than letting them accumulate silently.
- The `CONTRACT_MINOR_VERSION` constant is informational only; the runtime does
  not currently enforce minor-version lower bounds.

---

## Alternatives Considered

### Semantic versioning string comparison

Using a full `"1.0.0"` semver string and comparing major/minor/patch
separately adds complexity for minimal benefit at this stage.  Integer major
version is sufficient and simpler.

### No versioning (trust convention)

Without enforcement, a plugin with an incompatible interface will fail with an
`AttributeError` or `TypeError` deep inside a running cycle, which is harder
to diagnose than an explicit `IncompatibleVersionError` at startup.

### Capability negotiation

Allowing plugins to advertise a range of compatible major versions was
considered but deferred to a future ADR once the ecosystem is larger.

---

## References

- `CONTRACT_V1.md` — frozen V1 contract specification
- `src/ambient_agent/contracts/versions.py` — `check_compatibility` implementation
- `src/ambient_agent/registry/registry.py` — registration enforcement points
- `tests/contract/test_compatibility.py` — major-version rejection tests
- `IMPLEMENTATION_PLAN.md` — delivery phases and module ownership
- `AGENT_GUIDELINES.md` — contract freeze policy
