# Loop Tests

Loop tests validate ingest -> compare -> act -> persist behavior over multiple cycles.

Required first scenarios:

1. New fact appears and creates an action.
2. Duplicate event appears and is suppressed.
3. New evidence resolves a previously open item.
