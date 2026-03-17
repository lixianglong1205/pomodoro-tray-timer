param(
  [string]$IssPath = 'installer\pomodoro-tray-timer.iss'
)

$ErrorActionPreference = 'Stop'

function Find-ISCC {
  $candidates = @(
    "${env:LOCALAPPDATA}\Programs\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
  )
  foreach ($p in $candidates) {
    if ($p -and (Test-Path $p)) { return $p }
  }

  $cmd = Get-Command 'ISCC.exe' -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Source }

  return $null
}

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $repoRoot
Set-Location $repoRoot

$iscc = Find-ISCC
if (-not $iscc) {
  throw 'ISCC.exe not found. Please install Inno Setup 6 or add ISCC.exe to PATH.'
}

if (-not (Test-Path $IssPath)) {
  throw ("ISS script not found: {0}" -f $IssPath)
}

& $iscc $IssPath

Write-Host 'Installer build done: dist-installer\pomodoro-tray-timer-setup.exe'

