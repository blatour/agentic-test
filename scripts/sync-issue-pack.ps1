param(
    [string]$ConfigPath = ".github/issue-pack/issues.json"
)

$ErrorActionPreference = "Stop"

function Write-Info {
    param([string]$Message)
    Write-Host "[sync-issue-pack] $Message"
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
        # Fall through to explicit error.
    }

    return $null
}

function Find-IssueByTitle {
    param(
        [string]$Owner,
        [string]$Repo,
        [string]$Title,
        [hashtable]$Headers
    )

    $query = ('"{0}" repo:{1}/{2} is:issue' -f $Title, $Owner, $Repo)
    $encoded = [System.Uri]::EscapeDataString($query)
    $searchUrl = "https://api.github.com/search/issues?q=$encoded&per_page=10"
    $response = Invoke-RestMethod -Method Get -Uri $searchUrl -Headers $Headers
    if ($response.total_count -gt 0) {
        return $response.items[0]
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
if ([string]::IsNullOrWhiteSpace($config.repo)) {
    throw "Missing repo in config: $ConfigPath"
}

$parts = $config.repo -split "/"
if ($parts.Count -ne 2) {
    throw "Invalid repo format '$($config.repo)'. Expected OWNER/REPO."
}

$owner = $parts[0]
$repo = $parts[1]
$headers = @{
    Authorization = "Bearer $token"
    Accept = "application/vnd.github+json"
    "X-GitHub-Api-Version" = "2022-11-28"
}

foreach ($entry in $config.issues) {
    $title = [string]$entry.title
    $bodyFile = [string]$entry.bodyFile
    if (-not (Test-Path $bodyFile)) {
        throw "Body file not found: $bodyFile"
    }

    $issue = Find-IssueByTitle -Owner $owner -Repo $repo -Title $title -Headers $headers
    if (-not $issue) {
        Write-Info "Issue not found for title: $title"
        continue
    }

    $labels = @()
    if ($config.labels) {
        $labels += $config.labels
    }
    if ($entry.labels) {
        $labels += $entry.labels
    }

    $payload = [ordered]@{
        title = $title
        body = [string](Get-Content -Path $bodyFile -Raw)
        labels = @($labels | ForEach-Object { [string]$_ })
    } | ConvertTo-Json -Depth 6 -Compress

    $issueNumber = $issue.number
    Write-Info "Updating issue #${issueNumber}: $title"
    $null = Invoke-RestMethod -Method Patch -Uri "https://api.github.com/repos/$owner/$repo/issues/$issueNumber" -Headers $headers -Body $payload -ContentType "application/json"
}

Write-Info "Issue pack synchronization complete."
