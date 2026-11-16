$ErrorActionPreference = 'Stop'
$statePath = Join-Path $PSScriptRoot '..\private\workroom-access.json'
if (-not (Test-Path -LiteralPath $statePath)) { Write-Host '실행 기록이 없습니다.'; return }
$state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
$taskServer = (Join-Path $PSScriptRoot 'server.py')
$taskProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $([int]$state.pid)"
if ($taskProcess -and $taskProcess.Name -match '^python(w)?\.exe$' -and $taskProcess.CommandLine.Contains($taskServer)) {
 Stop-Process -Id ([int]$state.pid)
 Remove-Item -LiteralPath $statePath
 Write-Host '개인 작업실 서버를 종료했습니다.'
} elseif (-not $taskProcess) {
 Remove-Item -LiteralPath $statePath
 Write-Host '서버가 이미 종료됐습니다. 이전 실행 기록만 정리했습니다.'
} else { throw '기록된 프로세스가 이 작업실 서버인지 확인하지 못해 종료하지 않았습니다.' }
