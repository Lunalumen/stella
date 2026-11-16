param([switch]$NoBrowser)
$ErrorActionPreference='Stop'
$studyPython=Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
if(-not(Test-Path -LiteralPath $studyPython)){$studyPython=(Get-Command python -ErrorAction Stop).Source}
$studyRoot=$PSScriptRoot
& $studyPython -B -X utf8 (Join-Path $studyRoot 'setup_demo.py')
if($LASTEXITCODE -ne 0){throw 'Demo registry setup failed.'}
$studyState=Join-Path $env:LOCALAPPDATA 'MyeongwolStudy'
New-Item -ItemType Directory -Path $studyState -Force | Out-Null
$studySid=[System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
& icacls.exe $studyState /inheritance:r /grant:r ('*'+$studySid+':(OI)(CI)F') '*S-1-5-18:(OI)(CI)F' | Out-Null
if($LASTEXITCODE -ne 0){throw '개인용 접근 폴더를 보호하지 못했습니다.'}
function Get-StudyHealth {
    try {Invoke-RestMethod 'http://127.0.0.1:8765/health' -TimeoutSec 2} catch {$null}
}
$studyHealth=Get-StudyHealth
if(-not($studyHealth -and $studyHealth.app -eq 'myeongwol-study' -and $studyHealth.private -eq $true)){
    $studyScript=Join-Path $studyRoot 'server.py'
    Start-Process -FilePath $studyPython -ArgumentList @('-X','utf8',('"'+$studyScript+'"'),'--port','8765') -WorkingDirectory $studyRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $studyState 'server.stdout.log') -RedirectStandardError (Join-Path $studyState 'server.stderr.log') | Out-Null
    for($studyTry=0;$studyTry -lt 25;$studyTry++){
        Start-Sleep -Milliseconds 200
        $studyHealth=Get-StudyHealth
        if($studyHealth -and $studyHealth.app -eq 'myeongwol-study' -and $studyHealth.private -eq $true){break}
    }
}
if(-not($studyHealth -and $studyHealth.app -eq 'myeongwol-study' -and $studyHealth.private -eq $true)){throw '개인용 서버가 시작되지 않았습니다. 다른 앱이 8765 포트를 사용하는지 확인하세요.'}
$studyHelper=Join-Path $studyRoot 'private_access.py'
$studyUrl=& $studyPython -X utf8 $studyHelper
if($LASTEXITCODE -ne 0 -or -not($studyUrl -match '^http://127\.0\.0\.1:8765/unlock\?ticket=')){throw '개인용 열기 링크를 생성하지 못했습니다.'}
if($NoBrowser){Write-Output '개인용 서버 실행 완료.'}else{Start-Process $studyUrl | Out-Null}
