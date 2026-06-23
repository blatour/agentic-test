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

1. Agent A - Core Runtime Refactor
2. Agent B - Data and Persistence
3. Agent C - Analysis Contract and Model Gateway
4. Agent D - Policy and Notification Engine
5. Agent E - Operability and Deployment
6. Agent F - Test and CI Quality Gates

## Labels (Recommended)

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

## Dependency Notes

- Agent A and Agent B should start first.
- Agent C can start after analysis interfaces are scaffolded by Agent A.
- Agent D depends on Agent C response schema and Agent B action persistence.
- Agent E depends on Agent A runtime modularization.
- Agent F should begin early with skeleton tests and then expand as contracts freeze.
