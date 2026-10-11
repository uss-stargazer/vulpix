# Windows PowerShell bootstrap.

$ErrorActionPreference = 'Stop'

$VULPIX_REPO = 'uss-stargazer/vulpix'
$VULPIX_BRANCH = 'refactor/python-rewrite'
$VULPIX_REPO_GIT = "https://github.com/$VULPIX_REPO"
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

# step 1: bootstrap python and git ----------------------------------------------------------------

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

  # add to PATH (only for the powershell session, but that's all that's needed)
  $binDirs | ForEach-Object { $env:PATH = "$installDir\$_;$env:PATH" }
  Remove-Item $tmp -Force
}

function Bootstrap-Package([string]$Package) {
  if (-not (Test-Command $Package)) {
    Write-Host "INFO: $Package not installed"
    Install-ManualPackage $Package

    if (-not (Test-Command $Package)) {
      Write-Host "FATAL: $Package bootstrap suppossedly succeeded, but $Package isn't available"
      exit 1
    }
  }
  $bootstrappedPackages += @($Package)
}

Bootstrap-Package 'python' # obviously required for vulpix
Bootstrap-Package 'git' # required to `pip install git+...`

# step 2: install vulpix --------------------------------------------------------------------------

Write-Host "INFO: pip install vulpix"
python -m pip install "git+$VULPIX_REPO_GIT@$VULPIX_BRANCH"

if (-not (Test-Command vulpix)) {
  Write-Host "FATAL: install suppossedly succeeded, but vulpix isn't available"
  exit 1
}

# step 3: init blueprint --------------------------------------------------------------------------

$BLUEPRINT = Join-Path $VULPIX_CONFIG "blueprint.yaml"
$defaultBlueprint = @"
# vulpix blueprint for system/user

# specify target packages for system (by package manager)
packages:
  $(
    if ($bootstrappedPackages.Count -gt 0) {
      "manual: [$($bootstrappedPackages -join ", ")] # bootstrapped defaults`n"
    }
  )pip:
    - vulpix # updates vulpix itself automatically
  # ...other package managers

# specify target config for installed packages (controlled by each config manager)
configs:
  scripts: "Your config here!" # see 'scripts' config manager docs for more info
  # ...other config managers

# misc settings (optional, see docs)
dotfiles: ~/.dotfiles # looks for dotfiles here
settings:
  threads: # auto     # number of task worker threads
  alt_screen: true    # fancy fullscreen for cli
"@

write-host $defaultBlueprint

if ((-not (Test-Path $BLUEPRINT)) -or (Read-Yn "overwrite existing blueprint with default?")) {
  Write-Host "INFO: writing default blueprint"
  Set-Content $BLUEPRINT -Value $defaultBlueprint
}

# step 4: first run for registering blueprint packages --------------------------------------------

Write-Host "INFO: running vulpix for the first time"
vulpix sync
