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
