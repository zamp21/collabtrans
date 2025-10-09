# Build CollabTrans Windows Installer with Inno Setup
# Usage:
#   tools/build_win_installer.ps1            # build both lite and full installers
#   tools/build_win_installer.ps1 --lite     # build lite installer only
#   tools/build_win_installer.ps1 --full     # build full installer only

param(
    [switch]$Lite,
    [switch]$Full,
    [string]$InnoSetupPath = ""
)

$ErrorActionPreference = "Stop"

# Get script directory and project root
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
Set-Location $RootDir

Write-Host "Building CollabTrans Windows Installer..." -ForegroundColor Green

# Determine what to build
$want_lite = $true
$want_full = $true
if ($Lite) {
    $want_full = $false
} elseif ($Full) {
    $want_lite = $false
}

# Find Inno Setup
function Find-InnoSetup {
    $possiblePaths = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 5\ISCC.exe",
        "${env:ProgramFiles}\Inno Setup 5\ISCC.exe",
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "C:\Program Files\Inno Setup 6\ISCC.exe"
    )
    
    if ($InnoSetupPath -and (Test-Path $InnoSetupPath)) {
        return $InnoSetupPath
    }
    
    foreach ($path in $possiblePaths) {
        if (Test-Path $path) {
            return $path
        }
    }
    
    return $null
}

# Ensure virtual environment and build executables
function Ensure-Venv {
    if (-not (Test-Path ".venv")) {
        Write-Host "[env] Creating virtual environment..." -ForegroundColor Yellow
        python -m venv .venv
    }
    
    Write-Host "[env] Activating virtual environment..." -ForegroundColor Yellow
    & ".venv\Scripts\Activate.ps1"
    
    Write-Host "[env] Upgrading pip..." -ForegroundColor Yellow
    python -m pip install --upgrade pip | Out-Null
    
    # Pin numpy to 1.26.4 (compatible with Python 3.12, stable with PyInstaller)
    Write-Host "[env] Installing numpy==1.26.4 for stable PyInstaller builds (Py3.12 compatible)" -ForegroundColor Yellow
    python -m pip install --force-reinstall 'numpy==1.26.4' | Out-Null
    
    # Install project and PyInstaller after numpy is pinned
    Write-Host "[env] Installing project dependencies and PyInstaller..." -ForegroundColor Yellow
    python -m pip install . pyinstaller | Out-Null
}

# Get version
function Get-Version {
    $version = python -c "import collabtrans; print(collabtrans.__version__)"
    return $version.Trim()
}

# Build PyInstaller
function Build-PyInstaller {
    param($SpecFile)
    Write-Host "[build] pyinstaller -y $SpecFile" -ForegroundColor Yellow
    pyinstaller -y $SpecFile
}

# Update Inno Setup script with current version
function Update-InnoScript {
    param($Version)
    
    $scriptPath = "tools\collabtrans_installer.iss"
    if (-not (Test-Path $scriptPath)) {
        Write-Host "Error: Inno Setup script not found at $scriptPath" -ForegroundColor Red
        return $false
    }
    
    $content = Get-Content $scriptPath -Raw
    $content = $content -replace '#define MyAppVersion "2\.0\.0"', "#define MyAppVersion `"$Version`""
    $content = $content -replace '#define MyAppExeName "CollabTrans-2\.0\.0-win\.exe"', "#define MyAppExeName `"CollabTrans-$Version-win.exe`""
    $content = $content -replace '#define MyAppFullExeName "CollabTrans_full-2\.0\.0-win\.exe"', "#define MyAppFullExeName `"CollabTrans_full-$Version-win.exe`""
    
    Set-Content $scriptPath $content -Encoding UTF8
    Write-Host "[installer] Updated Inno Setup script with version $Version" -ForegroundColor Green
    return $true
}

# Build installer with Inno Setup
function Build-Installer {
    param($Version)
    
    $innoSetup = Find-InnoSetup
    if (-not $innoSetup) {
        Write-Host "Error: Inno Setup not found. Please install Inno Setup or specify the path with -InnoSetupPath" -ForegroundColor Red
        Write-Host "Download from: https://jrsoftware.org/isinfo.php" -ForegroundColor Yellow
        return $false
    }
    
    Write-Host "[installer] Found Inno Setup at: $innoSetup" -ForegroundColor Green
    
    # Update script with current version
    if (-not (Update-InnoScript $Version)) {
        return $false
    }
    
    # Build installer
    $scriptPath = "tools\collabtrans_installer.iss"
    Write-Host "[installer] Building installer with Inno Setup..." -ForegroundColor Yellow
    
    $process = Start-Process -FilePath $innoSetup -ArgumentList "`"$scriptPath`"" -Wait -PassThru -NoNewWindow
    
    if ($process.ExitCode -eq 0) {
        Write-Host "[installer] Installer built successfully!" -ForegroundColor Green
        return $true
    } else {
        Write-Host "[installer] Installer build failed with exit code: $($process.ExitCode)" -ForegroundColor Red
        return $false
    }
}

# Main execution
try {
    # Check if Inno Setup is available
    $innoSetup = Find-InnoSetup
    if (-not $innoSetup) {
        Write-Host "Inno Setup not found. Building simple package instead..." -ForegroundColor Yellow
        Write-Host "To build a proper installer, please install Inno Setup from: https://jrsoftware.org/isinfo.php" -ForegroundColor Yellow
        
        # Fall back to simple package build
        & "$ScriptDir\build_win.ps1" -Lite:$Lite -Full:$Full
        exit 0
    }
    
    Ensure-Venv
    $version = Get-Version
    Write-Host "Building version: $version" -ForegroundColor Cyan
    
    # Create output directories
    New-Item -ItemType Directory -Path "build\installer" -Force | Out-Null
    New-Item -ItemType Directory -Path "tools\windows" -Force | Out-Null
    
    # Build executables
    if ($want_lite) {
        Write-Host "Building lite executable..." -ForegroundColor Yellow
        Build-PyInstaller "lite.spec"
    }
    
    if ($want_full) {
        Write-Host "Building full executable..." -ForegroundColor Yellow
        Build-PyInstaller "full.spec"
    }
    
    # Build installer
    if (Build-Installer $version) {
        Write-Host "Windows installer build completed!" -ForegroundColor Green
        Write-Host "Installer is available in: build\installer\" -ForegroundColor Cyan
        
        # List generated files
        $installerFiles = Get-ChildItem "build\installer\*.exe" -ErrorAction SilentlyContinue
        if ($installerFiles) {
            Write-Host "Generated installers:" -ForegroundColor Cyan
            foreach ($file in $installerFiles) {
                Write-Host "  - $($file.Name)" -ForegroundColor White
            }
        }
    } else {
        Write-Host "Installer build failed!" -ForegroundColor Red
        exit 1
    }
    
} catch {
    Write-Host "Build failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
