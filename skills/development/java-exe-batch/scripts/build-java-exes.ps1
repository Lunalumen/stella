[CmdletBinding()]
param(
 [Parameter(Mandatory)][string]$SourceDirectory,
 [Parameter(Mandatory)][string[]]$Names,
 [Parameter(Mandatory)][AllowEmptyString()][string]$PackageName,
 [Parameter(Mandatory)][string]$JdkHome,
 [Parameter(Mandatory)][string]$JsmoothHome,
 [Parameter(Mandatory)][string]$OutputDirectory,
 [Parameter(Mandatory)][string]$BuildDirectory,
 [string]$MinimumVersion='1.8',
 [string]$SourceEncoding='UTF-8',
 [int]$ExeCodePage=949,
 [ValidateRange(1,120)][int]$TimeoutSeconds=10,
 [switch]$VerifyConsole
)
$ErrorActionPreference='Stop'
$java=Join-Path $JdkHome 'bin\java.exe'
$javac=Join-Path $JdkHome 'bin\javac.exe'
$jar=Join-Path $JdkHome 'bin\jar.exe'
$compiler=Join-Path $JsmoothHome 'jsmoothcmd.exe'
foreach($tool in @($java,$javac,$jar,$compiler)){if(!(Test-Path -LiteralPath $tool -PathType Leaf)){throw "Missing tool: $tool"}}
if($Names.Count -ne @($Names | Select-Object -Unique).Count){throw 'Duplicate names'}
foreach($name in $Names){
 if($name -notmatch '^[A-Za-z_$][A-Za-z0-9_$]*$'){throw "Invalid class name: $name"}
 if(!(Test-Path -LiteralPath (Join-Path $SourceDirectory "$name.java"))){throw "Missing source: $name"}
 foreach($ext in @('jar','exe','jsmooth')){if(Test-Path -LiteralPath (Join-Path $OutputDirectory "$name.$ext")){throw "Output exists: $name.$ext"}}
}
if(Test-Path -LiteralPath (Join-Path $OutputDirectory 'verification.json')){throw 'Report exists'}
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
New-Item -ItemType Directory -Path $BuildDirectory -Force | Out-Null
$OutputDirectory=(Resolve-Path -LiteralPath $OutputDirectory).Path
$BuildDirectory=(Resolve-Path -LiteralPath $BuildDirectory).Path
function Invoke-Console([string]$file,[string[]]$arguments,[Text.Encoding]$encoding){
 $s=[Diagnostics.ProcessStartInfo]::new()
 $s.FileName=$file
 $s.WorkingDirectory=$OutputDirectory
 $s.UseShellExecute=$false
 $s.CreateNoWindow=$true
 $s.RedirectStandardInput=$true
 $s.RedirectStandardOutput=$true
 $s.RedirectStandardError=$true
 $s.StandardOutputEncoding=$encoding
 $s.StandardErrorEncoding=$encoding
 foreach($a in $arguments){$s.ArgumentList.Add($a)}
 $p=[Diagnostics.Process]::Start($s)
 try{
  $outTask=$p.StandardOutput.ReadToEndAsync()
  $errTask=$p.StandardError.ReadToEndAsync()
  $p.StandardInput.WriteLine()
  $p.StandardInput.Close()
  if(!$p.WaitForExit($TimeoutSeconds*1000)){ $p.Kill($true); throw "Timed out: $file" }
  $stdout=$outTask.GetAwaiter().GetResult()
  $stderr=$errTask.GetAwaiter().GetResult()
  if($p.ExitCode -ne 0 -or $stderr){throw "Execution failed: $file code=$($p.ExitCode) $stderr"}
  return ($stdout -replace "`r`n","`n").Trim()
 }finally{$p.Dispose()}
}
$oldHome=$env:JAVA_HOME
$oldPath=$env:Path
$report=@()
try{
 $env:JAVA_HOME=$JdkHome
 $env:Path=(Join-Path $JdkHome 'bin')+';'+$oldPath
 foreach($name in $Names){
  $classes=Join-Path $BuildDirectory ($name+'-'+[guid]::NewGuid().ToString('N'))
  New-Item -ItemType Directory -Path $classes | Out-Null
  $main=if($PackageName){"$PackageName.$name"}else{$name}
  & $javac -encoding $SourceEncoding -d $classes (Join-Path $SourceDirectory "$name.java")
  if($LASTEXITCODE -ne 0){throw "javac failed: $name"}
  & $jar cfe (Join-Path $OutputDirectory "$name.jar") $main -C $classes .
  if($LASTEXITCODE -ne 0){throw "jar failed: $name"}
  $xml=[xml]'<jsmoothproject><JVMSearchPath>javahome</JVMSearchPath><JVMSearchPath>registry</JVMSearchPath><JVMSearchPath>exepath</JVMSearchPath><embeddedJar>true</embeddedJar><executableName/><jarLocation/><mainClassName/><minimumVersion/><skeletonName>Console Wrapper</skeletonName><skeletonProperties><key>PressKey</key><value>1</value></skeletonProperties></jsmoothproject>'
  $xml.jsmoothproject.executableName="$name.exe"
  $xml.jsmoothproject.jarLocation="$name.jar"
  $xml.jsmoothproject.mainClassName=$main
  $xml.jsmoothproject.minimumVersion=$MinimumVersion
  $config=Join-Path $OutputDirectory "$name.jsmooth"
  $xml.Save($config)
  $log=& $compiler $config 2>&1
  if($LASTEXITCODE -ne 0 -or !(Test-Path -LiteralPath (Join-Path $OutputDirectory "$name.exe"))){throw "JSmooth failed: $name $log"}
  $verified=$false
  if($VerifyConsole){
   $expected=Invoke-Console $java @('-Dfile.encoding=UTF-8','-jar',(Join-Path $OutputDirectory "$name.jar")) ([Text.Encoding]::UTF8)
   $actual=Invoke-Console (Join-Path $OutputDirectory "$name.exe") @() ([Text.Encoding]::GetEncoding($ExeCodePage))
   if(!$expected -or !($actual -eq $expected -or $actual.StartsWith($expected+"`n"))){throw "EXE output mismatch: $name"}
   $verified=$true
  }
  $report += [PSCustomObject]@{Name=$name;MainClass=$main;ConsoleVerified=$verified;ExeSHA256=(Get-FileHash -LiteralPath (Join-Path $OutputDirectory "$name.exe")).Hash}
  Write-Output "$name built; console verified=$verified"
 }
 $report | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $OutputDirectory 'verification.json') -Encoding utf8
}finally{$env:JAVA_HOME=$oldHome; $env:Path=$oldPath}
