# Ambient Agent Next Steps

This note captures the most useful follow-up work after the current demo.

## Why Not Keep Soaking The Demo

The current prototype already proved the core loop works:

- the agent wakes up on an interval
- it reads external events
- it persists state across cycles
- it can write summaries to a history file
- the Podman/Ollama wiring is usable

A long overnight soak run would mostly confirm the same failure modes repeatedly:

- NASA APOD rate limiting
- occasional Ollama timeouts or cold-start issues
- fetch failures being mixed together with model failures
- state that is still too shallow to be interesting long-term

## Next Stage Goals

### 1. Move State Into SQLite

Replace the JSON state file with a real SQLite database so the agent can keep structured memory.

Suggested tables:

- `events` - normalized raw events from all sources
- `analyses` - model outputs tied to events and cycles
- `cycles` - one row per wake cycle with timings and status
- `sources` - metadata about GitHub, USGS, NASA, and future sources
- `open_questions` - things the agent is actively tracking
- `actions` - notifications or follow-up tasks the agent decides to take

### 2. Separate Failure Types

Right now the history blends several different classes of failure together.

Track them distinctly:

- source fetch failure
- DNS or network failure
- model inference timeout
- model cold load / startup delay
- rate limit / HTTP 429
- parse or validation error

That makes the run history much more useful for debugging and for later agent behavior.

### 3. Make The Agent Reactive

Add a small reaction layer so the agent can do more than summarize.

Possible reactions:

- send a notification when severity crosses a threshold
- create an internal follow-up task when a source changes unexpectedly
- increase polling frequency for an interesting source
- reduce polling frequency for noisy or failing sources
- suppress repeated duplicate events for a time window

### 4. Add Open Questions / Intent

Give the agent a short list of things it is trying to learn.

Examples:

- Is GitHub activity increasing or stable?
- Are USGS events clustering around a region or time window?
- Is Ollama staying warm enough to avoid cold-start delays?
- Is NASA worth keeping as a live source, or should it be lower priority?

This turns the agent from a logger into something that has continuity.

### 5. Improve The Prompt Contract

Move from freeform markdown output to a structured response.

A good JSON response shape might be:

- `severity`
- `summary`
- `recommendation`
- `confidence`
- `opens_question`
- `closes_question`
- `suggested_action`
- `should_escalate`

That makes it easier for the runtime to decide what to do next.

### 6. Keep Ollama Warm

The current setup showed that model load and memory pressure matter.

Ideas:

- use a smaller model for steady-state runs
- send a warmup prompt on startup
- keep the model loaded with periodic tiny requests
- track the last inference time and reload behavior
- keep the inference timeout longer than the cold-start window

### 7. Revisit The Source List

NASA APOD is useful for demo purposes, but it is noisy because the demo key rate-limits.

Possible options:

- remove NASA until you have a real API key
- keep NASA but lower its priority
- replace it with another stable public source
- make it optional in a source configuration table

### 8. Add Health Telemetry

Track basic agent health separate from event health:

- cycle duration
- source latency
- inference latency
- number of cycles completed
- number of retries
- failure rate by source
- last successful model call

That will make future tuning much easier.

## Candidate Follow-Up Features

- SQLite schema and data-access layer
- event deduplication windows
- source priority and backoff
- structured notifications
- dashboard or CLI summary view
- replay mode for historical events
- richer startup report showing recent health trends
- explicit model warmup on startup

## Suggested Order

1. Add SQLite and structured cycle/event storage
2. Split failure types cleanly
3. Add a structured JSON response contract
4. Add open questions and actions
5. Rework source priorities and backoff
6. Only then consider overnight soak testing again

## Bottom Line

The current demo has done its job. The next real step is to make the agent stateful enough to learn from its own cycles and react differently when the world changes.
