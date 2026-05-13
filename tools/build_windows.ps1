param(
    [switch]$Clean,
    [switch]$Onefile
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

function Invoke-Step {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Label,
        [Parameter(Mandatory = $true)]
        [scriptblock]$Command
    )

    Write-Host ""
    Write-Host "==> $Label"
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE"
    }
}

if ($Clean) {
    Remove-Item -LiteralPath "build" -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath "dist" -Recurse -Force -ErrorAction SilentlyContinue
}

Invoke-Step "Installing runtime requirements" { python -m pip install -r requirements.txt }
Invoke-Step "Installing build requirements" { python -m pip install -r requirements-build.txt }
if ($Onefile) {
    Invoke-Step "Running PyInstaller onefile" { python -m PyInstaller --clean --noconfirm BeatScope_onefile.spec }
    $exePath = Join-Path $repoRoot "dist\BeatScope.exe"
} else {
    Invoke-Step "Running PyInstaller onedir" { python -m PyInstaller --clean --noconfirm BeatScope.spec }
    $exePath = Join-Path $repoRoot "dist\BeatScope\BeatScope.exe"
}

if (-not (Test-Path -LiteralPath $exePath)) {
    throw "Build did not create expected executable: $exePath"
}

Write-Host ""
Write-Host "Build finished:"
Write-Host "  $exePath"
