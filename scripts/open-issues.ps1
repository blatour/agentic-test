param(
    [string]$ConfigPath = ".github/issue-pack/issues.json"
)

$ErrorActionPreference = "Stop"

function Write-Info {
    param([string]$Message)
    Write-Host "[open-issues] $Message"
}

function Get-GitHubToken {
    if (-not [string]::IsNullOrWhiteSpace($env:GITHUB_TOKEN)) {
        return $env:GITHUB_TOKEN
    }

    try {
        $inputBlock = "protocol=https`nhost=github.com`n`n"
        $credentialLines = $inputBlock | git credential fill
        $passwordLine = $credentialLines | Where-Object { $_ -like "password=*" } | Select-Object -First 1
        if ($passwordLine) {
            return $passwordLine.Substring(9)
        }
    }
    catch {
        # Continue to explicit error below if no credential can be resolved.
    }

    return $null
}

if (-not (Test-Path $ConfigPath)) {
    throw "Issue config file not found: $ConfigPath"
}

$token = Get-GitHubToken
if ([string]::IsNullOrWhiteSpace($token)) {
    throw "No GitHub token available. Set GITHUB_TOKEN or sign in through Git credential manager, then retry."
}

$config = Get-Content -Path $ConfigPath -Raw | ConvertFrom-Json

if ([string]::IsNullOrWhiteSpace($config.repo) -or $config.repo -eq "REPLACE_OWNER/REPLACE_REPO") {
    throw "Config repo is not set. Update '.github/issue-pack/issues.json' repo value first."
}

$repoParts = $config.repo -split "/"
if ($repoParts.Count -ne 2) {
    throw "Invalid repo format '$($config.repo)'. Expected OWNER/REPO."
}

$owner = $repoParts[0]
$repo = $repoParts[1]

$headers = @{
    Authorization = "Bearer $token"
    Accept = "application/vnd.github+json"
    "X-GitHub-Api-Version" = "2022-11-28"
}

foreach ($issue in $config.issues) {
    $bodyPath = $issue.bodyFile
    if (-not (Test-Path $bodyPath)) {
        throw "Issue body file not found: $bodyPath"
    }

    $labels = @()
    if ($config.labels) {
        $labels += $config.labels
    }
    if ($issue.labels) {
        $labels += $issue.labels
    }

    $normalizedLabels = @($labels | ForEach-Object { [string]$_ })
    $payload = [ordered]@{
        title = [string]$issue.title
        body = [string](Get-Content -Path $bodyPath -Raw)
        labels = $normalizedLabels
    } | ConvertTo-Json -Depth 6 -Compress

    Write-Info "Creating issue: $($issue.title)"
    $response = Invoke-RestMethod -Method Post -Uri "https://api.github.com/repos/$owner/$repo/issues" -Headers $headers -Body $payload -ContentType "application/json"
    Write-Info "Created #$($response.number): $($response.html_url)"
}

Write-Info "All issue definitions processed successfully."
