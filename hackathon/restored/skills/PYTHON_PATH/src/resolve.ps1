<#
.SYNOPSIS
    Resolve the Python interpreter path from user.json config.
.DESCRIPTION
    Reads workspace/config/user.json -> python_path field.
    Falls back to H:\venv311\Scripts\python.exe if missing.
    If the resolved path does not exist, scans H:\ for venv*/Scripts/python.exe,
    picks the highest version, updates user.json, and outputs the found path.
.OUTPUTS
    The absolute path to a valid python.exe, or exits with code 1 if none found.
#>
param(
    [string]$WorkspaceRoot = (Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)))
)

$ErrorActionPreference = 'Stop'
$configPath = Join-Path $WorkspaceRoot 'workspace\config\user.json'
$fallback = 'H:\venv311\Scripts\python.exe'
$resolved = $null

# --- 1. Try user.json ---
if (Test-Path $configPath) {
    try {
        $cfg = Get-Content $configPath -Raw | ConvertFrom-Json
        if ($cfg.python_path) {
            $resolved = $cfg.python_path
        }
    }
    catch {
        Write-Host "WARN: Failed to parse $configPath - using fallback" -ForegroundColor Yellow
    }
}

if (-not $resolved) {
    $resolved = $fallback
}

# --- 1b. PATH fallback (mirrors resolve.py::_find_python_windows) ---
if (-not (Test-Path $resolved)) {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { $resolved = $cmd.Source }
}

# --- 2. Validate resolved path ---
if (Test-Path $resolved) {
    Write-Output $resolved
    exit 0
}

Write-Host "WARN: Configured python not found at $resolved - scanning for alternatives..." -ForegroundColor Yellow

# --- 3. Auto-detect: scan H:\venv* for python.exe ---
$candidates = @()
Get-ChildItem -Path 'H:\' -Directory -Filter 'venv*' -ErrorAction SilentlyContinue | ForEach-Object {
    $py = Join-Path $_.FullName 'Scripts\python.exe'
    if (Test-Path $py) {
        $candidates += $py
    }
}
$candidates = $candidates | Sort-Object -Descending

if ($candidates.Count -eq 0) {
    Write-Error "ERROR: No Python installation found in H:\venv*\Scripts\python.exe"
    exit 1
}

$found = $candidates[0]
Write-Host "Found Python at: $found" -ForegroundColor Green

# --- 4. Update user.json ---
if (Test-Path $configPath) {
    try {
        $cfg = Get-Content $configPath -Raw | ConvertFrom-Json
        $cfg.python_path = $found
        $json = $cfg | ConvertTo-Json -Depth 10
        [System.IO.File]::WriteAllText($configPath, $json, [System.Text.Encoding]::UTF8)
        Write-Host "Updated $configPath with python_path = $found" -ForegroundColor Green
    }
    catch {
        Write-Host "WARN: Could not update config - $($_.Exception.Message)" -ForegroundColor Yellow
    }
}
else {
    # Create minimal user.json
    $templatePath = Join-Path $WorkspaceRoot 'workspace\config\user.json.template'
    if (Test-Path $templatePath) {
        try {
            $cfg = Get-Content $templatePath -Raw | ConvertFrom-Json
            $cfg.python_path = $found
            $json = $cfg | ConvertTo-Json -Depth 10
            [System.IO.File]::WriteAllText($configPath, $json, [System.Text.Encoding]::UTF8)
            Write-Host "Created config from template with python_path = $found" -ForegroundColor Green
        }
        catch {
            Write-Host "WARN: Could not create config from template" -ForegroundColor Yellow
        }
    }
    else {
        $json = @{ python_path = $found } | ConvertTo-Json
        [System.IO.File]::WriteAllText($configPath, $json, [System.Text.Encoding]::UTF8)
        Write-Host "Created minimal config with python_path = $found" -ForegroundColor Green
    }
}

Write-Output $found
exit 0
