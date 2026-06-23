# Operations Guide

This document describes operational commands, health monitoring, and structured
logging for the Ambient Agent.

## Quick Reference

| Goal | Command |
|---|---|
| Start full deployment | `.\scripts\podman-ambient.ps1 -Action deploy` |
| Check infrastructure status | `.\scripts\podman-ambient.ps1 -Action status` |
| View agent health report | `.\scripts\podman-ambient.ps1 -Action health` |
| Run full diagnostics | `.\scripts\podman-ambient.ps1 -Action diagnostics` |
| Tail container logs | `.\scripts\podman-ambient.ps1 -Action logs` |
| Inspect agent memory | `.\scripts\podman-ambient.ps1 -Action memory` |
| Check Ollama model status | `.\scripts\podman-ambient.ps1 -Action ollama-status` |
| Stop the agent container | `.\scripts\podman-ambient.ps1 -Action stop` |

---

## Health Report

The health report combines persisted state (lifetime counters) with runtime
telemetry when the process is live.

### Via CLI flag (reads state file only)

```powershell
# Inside the container (execed by the health action):
python samples/ambient_agent.py --health --state-file /app/data/ambient_agent_state.json
```

```powershell
# From the host via the deployment script:
.\scripts\podman-ambient.ps1 -Action health
```

### Sample output

```
=== Ambient Agent Health Report ===
Generated:  2026-06-23 14:00:00

--- Cycle Status ---
Lifetime cycles completed : 42
Last run                  : 2026-06-23 13:59:45
Last cycle mode           : web-all

--- Last Cycle Source Status ---
  web-github           ok              WEB [2026-06-23T13:59:44Z] - GitHub PushEvent by @example ...
  web-usgs             ok              WEB [quake] - USGS earthquake M1.2 near Ridgecrest, CA ...
  web-nasa             ok              WEB [2026-06-23] - NASA APOD 'Title' (image, url=...) ...

===================================
```

### What each section means

| Section | Contents |
|---|---|
| **Cycle Status** | Lifetime cycle count, timestamp of last run, and last source mode. |
| **Last Cycle Source Status** | Per-source outcome from the most recently persisted cycle. |
| **Model Status** | Last model call outcome and latency (written to state when agent runs). |
| **Runtime Telemetry** | Live metrics only available while the process is running. |
| **Source Health (this run)** | Per-source ok/error counts, ok-rate, avg latency, convergence label. |
| **Stage Timing (this run)** | Ingest / analyze / persist / cycle timing averages and maximums. |

### Convergence labels

| Label | Meaning |
|---|---|
| `healthy` | ok-rate ≥ 90 % |
| `degraded` | ok-rate between 50 % and 90 % |
| `down` | ok-rate < 50 % |
| `unknown` | No calls recorded yet this run |

---

## Diagnostics Action

`diagnostics` combines status, health, memory, and Ollama status into one
output pass:

```powershell
.\scripts\podman-ambient.ps1 -Action diagnostics
```

Use this when investigating an incident — it captures all observable state in
one command.

---

## Structured Logs

Enable structured JSON logs by passing `--structured-logs` to the agent.  Each
log record is written to **stderr** as a single newline-terminated JSON object
so it can be forwarded to any log aggregator without interfering with the
normal `stdout` progress output.

### Enabling in a container run

Set the flag when starting the container manually:

```powershell
.\scripts\podman-ambient.ps1 -Action run
# Then edit the Run-Container call or add --structured-logs to $agentArgs
```

Or pass it directly:

```powershell
podman exec -it ambient-agent python samples/ambient_agent.py --source web-all --structured-logs
```

### Log record schema

Every record contains at minimum `ts` and `event`.  Optional fields are only
present when relevant to the event type.

| Field | Type | Description |
|---|---|---|
| `ts` | ISO-8601 string | UTC timestamp of the record. |
| `event` | string | Dot-namespaced event name (see table below). |
| `cycle_id` | UUID string | Correlates all records in one pipeline cycle. |
| `source` | string | Event source name (`web-github`, `web-usgs`, `web-nasa`, `simulated`). |
| `stage` | string | Pipeline stage: `ingest`, `analyze`, `persist`, `cycle`. |
| `status` | string | Outcome: `ok`, `dry-run`, `error`, `fetch-error`, `parse-error`. |
| `latency_ms` | float | Elapsed time for the named operation, in milliseconds. |
| `model` | string | Model name (on `agent.cycle` records). |
| `error` | string | Error message (on failure records). |

### Event names

| Event | Stage | Description |
|---|---|---|
| `agent.cycle` | — | Dispatched once per loop iteration before cycle functions are called. |
| `cycle.start` | cycle | Cycle function entered. |
| `cycle.complete` | cycle | Cycle completed successfully. |
| `cycle.error` | cycle | Unhandled exception terminated the cycle. |
| `ingest.ok` | ingest | Source fetch completed successfully. |
| `ingest.error` | ingest | Source fetch failed (network or parse error). |
| `analyze.ok` | analyze | Model or mock analysis completed. |
| `persist.ok` | persist | History file written. |

### Example records

```json
{"ts":"2026-06-23T14:00:00Z","event":"agent.cycle","cycle_id":"f1a2...","source":"web-all","model":"qwen3.5:4b"}
{"ts":"2026-06-23T14:00:00Z","event":"cycle.start","cycle_id":"f1a2...","source":"web-all","stage":"cycle"}
{"ts":"2026-06-23T14:00:01Z","event":"ingest.ok","cycle_id":"f1a2...","source":"web-github","stage":"ingest","status":"ok","latency_ms":340.2}
{"ts":"2026-06-23T14:00:01Z","event":"analyze.ok","cycle_id":"f1a2...","source":"web-github","stage":"analyze","status":"ok","latency_ms":4210.7}
{"ts":"2026-06-23T14:00:05Z","event":"persist.ok","cycle_id":"f1a2...","source":"web-all","stage":"persist","status":"ok","latency_ms":1.3}
{"ts":"2026-06-23T14:00:05Z","event":"cycle.complete","cycle_id":"f1a2...","source":"web-all","stage":"cycle","status":"ok","latency_ms":12500.0}
```

### Parsing structured logs from a running container

```powershell
# Stream only structured log records (stderr) from the container:
podman logs -f ambient-agent 2>&1 | Select-String '^{'
```

---

## Stage Timing Reference

| Stage | What is timed |
|---|---|
| `ingest` | HTTP fetch from the event source through response parsing. |
| `analyze` | Model prompt construction through response extraction (or mock). |
| `persist` | Writing the analysis entry to the history markdown file. |
| `cycle` | End-to-end wall time for the complete loop iteration. |

High `ingest` latency suggests source API slowness or network congestion.
High `analyze` latency is expected for cold model loads; warm runs should be
under a few seconds.

---

## Common Operations

### Restart the agent after a crash

```powershell
.\scripts\podman-ambient.ps1 -Action stop
.\scripts\podman-ambient.ps1 -Action run
```

### Deploy with GPU support for Ollama

```powershell
.\scripts\podman-ambient.ps1 -Action deploy -OllamaGpu all -AutoCreateOllama
```

### Run a single dry-run cycle for testing

```powershell
python samples/ambient_agent.py --source web-all --dry-run --once
```

### Check agent health without a running container

```powershell
python samples/ambient_agent.py --health --state-file ambient_agent_state.json
```

---

## Troubleshooting

| Symptom | Action |
|---|---|
| Container exits immediately | `.\scripts\podman-ambient.ps1 -Action logs` to inspect exit reason. |
| All sources show `fetch-error` | Check network connectivity and source API status. |
| `analyze` latency > 60 s | Model may be cold-loading; first call is expected to be slow. Subsequent calls should be faster. |
| Health report shows `convergence: down` | Multiple consecutive failures on a source. Review error logs and check API key / rate limits. |
| State file missing in health report | Agent has not completed a cycle yet, or the state file path is wrong. |
