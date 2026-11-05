[CmdletBinding()]
param(
 [Parameter(Mandatory)][string]$JarPath,
 [Parameter(Mandatory)][string]$OutputPath,
 [Parameter(Mandatory)][string]$BuildDirectory,
 [string]$AppName,
 [string[]]$DefaultArguments=@(),
 [string]$ExpectedOutputFile,
 [string]$CscPath="$env:WINDIR\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
)
$ErrorActionPreference='Stop'
$template=Join-Path $PSScriptRoot '..\assets\ConsoleLauncher.cs'
foreach($file in @($JarPath,$template,$CscPath)){if(!(Test-Path -LiteralPath $file -PathType Leaf)){throw "Missing file: $file"}}
if(Test-Path -LiteralPath $OutputPath){throw 'Output exists; preserved'}
if($ExpectedOutputFile -and !(Test-Path -LiteralPath $ExpectedOutputFile)){throw 'Expected output file missing'}
$OutputPath=[IO.Path]::GetFullPath($OutputPath)
if([IO.Path]::GetExtension($OutputPath) -ne '.exe'){throw 'Output must be an EXE'}
if(!$AppName){$AppName=[IO.Path]::GetFileNameWithoutExtension($OutputPath)}
New-Item -ItemType Directory -Path (Split-Path -Parent $OutputPath),$BuildDirectory -Force | Out-Null
function CsString([string]$value){'"'+$value.Replace('\','\\').Replace('"','\"').Replace("`r",'\r').Replace("`n",'\n')+'"'}
$config=Join-Path $BuildDirectory ('AppConfig-'+[guid]::NewGuid().ToString('N')+'.cs')
$argsLiteral=@($DefaultArguments | ForEach-Object {CsString $_}) -join ','
('internal static class AppConfig { public const string Name = '+(CsString $AppName)+'; public static readonly string[] Arguments = new string[] { '+$argsLiteral+' }; }') | Set-Content -LiteralPath $config -Encoding utf8
$jar=(Resolve-Path -LiteralPath $JarPath).Path
& $CscPath /nologo /target:exe /platform:anycpu /optimize+ "/out:$OutputPath" /reference:System.dll /reference:System.Core.dll "/resource:$jar,application.jar" $template $config
if($LASTEXITCODE -ne 0){throw 'Console EXE compilation failed'}
$verified=$false
if($ExpectedOutputFile){
 $result=[IO.Path]::GetFullPath((Join-Path $BuildDirectory ('output-'+[guid]::NewGuid().ToString('N')+'.txt')))
 $info=[Diagnostics.ProcessStartInfo]::new()
 $info.FileName=$OutputPath;$info.UseShellExecute=$false;$info.CreateNoWindow=$true
 $info.ArgumentList.Add('--verify-output');$info.ArgumentList.Add($result)
 $process=[Diagnostics.Process]::Start($info)
 try{
  if(!$process.WaitForExit(25000)){$process.Kill($true);throw 'Verification timed out'}
  if($process.ExitCode -ne 0){throw "Runner failed: exit code $($process.ExitCode)"}
 }finally{$process.Dispose()}
 $expected=([IO.File]::ReadAllText($ExpectedOutputFile) -replace "`r`n","`n").Trim()
 $actual=([IO.File]::ReadAllText($result) -replace "`r`n","`n").Trim()
 if($actual -cne $expected){throw 'Output differs from expected Java result'}
 $verified=$true
}
[PSCustomObject]@{EXE=$OutputPath;SHA256=(Get-FileHash -LiteralPath $OutputPath).Hash;RunnerOutputVerified=$verified;VisibleWindowVerified=$false}
