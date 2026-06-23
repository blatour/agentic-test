param(
    [ValidateSet("status", "setup", "build", "run", "deploy", "logs", "stop", "memory", "ollama-status", "health", "diagnostics")]
    [string]$Action = "deploy",
    [string]$MachineName = "podman-machine-default",
    [string]$ImageName = "ambient-agentic-test",
    [string]$ContainerName = "ambient-agent",
    [string]$DataVolume = "ambient-agent-data",
    [int]$IntervalSeconds = 120,
    [switch]$DryRun,
    [string]$NasaApiKey = "DEMO_KEY",
    [string]$OllamaContainerName = "ollama-backend",
    [string]$OllamaModel = "qwen3.5:4b",
    [string]$OllamaImage = "docker.io/ollama/ollama:latest",
    [string]$OllamaDataVolume = "ollama-models",
    [string]$NetworkName = "ambient-agent-net",
    [switch]$AutoCreateOllama,
    [switch]$SkipOllamaCheck,
    [switch]$WarmOllamaModel,
    [ValidateSet("all")]
    [string]$OllamaGpu,
    [string[]]$OllamaDevice,
    [string]$OllamaUrl
)

$ErrorActionPreference = "Stop"

function Write-Info {
    param([string]$Message)
    Write-Host "[ambient-podman] $Message"
}

function Invoke-Podman {
    param([string[]]$PodmanArgs)
    & podman @PodmanArgs
    if ($LASTEXITCODE -ne 0) {
        throw "podman command failed: podman $($PodmanArgs -join ' ')"
    }
}

function Ensure-PodmanInstalled {
    Write-Info "Checking Podman installation"
    & podman --version | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Podman CLI not found. Install Podman first."
    }
}

function Ensure-MachineRunning {
    Write-Info "Ensuring Podman machine '$MachineName' exists and is running"
    $machinesJson = & podman machine list --format json
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to query podman machines."
    }

    $machines = @()
    if ($machinesJson) {
        $machines = $machinesJson | ConvertFrom-Json
    }

    $target = $machines | Where-Object { $_.Name -eq $MachineName }
    if (-not $target) {
        Write-Info "Machine '$MachineName' not found, creating it"
        Invoke-Podman -PodmanArgs @("machine", "init", $MachineName)
        $machines = (& podman machine list --format json) | ConvertFrom-Json
        $target = $machines | Where-Object { $_.Name -eq $MachineName }
    }

    if (-not $target) {
        throw "Failed to create or find machine '$MachineName'."
    }

    if ($target.Running -ne $true) {
        Write-Info "Starting machine '$MachineName'"
        Invoke-Podman -PodmanArgs @("machine", "start", $MachineName)
    }

    Write-Info "Machine '$MachineName' is ready"
}

function Ensure-Network {
    & podman network exists $NetworkName
    if ($LASTEXITCODE -ne 0) {
        Write-Info "Creating network '$NetworkName'"
        Invoke-Podman -PodmanArgs @("network", "create", $NetworkName)
    }
}

function Test-ContainerExists {
    param([string]$Name)
    & podman container exists $Name
    return ($LASTEXITCODE -eq 0)
}

function Test-ContainerRunning {
    param([string]$Name)
    $running = (& podman inspect --format "{{.State.Running}}" $Name 2>$null)
    return (($LASTEXITCODE -eq 0) -and ($running -eq "true"))
}

function Test-OllamaModelExists {
    param(
        [string]$ContainerName,
        [string]$Model
    )

    try {
        & podman exec $ContainerName ollama show $Model >$null 2>$null
        return ($LASTEXITCODE -eq 0)
    }
    catch {
        return $false
    }
}

function Normalize-OllamaDevice {
    param([string]$Device)

    if ([string]::IsNullOrWhiteSpace($Device)) {
        return $Device
    }

    if ($Device -eq "gpu/all") {
        return "nvidia.com/gpu=all"
    }

    return $Device
}

function Ensure-OllamaReady {
    if ($SkipOllamaCheck) {
        Write-Info "Skipping Ollama readiness checks"
        return
    }

    Ensure-Network
    Write-Info "Ensuring Ollama container '$OllamaContainerName' is ready"

    if (-not (Test-ContainerExists -Name $OllamaContainerName)) {
        if (-not $AutoCreateOllama) {
            throw "Ollama container '$OllamaContainerName' was not found. Re-run with -AutoCreateOllama, or create/start it manually."
        }

        & podman volume exists $OllamaDataVolume
        if ($LASTEXITCODE -ne 0) {
            Write-Info "Creating volume '$OllamaDataVolume' for Ollama models"
            Invoke-Podman -PodmanArgs @("volume", "create", $OllamaDataVolume)
        }

        Write-Info "Creating Ollama container '$OllamaContainerName'"
        Invoke-Podman -PodmanArgs @(
            "run",
            "-d",
            "--name", $OllamaContainerName,
            "--restart", "unless-stopped",
            "--network", $NetworkName,
            "--network-alias", $OllamaContainerName,
            "-v", "${OllamaDataVolume}:/root/.ollama",
            $OllamaImage
        )

        if ($OllamaDevice -and $OllamaDevice.Count -gt 0) {
            Write-Info "Note: pass-through GPU devices are only applied when the Ollama container is created."
            Write-Info "Requested Ollama devices: $($OllamaDevice -join ', ')"
        }
    }

    if (-not (Test-ContainerRunning -Name $OllamaContainerName)) {
        Write-Info "Starting Ollama container '$OllamaContainerName'"
        Invoke-Podman -PodmanArgs @("start", $OllamaContainerName)
    }

    & podman exec $OllamaContainerName sh -lc "command -v ollama" >$null 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Container '$OllamaContainerName' does not include the ollama CLI. Use an Ollama image (for example docker.io/ollama/ollama:latest) or point to your real Ollama container."
    }

    Write-Info "Waiting for Ollama service to become responsive"
    $ready = $false
    for ($i = 1; $i -le 30; $i++) {
        try {
            & podman exec $OllamaContainerName ollama list >$null 2>$null
            if ($LASTEXITCODE -eq 0) {
                $ready = $true
                break
            }
        }
        catch {
            # Continue retry loop while Ollama starts up.
        }
        Start-Sleep -Seconds 2
    }

    if (-not $ready) {
        throw "Ollama container is running but not responding to CLI checks."
    }

    Write-Info "Checking Ollama model '$OllamaModel'"
    if (-not (Test-OllamaModelExists -ContainerName $OllamaContainerName -Model $OllamaModel)) {
        Write-Info "Model '$OllamaModel' not present. Pulling it now."
        Invoke-Podman -PodmanArgs @("exec", $OllamaContainerName, "ollama", "pull", $OllamaModel)
    }

    if ($WarmOllamaModel) {
        Write-Info "Warming Ollama model '$OllamaModel'"
        Invoke-Podman -PodmanArgs @(
            "exec",
            $OllamaContainerName,
            "ollama",
            "run",
            $OllamaModel,
            "Respond only with the word ready."
        )
    }

    Write-Info "Ollama container/model readiness checks passed"
}

function Build-Image {
    Write-Info "Building image '$ImageName'"
    Invoke-Podman -PodmanArgs @("build", "-t", $ImageName, "-f", "Containerfile", ".")
}

function Ensure-DataVolume {
    & podman volume exists $DataVolume
    if ($LASTEXITCODE -ne 0) {
        Write-Info "Creating volume '$DataVolume'"
        Invoke-Podman -PodmanArgs @("volume", "create", $DataVolume)
    }
}

function Run-Container {
    Write-Info "Starting container '$ContainerName'"
    Ensure-Network
    Ensure-DataVolume

    $effectiveOllamaUrl = $OllamaUrl
    if (-not $PSBoundParameters.ContainsKey("OllamaUrl") -or [string]::IsNullOrWhiteSpace($OllamaUrl)) {
        $effectiveOllamaUrl = "http://${OllamaContainerName}:11434/api/generate"
    }

    $null = & podman rm -f $ContainerName 2>$null

    $agentArgs = @("python", "samples/ambient_agent.py", "--source", "web-all", "--interval", "$IntervalSeconds")
    if ($DryRun) {
        $agentArgs += "--dry-run"
    }

    $runArgs = @(
        "run",
        "-d",
        "--name", $ContainerName,
        "--restart", "unless-stopped",
        "--network", $NetworkName,
        "-v", "${DataVolume}:/app/data",
        "-e", "AMBIENT_LOG_FILE=/app/data/ambient_agent_history.md",
        "-e", "AMBIENT_STATE_FILE=/app/data/ambient_agent_state.json",
        "-e", "OLLAMA_URL=$effectiveOllamaUrl",
        "-e", "NASA_API_KEY=$NasaApiKey",
        $ImageName
    ) + $agentArgs

    Invoke-Podman -PodmanArgs $runArgs
    Write-Info "Agent OLLAMA_URL: $effectiveOllamaUrl"
    Write-Info "Container '$ContainerName' is running"
}

function Show-Status {
    Write-Info "Podman machine status"
    & podman machine list

    Write-Info "Network status"
    & podman network ls --filter "name=$NetworkName"

    if (-not $SkipOllamaCheck) {
        Write-Info "Ollama container status"
        & podman ps -a --filter "name=$OllamaContainerName"
    }

    Write-Info "Container status"
    & podman ps -a --filter "name=$ContainerName"
}

function Show-Logs {
    Write-Info "Streaming logs for '$ContainerName'"
    Invoke-Podman -PodmanArgs @("logs", "-f", $ContainerName)
}

function Show-Memory {
    param([int]$HistoryLines = 120)

    Write-Info "=== Agent State (ambient_agent_state.json) ==="
    & podman exec $ContainerName cat /app/data/ambient_agent_state.json
    if ($LASTEXITCODE -ne 0) {
        Write-Host "(state file not yet written or container not running)"
    }

    Write-Host ""
    Write-Info "=== Recent History (last $HistoryLines lines of ambient_agent_history.md) ==="
    & podman exec $ContainerName sh -c "tail -n $HistoryLines /app/data/ambient_agent_history.md"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "(history file not yet written or container not running)"
    }
}

function Show-OllamaStatus {
    Write-Info "Ollama version"
    & podman exec $OllamaContainerName ollama --version

    Write-Info "Loaded models (ollama ps)"
    & podman exec $OllamaContainerName ollama ps

    Write-Info "All available models (ollama list)"
    & podman exec $OllamaContainerName ollama list
}

function Recreate-OllamaWithDevices {
    $normalizedDevices = @()
    if ($OllamaDevice -and $OllamaDevice.Count -gt 0) {
        $normalizedDevices = $OllamaDevice | ForEach-Object { Normalize-OllamaDevice $_ }
    }

    if ([string]::IsNullOrWhiteSpace($OllamaGpu) -and $normalizedDevices.Count -eq 0) {
        return
    }

    Ensure-Network
    $runArgs = @(
        "run",
        "-d",
        "--name", $OllamaContainerName,
        "--restart", "unless-stopped",
        "--network", $NetworkName,
        "--network-alias", $OllamaContainerName,
        "-v", "${OllamaDataVolume}:/root/.ollama"
    )

    if (-not [string]::IsNullOrWhiteSpace($OllamaGpu)) {
        $runArgs += @("--gpus", $OllamaGpu)
    }

    foreach ($device in $normalizedDevices) {
        $runArgs += @("--device", $device)
    }

    if (Test-ContainerExists -Name $OllamaContainerName) {
        $deviceSummary = @()
        if (-not [string]::IsNullOrWhiteSpace($OllamaGpu)) {
            $deviceSummary += "gpus=$OllamaGpu"
        }
        if ($normalizedDevices.Count -gt 0) {
            $deviceSummary += ($normalizedDevices -join ', ')
        }
        Write-Info "Recreating Ollama container '$OllamaContainerName' with GPU settings: $($deviceSummary -join '; ')"
        $null = & podman rm -f $OllamaContainerName 2>$null
    }

    & podman volume exists $OllamaDataVolume
    if ($LASTEXITCODE -ne 0) {
        Write-Info "Creating volume '$OllamaDataVolume' for Ollama models"
        Invoke-Podman -PodmanArgs @("volume", "create", $OllamaDataVolume)
    }

    $runArgs += $OllamaImage
    Invoke-Podman -PodmanArgs $runArgs
}

function Show-Health {
    Write-Info "Agent health report (reads from persisted state inside container)"
    & podman exec $ContainerName python samples/ambient_agent.py `
        --health `
        --state-file /app/data/ambient_agent_state.json
    if ($LASTEXITCODE -ne 0) {
        Write-Host "(health report unavailable: container may not be running or state not yet written)"
    }
}

function Show-Diagnostics {
    Write-Info "=== Diagnostics ==="
    Write-Host ""

    Write-Info "--- Container and Infrastructure Status ---"
    Show-Status
    Write-Host ""

    Write-Info "--- Agent Health ---"
    Show-Health
    Write-Host ""

    Write-Info "--- Agent Memory ---"
    Show-Memory
    Write-Host ""

    if (-not $SkipOllamaCheck) {
        Write-Info "--- Ollama Status ---"
        Show-OllamaStatus
    }
}

function Stop-Container {
    Write-Info "Stopping and removing '$ContainerName'"
    $null = & podman rm -f $ContainerName 2>$null
}

Ensure-PodmanInstalled

$needsOllamaGpuSetup = ($OllamaDevice -and $OllamaDevice.Count -gt 0) -or (-not [string]::IsNullOrWhiteSpace($OllamaGpu))

switch ($Action) {
    "setup" {
        Ensure-MachineRunning
        if ($needsOllamaGpuSetup) {
            Recreate-OllamaWithDevices
        }
        Ensure-OllamaReady
        Show-Status
    }
    "build" {
        Ensure-MachineRunning
        Build-Image
    }
    "run" {
        Ensure-MachineRunning
        Ensure-OllamaReady
        Run-Container
        Show-Status
    }
    "deploy" {
        Ensure-MachineRunning
        if ($needsOllamaGpuSetup) {
            Recreate-OllamaWithDevices
        }
        Ensure-OllamaReady
        Build-Image
        Run-Container
        Show-Status
    }
    "logs" {
        Ensure-MachineRunning
        Show-Logs
    }
    "stop" {
        Ensure-MachineRunning
        Stop-Container
        Show-Status
    }
    "status" {
        Ensure-MachineRunning
        Show-Status
    }
    "memory" {
        Ensure-MachineRunning
        Show-Memory
    }
    "ollama-status" {
        Ensure-MachineRunning
        Show-OllamaStatus
    }
    "health" {
        Ensure-MachineRunning
        Show-Health
    }
    "diagnostics" {
        Ensure-MachineRunning
        Show-Diagnostics
    }
}
