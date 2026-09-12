$ErrorActionPreference = 'Stop'
$nexusRoot = Split-Path -Parent $PSScriptRoot
& (Join-Path $PSScriptRoot 'start-mongodb.ps1')
$nexusLogs = Join-Path $env:LOCALAPPDATA 'Nexus\logs'
New-Item -ItemType Directory -Force -Path $nexusLogs | Out-Null
if (-not (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue)) {
    Start-Process -FilePath (Join-Path $nexusRoot '.venv\Scripts\python.exe') -WindowStyle Hidden -WorkingDirectory $nexusRoot -ArgumentList @('-m','uvicorn','app.main:app','--app-dir','backend','--host','127.0.0.1','--port','8000') -RedirectStandardOutput (Join-Path $nexusLogs 'backend.out.log') -RedirectStandardError (Join-Path $nexusLogs 'backend.err.log')
}
if (-not (Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue)) {
    $nexusNode = (Get-Command node.exe).Source
    Start-Process -FilePath $nexusNode -WindowStyle Hidden -WorkingDirectory (Join-Path $nexusRoot 'frontend') -ArgumentList @('node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','5173','--strictPort') -RedirectStandardOutput (Join-Path $nexusLogs 'frontend.out.log') -RedirectStandardError (Join-Path $nexusLogs 'frontend.err.log')
}
Write-Output 'NEXUS is starting at http://127.0.0.1:5173. Logs: %LOCALAPPDATA%\Nexus\logs'
