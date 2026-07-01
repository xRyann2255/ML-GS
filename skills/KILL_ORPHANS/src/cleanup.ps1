<#
.SYNOPSIS
    Kill orphaned PowerShell, conhost, Python, secexpr, and Code processes.

.DESCRIPTION
    Cleans up orphaned processes that accumulate from VS Code terminal usage:
    - powershell.exe: all except the current process
    - conhost.exe: those whose parent process is dead
    - python.exe / pythonw.exe: those whose parent process is dead
    - secexpr.exe / perl.exe: those whose parent process is dead (secexpr wraps perl)
    - Code.exe: those not part of any active VS Code window tree

    VS Code child processes are never killed — only genuine orphans whose
    parent process has exited.

.PARAMETER DryRun
    Preview what would be killed without taking action.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File cleanup.ps1
    powershell -ExecutionPolicy Bypass -File cleanup.ps1 -DryRun
#>
param(
    [switch]$DryRun
)

$ErrorActionPreference = 'SilentlyContinue'
$currentPid = $PID

# Also protect parent process (defense-in-depth for `powershell -File` invocations)
$parentPid = (Get-CimInstance Win32_Process -Filter "ProcessId=$currentPid" -Property ParentProcessId -ErrorAction SilentlyContinue).ParentProcessId

Write-Host "`n=== Orphan Process Cleanup ===" -ForegroundColor Cyan
if ($DryRun) {
    Write-Host "[DRY RUN] No processes will be killed.`n" -ForegroundColor Yellow
}

# --- Build global parent map (single WMI query for efficiency) ---
$parentMap = @{}
Get-CimInstance Win32_Process -Property ProcessId, ParentProcessId -ErrorAction SilentlyContinue |
    ForEach-Object { $parentMap[[int]$_.ProcessId] = [int]$_.ParentProcessId }

function Test-ParentAlive([int]$ProcessId) {
    $parentId = $parentMap[$ProcessId]
    if ($null -eq $parentId -or $parentId -eq 0) { return $false }
    try {
        $null = Get-Process -Id $parentId -ErrorAction Stop
        return $true
    }
    catch { return $false }
}

# --- Build VS Code protected PID set ---
# Protects: any Code.exe with a window, plus all Code.exe descendants in that tree.
$codeProcs = @(Get-Process -Name Code -ErrorAction SilentlyContinue)
$protectedCodePids = @{}
foreach ($c in $codeProcs) {
    if ($c.MainWindowHandle -ne [IntPtr]::Zero) {
        $protectedCodePids[$c.Id] = $true
    }
}
# Propagate protection to children of protected Code.exe processes
$changed = $true
while ($changed) {
    $changed = $false
    foreach ($c in $codeProcs) {
        if (-not $protectedCodePids.ContainsKey($c.Id)) {
            $pid = $parentMap[$c.Id]
            if ($null -ne $pid -and $protectedCodePids.ContainsKey($pid)) {
                $protectedCodePids[$c.Id] = $true
                $changed = $true
            }
        }
    }
}

# --- PowerShell orphans ---
$psProcs = Get-Process powershell | Where-Object { $_.Id -ne $currentPid -and $_.Id -ne $parentPid }
$psCount = ($psProcs | Measure-Object).Count
$psMemMB = [math]::Round(($psProcs | Measure-Object WorkingSet64 -Sum).Sum / 1MB, 1)

Write-Host "PowerShell processes (excluding current PID $currentPid): $psCount" -ForegroundColor White

if ($psCount -gt 0) {
    if ($DryRun) {
        Write-Host "  Would kill $psCount PowerShell processes (~${psMemMB} MB)" -ForegroundColor Yellow
    }
    else {
        $psProcs | Stop-Process -Force -ErrorAction SilentlyContinue
        Write-Host "  Killed $psCount PowerShell processes (~${psMemMB} MB freed)" -ForegroundColor Green
    }
}
else {
    Write-Host "  None found." -ForegroundColor DarkGray
}

# Brief pause to let OS clean up child conhost processes
if (-not $DryRun -and $psCount -gt 0) {
    Start-Sleep -Milliseconds 500
}

# --- Conhost orphans ---
$conhostProcs = @(Get-Process -Name conhost -ErrorAction SilentlyContinue)
$orphanConhosts = @()
$liveConhosts = 0

foreach ($ch in $conhostProcs) {
    if (Test-ParentAlive $ch.Id) { $liveConhosts++ }
    else { $orphanConhosts += $ch }
}

$orphanConhostCount = $orphanConhosts.Count
$orphanConhostMemMB = [math]::Round(($orphanConhosts | Measure-Object WorkingSet64 -Sum).Sum / 1MB, 1)

Write-Host "`nConhost processes: $($conhostProcs.Count) total, $orphanConhostCount orphaned, $liveConhosts live" -ForegroundColor White

if ($orphanConhostCount -gt 0) {
    if ($DryRun) {
        Write-Host "  Would kill $orphanConhostCount conhost processes (~${orphanConhostMemMB} MB)" -ForegroundColor Yellow
    }
    else {
        $orphanConhosts | Stop-Process -Force -ErrorAction SilentlyContinue
        Write-Host "  Killed $orphanConhostCount conhost processes (~${orphanConhostMemMB} MB freed)" -ForegroundColor Green
    }
}
else {
    Write-Host "  No orphans found." -ForegroundColor DarkGray
}

# --- Python orphans (parent-alive check; VS Code children are naturally protected) ---
$pythonProcs = @(Get-Process -Name python, pythonw -ErrorAction SilentlyContinue)
$orphanPythons = @()
$livePythons = 0

foreach ($py in $pythonProcs) {
    if (Test-ParentAlive $py.Id) { $livePythons++ }
    else { $orphanPythons += $py }
}

$orphanPythonCount = $orphanPythons.Count
$orphanPythonMemMB = [math]::Round(($orphanPythons | Measure-Object WorkingSet64 -Sum).Sum / 1MB, 1)

Write-Host "`nPython processes: $($pythonProcs.Count) total, $orphanPythonCount orphaned, $livePythons live" -ForegroundColor White

if ($orphanPythonCount -gt 0) {
    if ($DryRun) {
        Write-Host "  Would kill $orphanPythonCount Python processes (~${orphanPythonMemMB} MB)" -ForegroundColor Yellow
    }
    else {
        $orphanPythons | Stop-Process -Force -ErrorAction SilentlyContinue
        Write-Host "  Killed $orphanPythonCount Python processes (~${orphanPythonMemMB} MB freed)" -ForegroundColor Green
    }
}
else {
    Write-Host "  No orphans found." -ForegroundColor DarkGray
}

# --- Secexpr orphans (parent-alive check) ---
$secexprProcs = @(Get-Process -Name secexpr -ErrorAction SilentlyContinue)
$orphanSecexprs = @()
$liveSecexprs = 0

foreach ($se in $secexprProcs) {
    if (Test-ParentAlive $se.Id) { $liveSecexprs++ }
    else { $orphanSecexprs += $se }
}

# Also find orphaned perl processes (secexpr spawns perl as child)
$perlProcs = @(Get-Process -Name perl -ErrorAction SilentlyContinue)
$orphanPerls = @()
$livePerls = 0

foreach ($pl in $perlProcs) {
    if (Test-ParentAlive $pl.Id) { $livePerls++ }
    else { $orphanPerls += $pl }
}

$allSecexprOrphans = @($orphanSecexprs) + @($orphanPerls)
$orphanSecexprCount = $orphanSecexprs.Count
$orphanPerlCount = $orphanPerls.Count
$allSecexprOrphanCount = $allSecexprOrphans.Count
$allSecexprMemMB = [math]::Round(($allSecexprOrphans | Measure-Object WorkingSet64 -Sum).Sum / 1MB, 1)

Write-Host "`nSecexpr processes: $($secexprProcs.Count) total, $orphanSecexprCount orphaned, $liveSecexprs live" -ForegroundColor White
Write-Host "Perl processes: $($perlProcs.Count) total, $orphanPerlCount orphaned, $livePerls live" -ForegroundColor White

if ($allSecexprOrphanCount -gt 0) {
    if ($DryRun) {
        Write-Host "  Would kill $orphanSecexprCount secexpr + $orphanPerlCount perl processes (~${allSecexprMemMB} MB)" -ForegroundColor Yellow
    }
    else {
        $allSecexprOrphans | Stop-Process -Force -ErrorAction SilentlyContinue
        Write-Host "  Killed $orphanSecexprCount secexpr + $orphanPerlCount perl processes (~${allSecexprMemMB} MB freed)" -ForegroundColor Green
    }
}
else {
    Write-Host "  No orphans found." -ForegroundColor DarkGray
}

# --- Code.exe orphans (protected tree built above; only kill unprotected with dead parent) ---
$orphanCodes = @()
$liveCodes = 0

foreach ($c in $codeProcs) {
    if ($protectedCodePids.ContainsKey($c.Id)) {
        $liveCodes++
    }
    elseif (Test-ParentAlive $c.Id) {
        $liveCodes++
    }
    else {
        $orphanCodes += $c
    }
}

$orphanCodeCount = $orphanCodes.Count
$orphanCodeMemMB = [math]::Round(($orphanCodes | Measure-Object WorkingSet64 -Sum).Sum / 1MB, 1)

Write-Host "`nCode processes: $($codeProcs.Count) total, $orphanCodeCount orphaned, $liveCodes live" -ForegroundColor White

if ($orphanCodeCount -gt 0) {
    if ($DryRun) {
        Write-Host "  Would kill $orphanCodeCount Code processes (~${orphanCodeMemMB} MB)" -ForegroundColor Yellow
    }
    else {
        $orphanCodes | Stop-Process -Force -ErrorAction SilentlyContinue
        Write-Host "  Killed $orphanCodeCount Code processes (~${orphanCodeMemMB} MB freed)" -ForegroundColor Green
    }
}
else {
    Write-Host "  No orphans found." -ForegroundColor DarkGray
}

# --- Summary ---
$totalKilled = $psCount + $orphanConhostCount + $orphanPythonCount + $allSecexprOrphanCount + $orphanCodeCount
$totalMemMB = [math]::Round($psMemMB + $orphanConhostMemMB + $orphanPythonMemMB + $allSecexprMemMB + $orphanCodeMemMB, 1)

Write-Host "`n--- Summary ---" -ForegroundColor Cyan
if ($DryRun) {
    Write-Host "Would kill $totalKilled processes (~${totalMemMB} MB)" -ForegroundColor Yellow
}
else {
    Write-Host "Killed $totalKilled processes (~${totalMemMB} MB freed)" -ForegroundColor Green
}
Write-Host ""
