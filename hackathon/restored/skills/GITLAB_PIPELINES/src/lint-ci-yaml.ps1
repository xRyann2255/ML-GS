<#
.SYNOPSIS
    Validate a .gitlab-ci.yml file via the GitLab CI Lint API.

.PARAMETER ProjectId
    Numeric GitLab project ID.

.PARAMETER YamlPath
    Path to the .gitlab-ci.yml file to validate. Default: .gitlab-ci.yml in repo root.

.EXAMPLE
    .\lint-ci-yaml.ps1 -ProjectId 117719
    .\lint-ci-yaml.ps1 -ProjectId 117719 -YamlPath "C:\path\to\.gitlab-ci.yml"
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [int]$ProjectId,

    [string]$YamlPath = "",

    [string]$GitLabBase = "https://gitlab.aws.site.gs.com"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Resolve YAML path
if (-not $YamlPath) {
    $repoRoot = (Get-Item $PSScriptRoot).Parent.Parent.Parent.FullName
    $YamlPath = Join-Path $repoRoot ".gitlab-ci.yml"
}

if (-not (Test-Path $YamlPath)) {
    throw "YAML file not found: $YamlPath"
}

$yamlContent = Get-Content -Path $YamlPath -Raw -Encoding UTF8

# Authenticate
$authScript = Join-Path $PSScriptRoot "gitlab-auth.ps1"
$session = & $authScript -GitLabBase $GitLabBase

# Lint
$url = "$GitLabBase/api/v4/projects/$ProjectId/ci/lint"
$body = @{ content = $yamlContent } | ConvertTo-Json -Depth 2

$r = Invoke-WebRequest -Uri $url -Method POST -Body $body `
        -ContentType "application/json" -WebSession $session -UseBasicParsing -TimeoutSec 30

$result = $r.Content | ConvertFrom-Json

if ($result.valid) {
    Write-Host "VALID" -ForegroundColor Green
} else {
    Write-Host "INVALID" -ForegroundColor Red
}

if ($result.errors -and $result.errors.Count -gt 0) {
    Write-Host "`nErrors:"
    foreach ($e in $result.errors) { Write-Host "  - $e" -ForegroundColor Red }
}

if ($result.warnings -and $result.warnings.Count -gt 0) {
    Write-Host "`nWarnings:"
    foreach ($w in $result.warnings) { Write-Host "  - $w" -ForegroundColor Yellow }
}

# Save result
$outDir = Join-Path (Get-Item $PSScriptRoot).Parent.Parent.Parent.FullName "workspace\tmp"
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir -Force | Out-Null }
$outFile = Join-Path $outDir "gitlab-ci-lint-result.json"
$r.Content | Set-Content -Path $outFile -Encoding UTF8
Write-Host "`nSaved: $outFile"

return $result
