## Objective

Define and enforce structured analysis output and implement a model gateway abstraction that enriches ChangeSet quality for decisioning.

## Scope

1. Create strict JSON schema for analysis responses.
2. Implement model gateway with Ollama adapter.
3. Add validation and fallback for malformed model output.
4. Expose confidence and reason codes consumable by compare/policy stages.

## Deliverables

1. Analysis schema and parser utilities.
2. Gateway abstraction and Ollama implementation.
3. Contract tests with valid and invalid responses.
4. Mapping from analysis response to ChangeSet enrichment fields.

## Acceptance Criteria

1. Analysis payloads are schema-validated before persistence.
2. Invalid model output is classified and handled safely.
3. Runtime remains functional in dry-run mode.
4. Policy stage can consume analysis confidence and reason codes without source-specific parsing.

## Dependencies

1. Coordinate output persistence fields with Agent B.
2. Coordinate integration interfaces with Agent A.

## References

1. `IMPLEMENTATION_PLAN.md`
2. `CONTRACT_V1.md`
3. `AGENT_GUIDELINES.md`
