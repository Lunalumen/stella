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
 [hashtable]$DefaultArguments=@{},
 [string]$ZipPath,
 [int]$ExeCodePage=949,
 [ValidateRange(1,120)][int]$TimeoutSeconds=10,
 [switch]$VerifyConsole
)
$ErrorActionPreference='Stop'
if($ZipPath -and (Test-Path -LiteralPath $ZipPath)){throw 'ZIP already exists'}
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
foreach($key in $DefaultArguments.Keys){if($key -notin $Names){throw "Arguments for unknown example: $key"}}
if(Test-Path -LiteralPath (Join-Path $OutputDirectory 'verification.json')){throw 'Report exists'}
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
New-Item -ItemType Directory -Path $BuildDirectory -Force | Out-Null
$OutputDirectory=(Resolve-Path -LiteralPath $OutputDirectory).Path
$BuildDirectory=(Resolve-Path -LiteralPath $BuildDirectory).Path
function Invoke-Console([string]$file,[string[]]$arguments,[Text.Encoding]$encoding){
 $s=[Diagnostics.ProcessStartInfo]::new()
 $s.FileName=$file
 $s.WorkingDirectory=$BuildDirectory
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
function Test-PeAlignment([string]$file){
 $bytes=[IO.File]::ReadAllBytes($file)
 if($bytes.Length -lt 64 -or $bytes[0] -ne 77 -or $bytes[1] -ne 90){return $false}
 $pe=[BitConverter]::ToInt32($bytes,60)
 if($pe -lt 0 -or $pe+60 -gt $bytes.Length -or [BitConverter]::ToUInt32($bytes,$pe) -ne 17744){return $false}
 $count=[BitConverter]::ToUInt16($bytes,$pe+6)
 $optionalSize=[BitConverter]::ToUInt16($bytes,$pe+20)
 $alignment=[BitConverter]::ToUInt32($bytes,$pe+24+32)
 if(!$alignment){return $false}
 for($i=0;$i -lt $count;$i++){
  $offset=$pe+24+$optionalSize+$i*40
  if($offset+40 -gt $bytes.Length -or [BitConverter]::ToUInt32($bytes,$offset+12) % $alignment){return $false}
 }
 return $true
}
function Build-Wrapper([string]$config,[string]$exe){
 $log=& $compiler $config 2>&1
 if($LASTEXITCODE -ne 0 -or !(Test-Path -LiteralPath $exe) -or ($log | Out-String) -match 'Exception|(?im)^Error:'){throw "JSmooth failed: $config $log"}
}
$oldHome=$env:JAVA_HOME
$oldPath=$env:Path
$report=@()
$expectedOutputs=@{}
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
  $appArgs=@()
  if($DefaultArguments.ContainsKey($name)){
   $appArgs=@($DefaultArguments[$name])
   foreach($a in $appArgs){if([string]$a -match '[\s"\\]'){throw "DefaultArguments supports simple unquoted tokens only: $name"}}
   $argumentsNode=$xml.CreateElement('arguments')
   $argumentsNode.InnerText=$appArgs -join ' '
   $xml.jsmoothproject.AppendChild($argumentsNode) | Out-Null
  }
  $config=Join-Path $OutputDirectory "$name.jsmooth"
  $xml.Save($config)
  $exe=Join-Path $OutputDirectory "$name.exe"
  Build-Wrapper $config $exe
  $storedJar=$false
  if(!(Test-PeAlignment $exe)){
   # JSmooth can misalign a PE section for some embedded JAR sizes.
   # Repackage the same classes without ZIP compression; do not patch PE addresses.
   & $jar c0fe (Join-Path $OutputDirectory "$name.jar") $main -C $classes .
   if($LASTEXITCODE -ne 0){throw "Stored JAR failed: $name"}
   Remove-Item -LiteralPath $exe
   Build-Wrapper $config $exe
   if(!(Test-PeAlignment $exe)){throw "Invalid PE section alignment after repackaging: $name"}
   $storedJar=$true
  }
  $verified=$false
  if($VerifyConsole){
   $expected=Invoke-Console $java (@('-Dfile.encoding=UTF-8','-jar',(Join-Path $OutputDirectory "$name.jar"))+$appArgs) ([Text.Encoding]::UTF8)
   $actual=Invoke-Console (Join-Path $OutputDirectory "$name.exe") @() ([Text.Encoding]::GetEncoding($ExeCodePage))
   if(!$expected -or !($actual -eq $expected -or $actual.StartsWith($expected+"`n"))){throw "EXE output mismatch: $name"}
   $verified=$true
   $expectedOutputs[$name]=$expected
  }
  $report += [PSCustomObject]@{Name=$name;MainClass=$main;ConsoleVerified=$verified;PeAlignmentVerified=$true;StoredJarFallback=$storedJar;ZipExtractedVerified=$false;ExeSHA256=(Get-FileHash -LiteralPath $exe).Hash}
  Write-Output "$name built; console verified=$verified"
 }
 if($ZipPath){
  $zipParent=Split-Path -Parent ([IO.Path]::GetFullPath($ZipPath))
  New-Item -ItemType Directory -Path $zipParent -Force | Out-Null
  $zip=[IO.Compression.ZipFile]::Open($ZipPath,[IO.Compression.ZipArchiveMode]::Create)
  try{foreach($name in $Names){[IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip,(Join-Path $OutputDirectory "$name.exe"),"$name.exe") | Out-Null}}finally{$zip.Dispose()}
  $unpacked=Join-Path $BuildDirectory ('zip-check-'+[guid]::NewGuid().ToString('N'))
  [IO.Compression.ZipFile]::ExtractToDirectory($ZipPath,$unpacked)
  foreach($item in $report){
   $exe=Join-Path $unpacked ($item.Name+'.exe')
   if((Get-FileHash -LiteralPath $exe).Hash -ne $item.ExeSHA256){throw "ZIP hash mismatch: $($item.Name)"}
   if($VerifyConsole){
    $actual=Invoke-Console $exe @() ([Text.Encoding]::GetEncoding($ExeCodePage))
    $expected=$expectedOutputs[$item.Name]
    if(!($actual -eq $expected -or $actual.StartsWith($expected+"`n"))){throw "ZIP execution mismatch: $($item.Name)"}
    $item.ZipExtractedVerified=$true
   }
  }
 }
 $report | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $OutputDirectory 'verification.json') -Encoding utf8
}finally{$env:JAVA_HOME=$oldHome; $env:Path=$oldPath}
