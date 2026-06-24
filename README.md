# Ambient Agentic Test

This project runs an always-on ambient agent loop that can:

- Wake up on an interval
- Check external sources (GitHub public events, USGS earthquakes, NASA APOD)
- Summarize what it checked
- Persist state to disk
- Sleep and repeat

On restart, it loads prior state and prints a startup report that includes:

- Prior cycle count
- Last run timestamp
- Last cycle source mode
- Last cycle checked events and status
- Last seen event IDs used for dedupe

## Local Run (Windows PowerShell)

Use the virtual environment Python so dependencies are available:

```powershell
c:/Users/blato/OneDrive/Documents/GitHub/AIGenerated/agentic-test/.venv/Scripts/python.exe samples/ambient_agent.py --source web-all --dry-run --interval 60
```

One-shot run:

```powershell
c:/Users/blato/OneDrive/Documents/GitHub/AIGenerated/agentic-test/.venv/Scripts/python.exe samples/ambient_agent.py --source web-all --dry-run --once
```

## Podman Container (Windows + WSL)

### 1. Build Image

From repo root:

```powershell
podman build -t ambient-agentic-test -f Containerfile .
```

### Automated Workflow (Recommended)

Use the helper script to automate machine init/start, build, and run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/podman-ambient.ps1 -Action deploy
```

Common actions:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/podman-ambient.ps1 -Action status
powershell -ExecutionPolicy Bypass -File scripts/podman-ambient.ps1 -Action build
powershell -ExecutionPolicy Bypass -File scripts/podman-ambient.ps1 -Action run -DryRun
powershell -ExecutionPolicy Bypass -File scripts/podman-ambient.ps1 -Action logs
powershell -ExecutionPolicy Bypass -File scripts/podman-ambient.ps1 -Action stop
```

Useful parameters:

- `-MachineName podman-machine-default`
- `-IntervalSeconds 120`
- `-OllamaContainerName ollama-backend`
- `-OllamaModel qwen3.5:4b`
- `-AutoCreateOllama`
- `-WarmOllamaModel`
- `-OllamaDevice gpu/all`
- `-OllamaUrl http://ollama-backend:11434/api/generate`
- `-NetworkName ambient-agent-net`
- `-NasaApiKey DEMO_KEY`

Ollama behavior in automation:

- For `setup`, `run`, and `deploy`, the script verifies the Ollama container exists and is running.
- It checks whether the configured model exists and automatically pulls it if missing.
- If the Ollama container is missing, you can auto-create it with `-AutoCreateOllama`.
- If your CDI exposes GPU devices, pass them through with `-OllamaDevice gpu/all` (or your CDI name); the Ollama container is recreated so the device mount applies.
- If `-WarmOllamaModel` is passed, it runs a tiny warm-up prompt before starting the ambient agent.
- By default, if `-OllamaUrl` is not provided, the agent uses `http://ollama-backend:11434/api/generate`.

**Verified working setup command** (creates Ollama container + pulls model):

```powershell
powershell -ExecutionPolicy Bypass -File podman-ambient.ps1 -Action setup -AutoCreateOllama -OllamaContainerName ollama-backend -OllamaImage docker.io/ollama/ollama:latest -OllamaModel qwen3.5:4b
```

Then deploy the ambient agent against it:

```powershell
powershell -ExecutionPolicy Bypass -File podman-ambient.ps1 -Action deploy -OllamaContainerName ollama-backend -OllamaModel qwen3.5:4b
```

Or setup + deploy in one step:

```powershell
powershell -ExecutionPolicy Bypass -File podman-ambient.ps1 -Action deploy -AutoCreateOllama -OllamaContainerName ollama-backend -OllamaImage docker.io/ollama/ollama:latest -OllamaModel qwen3.5:4b
```

### 2. Run Continuously with Persistent Memory

This mounts the repo folder so state and logs persist between restarts.

```powershell
podman run -d --name ambient-agent \
	--restart unless-stopped \
	-v ${PWD}:/app/data \
	-e AMBIENT_LOG_FILE=/app/data/ambient_agent_history.md \
	-e AMBIENT_STATE_FILE=/app/data/ambient_agent_state.json \
	-e OLLAMA_URL=http://host.containers.internal:11434/api/generate \
	ambient-agentic-test
```

Notes:

- `host.containers.internal` lets the container reach services on the Windows host.
- If you only want fetch-and-summarize without model calls, add `--dry-run` to container args (see custom run command below).

### 3. Custom Run Command

Override the default CMD to change source, interval, or dry-run behavior:

```powershell
podman run --rm -it \
	-v ${PWD}:/app/data \
	-e AMBIENT_LOG_FILE=/app/data/ambient_agent_history.md \
	-e AMBIENT_STATE_FILE=/app/data/ambient_agent_state.json \
	ambient-agentic-test \
	python samples/ambient_agent.py --source web-all --dry-run --interval 30
```

### 4. Useful Podman Commands

```powershell
podman logs -f ambient-agent
podman stop ambient-agent
podman rm ambient-agent
```

## State and History Files

- `ambient_agent_state.json`: remembers last-seen IDs and last cycle summary
- `ambient_agent_history.md`: append-only cycle output and recommendations

## Enterprise Planning

- Implementation plan for scaling this prototype into a realistic enterprise-style system:
	- `IMPLEMENTATION_PLAN.md`
- Contract baseline for parallel implementation:
	- `CONTRACT_V1.md`
	- `AGENT_TASKS_V1.md`
	- `AGENT_WAVES.md`
	- `src/ambient_agent/contracts/`
- Companion issue pack and automation:
	- `ISSUE_PACK.md`
	- `.github/issue-pack/`
	- `scripts/open-issues.ps1`
	- `scripts/sync-issue-pack.ps1`
- Multi-agent execution guide:
	- `AGENT_GUIDELINES.md`

