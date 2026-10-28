param (
  [Parameter(Mandatory=$true)]
  [string]$InstallDir,
  [switch]$Force
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$PSNativeCommandUseErrorActionPreference = $true

$GitRepo = 'msys2/msys2-installer'
$BinDirectories = @('.', 'usr\bin', 'ucrt64\bin', 'mingw64\bin', 'clang64\bin')
$InitPackages = @('unzip') # we install these packages after init 1) to make sure it works and 2) to run msys2 init script

function Test-ValidInstall() {
  -not ((Test-Path ($binDirectories | ForEach-Object { "$InstallDir\$_" })) -contains $false)
}

function Get-DownloadUrl($Version) {
  $arch = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture
  if ($arch -eq 'Arm64') {
    [Console]::Error.WriteLine("FATAL: msys2 does not expose base archive for ARM")
    exit 1
  }

  $releases = `
    Invoke-WebRequest -UseBasicParsing "https://api.github.com/repos/$GitRepo/releases" |
    ConvertFrom-Json
  $versionTag = $releases |
    Select-Object -ExpandProperty tag_name |
    Where-Object { $_ -match '^\d' } |
    Sort-Object -Descending |
    Select-Object -First 1

  return "https://github.com/$GitRepo/releases/download/$versionTag/msys2-base-x86_64-$($versionTag -replace '-', '').sfx.exe"
}

$alreadyInstalled = (-not $Force) -and (Test-Path $InstallDir) -and (Test-ValidInstall)

if (-not $alreadyInstalled) {
  if (Test-Path $InstallDir) {
    Remove-Item -Force -Recurse $InstallDir 
  }

  $url = Get-DownloadUrl 
  [Console]::Error.WriteLine("DEBUG: url=$url")

  [Console]::Error.WriteLine('INFO: downloading self-extracting msys2-installer')
  $tmp = New-TemporaryFile
  Move-Item $tmp "$tmp.exe"
  $tmp = "$tmp.exe"
  Invoke-WebRequest -UseBasicParsing "$url" -OutFile "$tmp"

  [Console]::Error.WriteLine('INFO: extracting msys2')
  $tmpDir = [System.IO.Path]::GetFullPath((Join-Path $env:TEMP 'msys2'))
  New-Item "$tmpDir" -Type Directory -Force | Out-Null
  Start-Process -Wait -FilePath "$tmp" -ArgumentList @("-y", "-o$tmpDir")
  $status = $?
  if ($status) {
    $installation = Join-Path $tmpDir 'msys64'
    if (-not (Test-Path $installation)) {
      [Console]::Error.WriteLine('FATAL: expected msys64 subdir from installation')
      exit 1
    }
    Move-Item $installation $InstallDir -Force
  }
  Remove-Item "$tmp", "$tmpDir" -Force -Recurse
  if (-not $status) {
    exit $status
  }

  if (-not (Test-ValidInstall)) {
    [Console]::Error.WriteLine('WARN: not all expected binary dirs exist')
  }

  # have to run shell for initial setup
  [Console]::Error.WriteLine('INFO: running initial setup')
  $shell = Join-Path $InstallDir 'msys2_shell.cmd'
  if (-not (Test-Path $shell)) {
    [Console]::Error.WriteLine('FATAL: expected msys2_shell.cmd')
    exit 1
  }
  Start-Process -Wait -FilePath "$shell" -ArgumentList @("-c", "exit")
}

# update msys2 with pacman
[Console]::Error.WriteLine('INFO: updating with pacman')
$pacman = Join-Path $InstallDir 'usr\bin\pacman.exe'
if (-not (Test-Path $pacman)) {
  [Console]::Error.WriteLine('FATAL: expected pacman to be available!')
  exit 1
}
& "$pacman" -Suy --noconfirm

return $BinDirectories
