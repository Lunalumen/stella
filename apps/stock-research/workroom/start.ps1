param([ValidateRange(1024,65535)][int]$Port = 8767, [switch]$NoOpen)
$ErrorActionPreference = 'Stop'
$taskPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) { $taskPython = 'python' }
$statePath = Join-Path $PSScriptRoot '..\private\workroom-access.json'
$taskServer = Join-Path $PSScriptRoot 'server.py'
if (Test-Path -LiteralPath $statePath) {
 $previous = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
 $existing = Get-CimInstance Win32_Process -Filter "ProcessId = $([int]$previous.pid)"
 if ($existing -and $existing.Name -match '^python(w)?\.exe$' -and $existing.CommandLine.Contains($taskServer)) {
  if ([Uri]$previous.url -and ([Uri]$previous.url).Port -ne $Port) { throw '다른 포트의 작업실이 실행 중입니다. stop.ps1로 종료한 후 다시 시작하세요.' }
  Write-Host "MOON LAB private: http://127.0.0.1:$Port/ (already running)"
  if (-not $NoOpen) { & (Join-Path $PSScriptRoot 'open.ps1') }
  return
 }
}
$logPath = Join-Path $PSScriptRoot '..\private\verification\workroom-private.log'
$errorPath = Join-Path $PSScriptRoot '..\private\verification\workroom-private-error.log'
New-Item -ItemType Directory -Force -Path (Split-Path $logPath) | Out-Null
$taskProcess = Start-Process -FilePath $taskPython -ArgumentList @('-u', ('"' + $taskServer + '"'), '--port', $Port) -WindowStyle Hidden -RedirectStandardOutput $logPath -RedirectStandardError $errorPath -PassThru
for ($attempt=0; $attempt -lt 40; $attempt++) {
 Start-Sleep -Milliseconds 150
 if ($taskProcess.HasExited) { throw '서버가 시작되지 않았습니다. 사용 중인 포트나 private/verification/workroom-private-error.log를 확인하세요.' }
 if (Test-Path -LiteralPath $statePath) {
  $ready = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
  if ($ready.pid -eq $taskProcess.Id) {
   Write-Host "MOON LAB private: http://127.0.0.1:$Port/ (PID $($taskProcess.Id))"
   if (-not $NoOpen) { & (Join-Path $PSScriptRoot 'open.ps1') }
   return
  }
 }
}
throw '서버 준비 확인 시간이 초과됐습니다. 서버 로그를 확인하세요.'
