<#
.SYNOPSIS
    Fetch pipeline & job info from internal GitLab and save to workspace/tmp/.

.DESCRIPTION
    Uses an authenticated GitLab session (from gitlab-auth.ps1) to query
    pipeline status, job details, and optionally job trace logs.

.PARAMETER ProjectId
    Numeric GitLab project ID.

.PARAMETER PipelineId
    Pipeline ID to inspect. If omitted, fetches the latest pipeline for the given Ref.

.PARAMETER Ref
    Git ref (branch) to find the latest pipeline for. Default: "main".

.PARAMETER IncludeTrace
    If set, also downloads the job trace (log) for each failed job.

.PARAMETER OutDir
    Output directory. Default: workspace/tmp under the repo root.

.EXAMPLE
    .\fetch-pipeline.ps1 -ProjectId 117719 -Ref main -IncludeTrace
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [int]$ProjectId,

    [int]$PipelineId = 0,

    [string]$Ref = "main",

    [switch]$IncludeTrace,

    [string]$GitLabBase = "https://gitlab.aws.site.gs.com",

    [string]$OutDir = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Resolve output dir
if (-not $OutDir) {
    $repoRoot = (Get-Item $PSScriptRoot).Parent.Parent.Parent.FullName
    $OutDir = Join-Path $repoRoot "workspace\tmp"
}
if (-not (Test-Path $OutDir)) { New-Item -ItemType Directory -Path $OutDir -Force | Out-Null }

# Authenticate
$authScript = Join-Path $PSScriptRoot "gitlab-auth.ps1"
$session = & $authScript -GitLabBase $GitLabBase

$apiBase = "$GitLabBase/api/v4/projects/$ProjectId"

function Invoke-GitLabApi {
    param([string]$Path, [string]$Accept = "application/json")
    $url = "$apiBase$Path"
    Write-Verbose "GET $url"
    $r = Invoke-WebRequest -Uri $url -WebSession $session -UseBasicParsing `
            -Headers @{ Accept = $Accept } -TimeoutSec 30
    return $r
}

# --- Get pipeline ---
if ($PipelineId -eq 0) {
    Write-Host "Fetching latest pipeline for ref=$Ref ..."
    $r = Invoke-GitLabApi "/pipelines?ref=$Ref&per_page=1"
    $pipelines = $r.Content | ConvertFrom-Json
    if ($pipelines.Count -eq 0) {
        Write-Warning "No pipelines found for ref=$Ref"
        return
    }
    $PipelineId = $pipelines[0].id
}

Write-Host "Pipeline ID: $PipelineId"
$r = Invoke-GitLabApi "/pipelines/$PipelineId"
$pipeline = $r.Content | ConvertFrom-Json
$pipelineFile = Join-Path $OutDir "gitlab-pipeline-$PipelineId.json"
$r.Content | Set-Content -Path $pipelineFile -Encoding UTF8
Write-Host "Pipeline status: $($pipeline.status)"
Write-Host "Saved: $pipelineFile"

# --- Get jobs ---
Write-Host "Fetching jobs ..."
$r = Invoke-GitLabApi "/pipelines/$PipelineId/jobs?per_page=100"
$jobs = $r.Content | ConvertFrom-Json
$jobsFile = Join-Path $OutDir "gitlab-pipeline-$PipelineId-jobs.json"
$r.Content | Set-Content -Path $jobsFile -Encoding UTF8
Write-Host "Jobs: $($jobs.Count)"
Write-Host "Saved: $jobsFile"

foreach ($job in $jobs) {
    $status = $job.status
    $reason = if ($job.failure_reason) { " ($($job.failure_reason))" } else { "" }
    $runner = if ($job.runner) { " runner=$($job.runner.description)" } else { "" }
    Write-Host "  [$status] $($job.name)$reason$runner"

    # Download trace for failed jobs
    if ($IncludeTrace -and $status -eq "failed") {
        Write-Host "    Downloading trace ..."
        try {
            $tr = Invoke-GitLabApi "/jobs/$($job.id)/trace" -Accept "text/plain"
            $traceFile = Join-Path $OutDir "gitlab-job-$($job.id)-trace.txt"
            $tr.Content | Set-Content -Path $traceFile -Encoding UTF8
            Write-Host "    Saved: $traceFile"
        } catch {
            Write-Warning "    Could not download trace: $_"
        }
    }
}

# --- Summary ---
$failed = @($jobs | Where-Object { $_.status -eq "failed" })
if ($failed.Count -gt 0) {
    Write-Host "`n$($failed.Count) failed job(s):"
    foreach ($j in $failed) {
        Write-Host "  - $($j.name): $($j.failure_reason)"
    }
} else {
    Write-Host "`nAll jobs passed."
}
