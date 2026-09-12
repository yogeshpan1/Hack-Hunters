$ErrorActionPreference = 'Stop'
$nexusRoot = Split-Path -Parent $PSScriptRoot
$nexusPython = [IO.Path]::GetFullPath((Join-Path $nexusRoot '.venv\Scripts\python.exe'))
$nexusListeners = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
foreach ($nexusListener in $nexusListeners) {
    $nexusProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $($nexusListener.OwningProcess)"
    $nexusParent = Get-CimInstance Win32_Process -Filter "ProcessId = $($nexusProcess.ParentProcessId)"
    $nexusOwned = $nexusProcess.ExecutablePath -eq $nexusPython -or ($nexusParent.ExecutablePath -eq $nexusPython -and $nexusParent.CommandLine -match 'uvicorn\s+app.main:app')
    if (-not $nexusOwned -or $nexusProcess.CommandLine -notmatch 'uvicorn\s+app.main:app') {
        throw 'Port 8000 is owned by another application. It was not stopped.'
    }
    Stop-Process -Id $nexusProcess.ProcessId
}
& (Join-Path $PSScriptRoot 'start-nexus.ps1')
