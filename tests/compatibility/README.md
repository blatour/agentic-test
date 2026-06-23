# Compatibility Tests

Compatibility tests validate major version handling rules.

Required first scenarios:

1. Accept version 1.x envelopes.
2. Reject version 2.x envelopes with explicit compatibility error.
3. Ensure rejection path writes diagnostic telemetry.
