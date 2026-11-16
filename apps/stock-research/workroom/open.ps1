$ErrorActionPreference = 'Stop'
$statePath = Join-Path $PSScriptRoot '..\private\workroom-access.json'
if (-not (Test-Path -LiteralPath $statePath)) { throw '먼저 workroom\start.ps1을 실행하세요.' }
$state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
$uri = [Uri]$state.url
if ($uri.Scheme -ne 'http' -or $uri.Host -ne '127.0.0.1' -or $uri.AbsolutePath -ne '/') { throw '잘못된 로컬 작업실 주소입니다.' }
Add-Type -AssemblyName System.Security
try {
 $keyBytes = [System.Security.Cryptography.ProtectedData]::Unprotect([Convert]::FromBase64String($state.encrypted_key), $null, [System.Security.Cryptography.DataProtectionScope]::CurrentUser)
 $launchKey = [System.Text.Encoding]::UTF8.GetString($keyBytes)
 Start-Process -FilePath ($state.url + '/unlock#key=' + [Uri]::EscapeDataString($launchKey))
} catch { throw '이 Windows 계정의 작업실 접속키를 열지 못했습니다. start.ps1로 다시 시작하세요.' }
finally { if ($keyBytes) { [Array]::Clear($keyBytes, 0, $keyBytes.Length) }; $launchKey = $null }
