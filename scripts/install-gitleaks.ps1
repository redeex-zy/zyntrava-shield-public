$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$toolsDirectory = Join-Path $projectRoot '.tools'
New-Item -ItemType Directory -Path $toolsDirectory -Force | Out-Null
$archivePath = Join-Path $toolsDirectory 'gitleaks-8.30.1.zip'
Invoke-WebRequest -Uri 'https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/gitleaks_8.30.1_windows_x64.zip' -OutFile $archivePath
$expectedHash = 'd29144deff3a68aa93ced33dddf84b7fdc26070add4aa0f4513094c8332afc4e'
$actualHash = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actualHash -ne $expectedHash) { throw 'Gitleaks archive checksum mismatch; refusing installation.' }
Expand-Archive -LiteralPath $archivePath -DestinationPath (Join-Path $toolsDirectory 'gitleaks') -Force
Write-Output 'Verified Gitleaks 8.30.1 installed under .tools/gitleaks.'
