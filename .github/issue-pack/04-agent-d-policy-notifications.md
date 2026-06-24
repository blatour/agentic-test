## Objective

Implement the decision layer with policy evaluation, suppression windows, and notification action dispatch.

## Scope

1. Policy rules for escalation and duplicate suppression.
2. Action generation and dispatch interfaces.
3. Initial sinks: console and webhook.
4. Decisioning based on ChangeSet deltas and KnowledgeState context.

## Deliverables

1. Policy engine with configurable thresholds.
2. Notification dispatcher with pluggable sinks.
3. Tests for suppression and escalation behavior.
4. Rules that can open, update, and resolve tracked items.

## Acceptance Criteria

1. At least one rule triggers a persisted action.
2. Duplicate events are suppressed in configured windows.
3. Notification send outcomes are recorded.
4. At least one previously-open item can be resolved when new evidence arrives.

## Dependencies

1. Action persistence support from Agent B.
2. Analysis contract fields from Agent C.

## References

1. `IMPLEMENTATION_PLAN.md`
2. `CONTRACT_V1.md`
3. `AGENT_GUIDELINES.md`
