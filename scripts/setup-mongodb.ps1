$ErrorActionPreference = 'Stop'
$nexusRoot = Split-Path -Parent $PSScriptRoot
$nexusArchive = Join-Path $nexusRoot 'tmp\mongodb.zip'
$nexusDestination = Join-Path $nexusRoot 'tmp\mongodb-runtime'
New-Item -ItemType Directory -Force -Path (Join-Path $nexusRoot 'tmp') | Out-Null
Invoke-WebRequest 'https://fastdl.mongodb.org/windows/mongodb-windows-x86_64-8.0.32.zip' -OutFile $nexusArchive
if ((Get-FileHash -LiteralPath $nexusArchive -Algorithm SHA256).Hash.ToLower() -ne '5a0675fdec49b544cd5d374ad50a9a594cf5b3278b5ace658aa51cbb4df17177') {
    throw 'MongoDB archive checksum mismatch.'
}
Expand-Archive -LiteralPath $nexusArchive -DestinationPath $nexusDestination -Force
& (Join-Path $PSScriptRoot 'start-mongodb.ps1')
