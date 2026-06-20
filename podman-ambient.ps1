param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$RemainingArgs
)

$scriptPath = Join-Path -Path $PSScriptRoot -ChildPath "scripts\podman-ambient.ps1"

if (-not (Test-Path -Path $scriptPath)) {
    throw "Expected script not found at: $scriptPath"
}

& powershell -ExecutionPolicy Bypass -File $scriptPath @RemainingArgs
exit $LASTEXITCODE
