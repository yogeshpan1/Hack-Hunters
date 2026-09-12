$ErrorActionPreference = 'Stop'
$nexusRoot = Split-Path -Parent $PSScriptRoot
$nexusDataRoot = Join-Path $env:LOCALAPPDATA 'Nexus\MongoDB'
$nexusRuntime = Join-Path $nexusRoot 'tmp\mongodb-runtime\mongodb-win32-x86_64-windows-8.0.32\bin\mongod.exe'
if (-not (Test-Path -LiteralPath $nexusRuntime)) {
    throw 'MongoDB runtime is missing. Run scripts/setup-mongodb.ps1 first.'
}
New-Item -ItemType Directory -Force -Path $nexusDataRoot | Out-Null
$nexusPort = Get-NetTCPConnection -LocalPort 27017 -State Listen -ErrorAction SilentlyContinue
if (-not $nexusPort) {
    Start-Process -FilePath $nexusRuntime -WindowStyle Hidden -ArgumentList @('--dbpath', ('"' + $nexusDataRoot + '"'), '--replSet', 'nexus-rs', '--bind_ip', '127.0.0.1', '--port', '27017', '--logpath', ('"' + (Join-Path $nexusDataRoot 'mongod.log') + '"'), '--logappend')
}
& (Join-Path $nexusRoot '.venv\Scripts\python.exe') (Join-Path $PSScriptRoot 'initialize-mongodb.py')
if ($LASTEXITCODE -ne 0) { throw 'MongoDB initialization failed.' }
