<#
.SYNOPSIS
    Search GitLab code, MRs, commits, and issues via the Search API.

.DESCRIPTION
    By default performs a GLOBAL search across all GitLab projects.
    Use -ProjectId or -GroupId to narrow scope.

    Auth: PRIVATE-TOKEN from Windows Credential Manager (git credential fill).

.PARAMETER Query
    Search string (required).

.PARAMETER Scope
    blobs (code), wiki_blobs, commits, merge_requests, issues, milestones, projects.
    Default: blobs.

.PARAMETER ProjectId
    Numeric project ID. Narrows search to one project. Omit for global.

.PARAMETER GroupId
    Numeric group ID. Narrows search to a group. Omit for global.

.PARAMETER MaxResults
    Maximum results (paginated). Default: 20.

.PARAMETER GitLabBase
    GitLab instance URL. Default: https://gitlab.aws.site.gs.com

.PARAMETER OutFile
    Path to save raw JSON. Default: workspace/tmp/gitlab-search-results.json

.EXAMPLE
    # Global code search
    .\gitlab-search.ps1 -Query "persona"

    # Project-scoped search
    .\gitlab-search.ps1 -Query "workflow" -ProjectId 117719

    # Group-scoped MR search
    .\gitlab-search.ps1 -Query "pipeline fix" -GroupId 4521 -Scope merge_requests

    # Search projects by name
    .\gitlab-search.ps1 -Query "volatility" -Scope projects -MaxResults 10
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$Query,

    [ValidateSet("blobs","wiki_blobs","commits","merge_requests","issues","milestones","projects")]
    [string]$Scope = "blobs",

    [int]$ProjectId = 0,

    [int]$GroupId = 0,

    [int]$MaxResults = 20,

    [string]$GitLabBase = "https://gitlab.aws.site.gs.com",

    [string]$OutFile = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# --- Auth via PAT from Windows Credential Manager ---
$host_ = ([System.Uri]$GitLabBase).Host
$credInput = "protocol=https`nhost=$host_`n`n"
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = "git"
$psi.Arguments = "credential fill"
$psi.RedirectStandardInput  = $true
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError  = $true
$psi.UseShellExecute = $false
$psi.CreateNoWindow  = $true
$proc = [System.Diagnostics.Process]::Start($psi)
$proc.StandardInput.Write($credInput)
$proc.StandardInput.Close()
$credOut = $proc.StandardOutput.ReadToEnd()
$proc.WaitForExit(10000)
if (-not $proc.HasExited) { $proc.Kill() }

$token = ($credOut -split "`n" | Where-Object { $_ -match "^password=" } | ForEach-Object { ($_ -split '=',2)[1].Trim() })
if (-not $token) {
    throw "No GitLab PAT found in Credential Manager for $host_. Store via: git credential approve"
}

$headers = @{ "PRIVATE-TOKEN" = $token }

# --- Build search URL prefix ---
if ($ProjectId -gt 0) {
    $urlPrefix = "$GitLabBase/api/v4/projects/$ProjectId/search"
    $scopeLabel = "project $ProjectId"
} elseif ($GroupId -gt 0) {
    $urlPrefix = "$GitLabBase/api/v4/groups/$GroupId/search"
    $scopeLabel = "group $GroupId"
} else {
    $urlPrefix = "$GitLabBase/api/v4/search"
    $scopeLabel = "global"
}

# --- Paginate ---
$allResults = @()
$page = 1
$perPage = [Math]::Min($MaxResults, 100)

while ($allResults.Count -lt $MaxResults) {
    $encodedQuery = [System.Uri]::EscapeDataString($Query)
    $url = "${urlPrefix}?scope=$Scope&search=$encodedQuery&page=$page&per_page=$perPage"

    Write-Verbose "GET $url"
    $resp = Invoke-WebRequest -Uri $url -Headers $headers -UseBasicParsing -TimeoutSec 30
    $items = $resp.Content | ConvertFrom-Json

    if ($items.Count -eq 0) { break }

    $allResults += $items
    $page++

    if ($items.Count -lt $perPage) { break }
}

if ($allResults.Count -gt $MaxResults) {
    $allResults = $allResults[0..($MaxResults - 1)]
}

# --- Resolve project paths for web URLs ---
$projCache = @{}
if ($Scope -in "blobs","wiki_blobs","commits") {
    $uniqueIds = $allResults | Where-Object { $_.project_id } | ForEach-Object { $_.project_id } | Sort-Object -Unique
    foreach ($projId in $uniqueIds) {
        try {
            $proj = Invoke-RestMethod -Uri "$GitLabBase/api/v4/projects/$projId" -Headers $headers -TimeoutSec 30
            $projCache[$projId] = $proj.path_with_namespace
        } catch {
            $projCache[$projId] = $null
        }
    }
}

# --- Display ---
Write-Host "`nFound $($allResults.Count) result(s) for '$Query' (scope: $Scope, $scopeLabel)`n" -ForegroundColor Green

switch ($Scope) {
    "blobs" {
        foreach ($r in $allResults) {
            $projPath = $projCache[[int]$r.project_id]
            $proj = if ($projPath) { " [$projPath]" } elseif ($r.project_id) { " [project:$($r.project_id)]" } else { "" }
            Write-Host "  $($r.filename)$proj" -ForegroundColor Yellow
            Write-Host "    path: $($r.path)"
            if ($projPath) {
                $lineAnchor = if ($r.startline) { "#L$($r.startline)" } else { "" }
                Write-Host "    $GitLabBase/$projPath/-/blob/$($r.ref)/$($r.path)$lineAnchor" -ForegroundColor Cyan
            }
            if ($r.startline) {
                $lineCount = ($r.data -split "`n").Count
                Write-Host "    lines: $($r.startline)-$($r.startline + $lineCount - 1)"
            }
            $preview = $r.data.Substring(0, [Math]::Min(200, $r.data.Length))
            Write-Host "    $preview"
            Write-Host ""
        }
    }
    "merge_requests" {
        foreach ($r in $allResults) {
            Write-Host "  !$($r.iid) [$($r.state)] $($r.title)" -ForegroundColor Yellow
            Write-Host "    author: $($r.author.username)  created: $($r.created_at)"
            Write-Host "    $($r.web_url)"
            Write-Host ""
        }
    }
    "commits" {
        foreach ($r in $allResults) {
            $projPath = if ($r.project_id) { $projCache[[int]$r.project_id] } else { $null }
            Write-Host "  $($r.short_id) $($r.title)" -ForegroundColor Yellow
            Write-Host "    author: $($r.author_name)  date: $($r.created_at)"
            if ($projPath -and $r.id) {
                Write-Host "    $GitLabBase/$projPath/-/commit/$($r.id)" -ForegroundColor Cyan
            }
            Write-Host ""
        }
    }
    "issues" {
        foreach ($r in $allResults) {
            Write-Host "  #$($r.iid) [$($r.state)] $($r.title)" -ForegroundColor Yellow
            Write-Host "    author: $($r.author.username)  created: $($r.created_at)"
            if ($r.web_url) { Write-Host "    $($r.web_url)" }
            Write-Host ""
        }
    }
    "projects" {
        foreach ($r in $allResults) {
            Write-Host "  $($r.path_with_namespace) [id:$($r.id)]" -ForegroundColor Yellow
            if ($r.description) {
                $desc = $r.description.Substring(0, [Math]::Min(120, $r.description.Length))
                Write-Host "    $desc"
            }
            Write-Host "    $($r.web_url)"
            Write-Host ""
        }
    }
    default {
        $allResults | ConvertTo-Json -Depth 5 | Write-Host
    }
}

# --- Save JSON ---
if (-not $OutFile) {
    $repoRoot = (Get-Item $PSScriptRoot).Parent.Parent.Parent.FullName
    $OutFile = Join-Path $repoRoot "workspace\tmp\gitlab-search-results.json"
}
$allResults | ConvertTo-Json -Depth 10 | Set-Content -Path $OutFile -Encoding UTF8
Write-Host "Raw JSON saved to $OutFile" -ForegroundColor Cyan
