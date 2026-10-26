# Windows PowerShell bootstrap.

$ErrorActionPreference = 'Stop'

$VULPIX_REPO = 'uss-stargazer/vulpix'
$VULPIX_BRANCH = 'main'
$VULPIX_REPO_RAW = "https://raw.githubusercontent.com/$VULPIX_REPO/$VULPIX_BRANCH"

if ($PSVersionTable.PSEdition -ne 'Desktop') {
  Write-Error 'Only for execution by Windows PowerShell on a Windows machine'
  exit 1
}

function Test-Admin() {
  ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()). `
    IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Test-Command([string]$Cmd) {
  if ((Get-Command $Cmd -ErrorAction SilentlyContinue) -ne $null) {
    & $Cmd --version | Out-Null
    return $LASTEXITCODE -eq 0
  }
  return $false
}

function Read-Yn([string]$Prompt) {
  return (Read-Host -Prompt "$Prompt (y/n)").ToLower()[0] -eq "y"
}

# IMPORTANT: Define standard dirs, which SHOULD BE THE SAME as defined in `src/vulpix/core/dirs.py`
if (Test-Admin) {
  $VULPIX_DATA = "$env:ProgramData\vulpix"
  $VULPIX_CONFIG = "$env:ProgramData\vulpix\config"
} else {
  $VULPIX_DATA = "$env:LOCALAPPDATA\vulpix-data"
  $VULPIX_CONFIG = "$env:LOCALAPPDATA\vulpix"
}

# step 1: bootstrap python ------------------------------------------------------------------------

$bootstrappedPackages = @()

function Install-ManualPackage([string]$Package) {
  Write-Host "INFO: downloading $Package bootstrap script"
  $tmp = New-TemporaryFile
  Move-Item $tmp "$tmp.ps1"
  $tmp = "$tmp.ps1"
  $url = "$VULPIX_REPO_RAW/src/vulpix/package_managers/manual/packages/$Package.ps1"
  Invoke-WebRequest -Uri $url -OutFile $tmp
  $installDir = "$VULPIX_DATA\manual\packages\$Package"

  Write-Host "INFO: installing $Package in '$installDir'"
  $binDirs = @(powershell -NoProfile -File $tmp -InstallDir "$installDir")
  if (-not ($? -and $binDirs -and ($binDirs -is [array]))) {
    Write-Host "FATAL: $Package bootstrap failed"
    exit 1
  }

  # add temporarily to PATH (only for the powershell session, but that's all that's needed)
  $binDirs | ForEach-Object { $env:PATH = "$installDir\$_;$env:PATH" }
  Remove-Item $tmp -Force
}

function Bootstrap-Packages([string[]]$Packages) {
  $Packages = $Packages | Where-Object { -not (Test-Command $_) }
  if ($Packages.Count -eq 0) {
    return
  }

  $Packages | ForEach-Object {
    Write-Host "INFO: $_ not installed"
    Install-ManualPackage $_

    if (-not (Test-Command $_)) {
      Write-Host "FATAL: $_ bootstrap suppossedly succeeded, but $_ isn't available"
      exit 1
    }
  }

  # let vulpix know about bootstrapped packages with bootstrapped.json
  # (see src/vulpix/cli/bootstrap.py)
  @{ packages = @{ manual = @($Packages); }; } |
    ConvertTo-Json -Depth 10 |
    Set-Content (Join-Path $VULPIX_DATA "bootstrapped.json")
}

# python is obviously required for vulpix
Bootstrap-Packages 'python'

# step 2: install vulpix --------------------------------------------------------------------------

Write-Host "INFO: pip install vulpix"
python -m pip install --upgrade vulpix

if ($LASTEXITCODE -ne 0) {
  Write-Host "FATAL: install failed"
  exit 1
}
if (-not (Test-Command vulpix)) {
  Write-Host "FATAL: install suppossedly succeeded, but vulpix isn't available"
  exit 1
}

# step 3: first run for registering blueprint packages --------------------------------------------

Write-Host "INFO: running vulpix for the first time"
vulpix sync
