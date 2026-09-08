# Anchor Installation Script for Windows PowerShell
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\setup.ps1
# or:
#   irm https://raw.githubusercontent.com/yosef-atta/anchor/main/setup.ps1 | iex

$ErrorActionPreference = "Stop"

Write-Host "⚓ Installing Anchor..." -ForegroundColor Cyan

# Determine installation source: local repo directory or remote git repo
$ScriptDir = $null
if ($MyInvocation -and $MyInvocation.MyCommand -and $MyInvocation.MyCommand.Path) {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path -ErrorAction SilentlyContinue
}

if ($ScriptDir -and (Test-Path "$ScriptDir\pyproject.toml")) {
    $InstallSource = $ScriptDir
} else {
    $InstallSource = "git+https://github.com/yosef-atta/anchor.git"
}

# Check if uv is installed
$UvPath = Get-Command uv -ErrorAction SilentlyContinue

if ($UvPath) {
    Write-Host "• Found uv package manager. Installing Anchor tool globally with uv..." -ForegroundColor Green
    uv tool install --force $InstallSource
} else {
    # Check for python
    $PythonPath = Get-Command python -ErrorAction SilentlyContinue
    if (-not $PythonPath) {
        $PythonPath = Get-Command py -ErrorAction SilentlyContinue
    }

    if (-not $PythonPath) {
        Write-Error "Neither uv nor Python 3.12+ was found on your system. Please install uv (https://astral.sh/uv) or Python 3.12+ to install Anchor."
        exit 1
    }

    Write-Host "• Installing Anchor via pip..." -ForegroundColor Green
    & $PythonPath.Source -m pip install --upgrade $InstallSource
}

# Verify installation
Write-Host "• Verifying installation..." -ForegroundColor Cyan

# Refresh environment path in current session if needed
$UvBinPath = "$HOME\.local\bin"
if ((Test-Path -Path $UvBinPath) -and ($env:Path -notlike "*$UvBinPath*")) {
    $env:Path = "$UvBinPath;$env:Path"
}

$AnchorCmd = Get-Command anchor -ErrorAction SilentlyContinue

if ($AnchorCmd) {
    $VersionOutput = & $AnchorCmd.Source --version
    Write-Host "✓ Successfully installed $VersionOutput" -ForegroundColor Green
    Write-Host "Run 'anchor --help' to get started." -ForegroundColor Green
} else {
    Write-Host "✓ Anchor package installed." -ForegroundColor Green
    Write-Host "NOTE: Please ensure '$HOME\.local\bin' or your Python Scripts directory is in your PATH." -ForegroundColor Yellow
}
