## Objective

Implement the decision layer with policy evaluation, suppression windows, and notification action dispatch.

## Scope

1. Policy rules for escalation and duplicate suppression.
2. Action generation and dispatch interfaces.
3. Initial sinks: console and webhook.

## Deliverables

1. Policy engine with configurable thresholds.
2. Notification dispatcher with pluggable sinks.
3. Tests for suppression and escalation behavior.

## Acceptance Criteria

1. At least one rule triggers a persisted action.
2. Duplicate events are suppressed in configured windows.
3. Notification send outcomes are recorded.

## Dependencies

1. Action persistence support from Agent B.
2. Analysis contract fields from Agent C.

## References

1. `IMPLEMENTATION_PLAN.md`
2. `AGENT_GUIDELINES.md`
