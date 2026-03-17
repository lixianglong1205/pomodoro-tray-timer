param(
  [string]$OutputDir = 'dist',
  [string]$AppName = 'pomodoro-tray-timer'
)

$ErrorActionPreference = 'Stop'

function Assert-Command {
  param([Parameter(Mandatory = $true)][string]$Name)

  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw ("Command not found: {0}. Please install it and ensure it is in PATH." -f $Name)
  }
}

function Test-AsciiPath {
  param([Parameter(Mandatory = $true)][string]$Path)
  return ($Path -match '^[\x00-\x7F]+$')
}

function Copy-Tree {
  param(
    [Parameter(Mandatory = $true)][string]$Src,
    [Parameter(Mandatory = $true)][string]$Dst
  )

  Assert-Command robocopy
  if (-not (Test-Path $Dst)) { New-Item -ItemType Directory -Path $Dst | Out-Null }

  $excludeDirs = @('.git', '.venv', 'dist', 'dist-installer', '__pycache__', '.cursor')
  $xdArgs = @()
  foreach ($d in $excludeDirs) { $xdArgs += @('/XD', (Join-Path $Src $d)) }

  # robocopy: return codes 0-7 are success conditions; normalize to success
  robocopy $Src $Dst /MIR @xdArgs /NFL /NDL /NJH /NJS /NP | Out-Host
  if ($LASTEXITCODE -gt 7) {
    throw ("robocopy failed with exit code {0}" -f $LASTEXITCODE)
  }
  $global:LASTEXITCODE = 0
}

function Remove-TreeSafe {
  param([Parameter(Mandatory = $true)][string]$Path)

  if (-not (Test-Path $Path)) { return }

  $max = 5
  for ($i = 1; $i -le $max; $i++) {
    try {
      Remove-Item -Recurse -Force $Path -ErrorAction Stop
      return
    } catch {
      if ($i -lt $max) { Start-Sleep -Milliseconds (400 * $i) }
    }
  }

  # If still locked (e.g. qwindows.dll in use), keep it as a backup.
  $backup = ("{0}.bak-{1}" -f $Path, (Get-Date -Format 'yyyyMMdd-HHmmss'))
  try {
    Rename-Item -Path $Path -NewName (Split-Path -Leaf $backup) -ErrorAction Stop
  } catch {
    throw ("Failed to remove or backup existing directory: {0}. Close running app/explorer locks and retry." -f $Path)
  }
}

Assert-Command uv

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $repoRoot
$buildRoot = $repoRoot

if (-not (Test-AsciiPath $repoRoot)) {
  $buildRoot = Join-Path $env:TEMP 'pomodoro-tray-timer-build'
  Write-Host ("Repo path contains non-ASCII chars, building in temp dir: {0}" -f $buildRoot)
  Copy-Tree -Src $repoRoot -Dst $buildRoot
}

Set-Location $buildRoot

uv sync --all-groups

$nuitkaArgs = @(
  '-m', 'nuitka',
  'main.py',
  '--standalone',
  '--enable-plugins=pyside6',
  '--assume-yes-for-downloads',
  '--disable-dll-dependency-cache',
  '--windows-console-mode=disable',
  "--output-dir=$OutputDir",
  "--output-filename=$AppName"
)

uv run python @nuitkaArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# Normalize output folder name to dist\<AppName>\...
$expected = Join-Path $OutputDir $AppName
$defaultDist = Join-Path $OutputDir 'main.dist'
if (Test-Path $defaultDist) {
  Remove-TreeSafe -Path $expected
  Rename-Item -Path $defaultDist -NewName $AppName
}

if ($buildRoot -ne $repoRoot) {
  Set-Location $repoRoot
  Remove-TreeSafe -Path $expected
  Copy-Tree -Src (Join-Path $buildRoot $expected) -Dst $expected
}

Write-Host ("Build done: {0}\{1}\" -f $OutputDir, $AppName)

