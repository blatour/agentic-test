# Companion Issue Pack

This file contains the ready-to-open issue set for the enterprise implementation plan.

## How to Use

1. Confirm repository owner and repo name in `.github/issue-pack/issues.json`.
2. Set `GITHUB_TOKEN` in your shell with repo issue write permissions.
3. Run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/open-issues.ps1
```

4. Review created issues and assign owners for Agent A through Agent F.

## Issue Set

1. Phase 0 - Contracts and Registries Guardrails
2. Agent A - Core Runtime Refactor
3. Agent B - Data and Persistence
4. Agent C - Analysis Contract and Model Gateway
5. Agent D - Policy and Notification Engine
6. Agent E - Operability and Deployment
7. Agent F - Test and CI Quality Gates

## Labels (Recommended)

- `phase-0`
- `phase-1`
- `phase-2`
- `phase-3`
- `agent-a`
- `agent-b`
- `agent-c`
- `agent-d`
- `agent-e`
- `agent-f`
- `architecture`
- `persistence`
- `analysis`
- `policy`
- `observability`
- `ci`
- `loop-core`
- `changeset`
- `knowledge-state`

## Dependency Notes

- Phase 0 should start first and be completed or nearly complete before deep feature work.
- Agent A and Agent B should start immediately after Phase 0 contract agreement.
- Agent C can start after analysis interfaces are scaffolded by Agent A.
- Agent D depends on Agent C response schema and Agent B action persistence.
- Agent E depends on Agent A runtime modularization.
- Agent F should begin early with skeleton tests and then expand as contracts freeze.

## Loop Success Criteria (Cross-Issue)

The issue pack is successful only if the system demonstrates all of the following:

1. Ingest: multi-source payloads are captured and persisted in raw and canonical form.
2. Compare: each cycle produces a non-empty or explicitly-empty ChangeSet with reason codes.
3. Act: at least one action type is emitted based on ChangeSet deltas.
4. Persist: KnowledgeState updates across cycles and can resolve previously open items.
