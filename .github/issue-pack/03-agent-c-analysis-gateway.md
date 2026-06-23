## Objective

Define and enforce structured analysis output and implement a model gateway abstraction.

## Scope

1. Create strict JSON schema for analysis responses.
2. Implement model gateway with Ollama adapter.
3. Add validation and fallback for malformed model output.

## Deliverables

1. Analysis schema and parser utilities.
2. Gateway abstraction and Ollama implementation.
3. Contract tests with valid and invalid responses.

## Acceptance Criteria

1. Analysis payloads are schema-validated before persistence.
2. Invalid model output is classified and handled safely.
3. Runtime remains functional in dry-run mode.

## Dependencies

1. Coordinate output persistence fields with Agent B.
2. Coordinate integration interfaces with Agent A.

## References

1. `IMPLEMENTATION_PLAN.md`
2. `AGENT_GUIDELINES.md`
