param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Arguments)
$ErrorActionPreference = 'Stop'
$taskPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) { $taskPython = 'python' }
Push-Location $PSScriptRoot
try { & $taskPython -X utf8 -m stock_agent @Arguments; exit $LASTEXITCODE }
finally { Pop-Location }
