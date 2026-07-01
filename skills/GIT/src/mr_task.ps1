param(
    [Parameter(Mandatory)][string]$ArgsFile
)
# GitLab MR create/update via REST API.
# Called by mr_task.cmd — never directly.

$ErrorActionPreference = 'Stop'

$a = Get-Content $ArgsFile -Raw | ConvertFrom-Json

# --- Auth ---
$cred = echo "protocol=https`nhost=gitlab.aws.site.gs.com" | git credential fill 2>$null
$token = ($cred | Select-String "password" | ForEach-Object { ($_ -split '=',2)[1] })
if (-not $token) { Write-Error "Could not obtain GitLab token via git credential fill"; exit 1 }

$headers = @{ "PRIVATE-TOKEN" = $token; "Content-Type" = "application/json" }
$projectId = [uri]::EscapeDataString("eq-tech/sts/ml-vol-estimator")
$baseUrl = "https://gitlab.aws.site.gs.com/api/v4"

$me = (Invoke-RestMethod -Uri "$baseUrl/user" -Headers $headers -TimeoutSec 30).id

$action = if ($a.action) { $a.action } else { "create" }
$targetBranch = if ($a.target_branch) { $a.target_branch } else { "master" }
$outFile = $a.out_file

$result = ""

switch ($action) {
    "create" {
        $sourceBranch = $a.source_branch
        if (-not $sourceBranch) { Write-Error "source_branch is required for create"; exit 1 }
        if (-not $a.title) { Write-Error "title is required"; exit 1 }

        # Check if MR already exists
        $existing = Invoke-RestMethod -Uri "$baseUrl/projects/$projectId/merge_requests?state=opened&source_branch=$sourceBranch" -Headers $headers -TimeoutSec 30
        if ($existing.Count -gt 0) {
            $result = "MR already exists: !$($existing[0].iid) - $($existing[0].web_url)"
            Write-Host $result
            if ($outFile) { [System.IO.File]::WriteAllText($outFile, $result) }
            exit 0
        }

        $body = @{
            source_branch        = $sourceBranch
            target_branch        = $targetBranch
            title                = $a.title
            description          = if ($a.description) { $a.description } else { "" }
            assignee_id          = $me
            remove_source_branch = $true
        } | ConvertTo-Json -Compress

        $mr = Invoke-RestMethod -Method Post -Uri "$baseUrl/projects/$projectId/merge_requests" -Headers $headers -Body $body -TimeoutSec 30
        $result = "MR created: !$($mr.iid) - $($mr.web_url)"
    }
    "update" {
        $mrIid = $a.mr_iid
        if (-not $mrIid) { Write-Error "mr_iid is required for update"; exit 1 }

        $bodyHash = @{
            assignee_id          = $me
            remove_source_branch = $true
        }
        if ($a.title) { $bodyHash.title = $a.title }
        if ($a.description) { $bodyHash.description = $a.description }

        $body = $bodyHash | ConvertTo-Json -Compress

        $mr = Invoke-RestMethod -Method Put -Uri "$baseUrl/projects/$projectId/merge_requests/$mrIid" -Headers $headers -Body $body -TimeoutSec 30
        $result = "MR updated: !$($mr.iid) - $($mr.web_url)"
    }
    default {
        Write-Error "Unknown action: $action (expected 'create' or 'update')"
        exit 1
    }
}

Write-Host $result
if ($outFile) {
    $dir = Split-Path $outFile -Parent
    if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    [System.IO.File]::WriteAllText($outFile, $result)
}
