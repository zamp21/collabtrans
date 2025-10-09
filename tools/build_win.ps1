# Build CollabTrans Windows installer package
# Usage:
#   tools/build_win.ps1            # build both lite and full
#   tools/build_win.ps1 --lite     # build lite only
#   tools/build_win.ps1 --full     # build full only

param(
    [string]$param1 = ""
)

$ErrorActionPreference = "Stop"

# Get script directory and project root
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
Set-Location $RootDir

Write-Host "Building CollabTrans Windows package..." -ForegroundColor Green

# Determine what to build
$want_lite = $true
$want_full = $true
if ($param1 -eq "--lite") {
    $want_full = $false
    Write-Host "Building LITE version only" -ForegroundColor Cyan
} elseif ($param1 -eq "--full") {
    $want_lite = $false
    Write-Host "Building FULL version only" -ForegroundColor Cyan
} else {
    Write-Host "Building BOTH lite and full versions" -ForegroundColor Cyan
}

# Ensure virtual environment
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
    pyinstaller -y --clean $SpecFile
}

# Create Windows installer package
function Make-WinPackage {
    param($Version, $IsFull = $false)
    
    $packageType = if ($IsFull) { "full" } else { "lite" }
    $outDir = "build\win"
    $packageRoot = "$outDir\collabtrans-$packageType-$Version"
    $exeName = if ($IsFull) { "CollabTrans_full-$Version-win.exe" } else { "CollabTrans-$Version-win.exe" }
    $appBin = "dist\$exeName"
    
    if (-not (Test-Path $appBin)) {
        Write-Host "[$packageType] Binary not found: $appBin" -ForegroundColor Red
        return $false
    }
    
    # Clean and create package structure
    if (Test-Path $packageRoot) {
        Remove-Item -Recurse -Force $packageRoot
    }
    New-Item -ItemType Directory -Path $packageRoot -Force | Out-Null
    New-Item -ItemType Directory -Path "$packageRoot\bin" -Force | Out-Null
    New-Item -ItemType Directory -Path "$packageRoot\config" -Force | Out-Null
    New-Item -ItemType Directory -Path "$packageRoot\config\templates" -Force | Out-Null
    
    # Copy executable
    Copy-Item $appBin "$packageRoot\bin\"
    
    # Copy configuration files to config directory
    $configFiles = @(
        "global_config.json",
        "local_secrets.json.template",
        "app_config.json.template"
    )
    
    foreach ($configFile in $configFiles) {
        if (Test-Path $configFile) {
            Copy-Item $configFile "$packageRoot\config\"
            Write-Host "[$packageType] Copied $configFile" -ForegroundColor Green
        }
    }
    
    # Copy additional template files if they exist
    $templateFiles = @(
        "local_config.json.template",
        "app_config.json"
    )
    
    foreach ($templateFile in $templateFiles) {
        if (Test-Path $templateFile) {
            Copy-Item $templateFile "$packageRoot\config\templates\"
            Write-Host "[$packageType] Copied template $templateFile" -ForegroundColor Green
        }
    }
    
    # Create Windows batch launcher
    $launcherName = if ($IsFull) { "collabtrans-full.bat" } else { "collabtrans.bat" }
    $exeNameInBin = if ($IsFull) { "CollabTrans_full-$Version-win.exe" } else { "CollabTrans-$Version-win.exe" }
    
    $launcherContent = @"
@echo off
setlocal

REM Set default configuration directory for Windows
set COLLABTRANS_CONFIG_DIR=C:\Users\Public\collabtrans
set COLLABTRANS_PORT=8010

REM Create config directory if it doesn't exist
if not exist "%COLLABTRANS_CONFIG_DIR%" (
    mkdir "%COLLABTRANS_CONFIG_DIR%"
    echo Created configuration directory: %COLLABTRANS_CONFIG_DIR%
)

REM Copy template files to config directory if they don't exist
if not exist "%COLLABTRANS_CONFIG_DIR%\global_config.json" (
    copy "%~dp0config\global_config.json" "%COLLABTRANS_CONFIG_DIR%\"
    echo Copied global_config.json to %COLLABTRANS_CONFIG_DIR%
)

if not exist "%COLLABTRANS_CONFIG_DIR%\local_secrets.json" (
    copy "%~dp0config\local_secrets.json.template" "%COLLABTRANS_CONFIG_DIR%\local_secrets.json"
    echo Copied local_secrets.json template to %COLLABTRANS_CONFIG_DIR%
)

if not exist "%COLLABTRANS_CONFIG_DIR%\app_config.json" (
    if exist "%~dp0config\app_config.json.template" (
        copy "%~dp0config\app_config.json.template" "%COLLABTRANS_CONFIG_DIR%\app_config.json"
    ) else (
        copy "%~dp0config\app_config.json" "%COLLABTRANS_CONFIG_DIR%\"
    )
    echo Copied app_config.json to %COLLABTRANS_CONFIG_DIR%
)

REM Set environment variables for the application
set DOCUTRANSLATE_PORT=%COLLABTRANS_PORT%
set COLLABTRANS_CONFIG_PATH=%COLLABTRANS_CONFIG_DIR%

REM Change to the directory containing the executable
cd /d "%~dp0bin"

REM Run the application
echo Starting CollabTrans $packageType...
echo Configuration directory: %COLLABTRANS_CONFIG_DIR%
echo Port: %COLLABTRANS_PORT%
echo.
"%exeNameInBin%" %*
"@
    
    $launcherContent | Out-File -FilePath "$packageRoot\$launcherName" -Encoding ASCII
    
    # Create installation script
    $installScript = @"
@echo off
setlocal

echo Installing CollabTrans $packageType...

REM Create installation directory
set INSTALL_DIR=C:\Program Files\CollabTrans
if not exist "%INSTALL_DIR%" (
    mkdir "%INSTALL_DIR%"
    echo Created installation directory: %INSTALL_DIR%
)

REM Copy files
xcopy /E /I /Y "%~dp0*" "%INSTALL_DIR%\"
echo Copied application files to %INSTALL_DIR%

REM Ensure Redis files are properly copied
if exist "%INSTALL_DIR%\3rdParty\windows\Redis-x64-3.0.504\redis-server.exe" (
    echo ✅ Redis executable found in installation directory
) else (
    echo ❌ WARNING: Redis executable not found in installation directory
    echo Expected location: %INSTALL_DIR%\3rdParty\windows\Redis-x64-3.0.504\redis-server.exe
)

REM Prepare Windows public configuration directory
set CONFIG_DIR=C:\Users\Public\collabtrans
if not exist "%CONFIG_DIR%" (
    mkdir "%CONFIG_DIR%"
    echo Created configuration directory: %CONFIG_DIR%
)

REM Initialize runtime configuration files from templates
echo Initializing runtime configuration files from templates...

REM Check if config directory is writable
echo test > "%CONFIG_DIR%\test_write.tmp" 2>nul
if errorlevel 1 (
    echo ERROR: Cannot write to configuration directory: %CONFIG_DIR%
    echo Please run as Administrator or check directory permissions.
    pause
    exit /b 1
) else (
    del "%CONFIG_DIR%\test_write.tmp" >nul 2>&1
)

echo Template directory: %INSTALL_DIR%\config
echo Runtime directory: %CONFIG_DIR%

REM Copy global_config.json from template to runtime directory
if not exist "%CONFIG_DIR%\global_config.json" (
    if exist "%INSTALL_DIR%\config\global_config.json" (
        copy "%INSTALL_DIR%\config\global_config.json" "%CONFIG_DIR%\" >nul
        if errorlevel 1 (
            echo WARNING: Failed to copy global_config.json template to runtime directory
        ) else (
            echo Copied global_config.json template to runtime directory
        )
    ) else (
        echo WARNING: global_config.json template not found in installation package
        echo Template location: %INSTALL_DIR%\config\global_config.json
    )
) else (
    echo global_config.json already exists in runtime directory, skipping template copy
)

REM Copy local_secrets.json from template to runtime directory
if not exist "%CONFIG_DIR%\local_secrets.json" (
    if exist "%INSTALL_DIR%\config\local_secrets.json.template" (
        copy "%INSTALL_DIR%\config\local_secrets.json.template" "%CONFIG_DIR%\local_secrets.json" >nul
        if errorlevel 1 (
            echo WARNING: Failed to copy local_secrets.json template to runtime directory
        ) else (
            echo Created local_secrets.json from template in runtime directory
        )
    ) else (
        echo WARNING: local_secrets.json.template not found in installation package
        echo Template location: %INSTALL_DIR%\config\local_secrets.json.template
    )
) else (
    echo local_secrets.json already exists in runtime directory, skipping template copy
)

REM Copy app_config.json
if not exist "%CONFIG_DIR%\app_config.json" (
    if exist "%INSTALL_DIR%\config\templates\app_config.json" (
        copy "%INSTALL_DIR%\config\templates\app_config.json" "%CONFIG_DIR%\app_config.json" >nul
        if errorlevel 1 (
            echo WARNING: Failed to copy app_config.json template
        ) else (
            echo Created app_config.json from template
        )
    ) else if exist "%INSTALL_DIR%\config\app_config.json" (
        copy "%INSTALL_DIR%\config\app_config.json" "%CONFIG_DIR%\" >nul
        if errorlevel 1 (
            echo WARNING: Failed to copy app_config.json
        ) else (
            echo Copied app_config.json
        )
    ) else (
        echo WARNING: app_config.json not found in installation package
        echo Expected locations:
        echo   - %INSTALL_DIR%\config\templates\app_config.json
        echo   - %INSTALL_DIR%\config\app_config.json
    )
)

REM Copy local_config.json from template
if not exist "%CONFIG_DIR%\local_config.json" (
    if exist "%INSTALL_DIR%\config\templates\local_config.json.template" (
        copy "%INSTALL_DIR%\config\templates\local_config.json.template" "%CONFIG_DIR%\local_config.json" >nul
        if errorlevel 1 (
            echo WARNING: Failed to copy local_config.json template
        ) else (
            echo Created local_config.json from template
        )
    ) else (
        echo WARNING: local_config.json.template not found in installation package
    )
)

REM Copy local_users.json from template
if not exist "%CONFIG_DIR%\local_users.json" (
    if exist "%INSTALL_DIR%\config\templates\local_users.json.template" (
        copy "%INSTALL_DIR%\config\templates\local_users.json.template" "%CONFIG_DIR%\local_users.json" >nul
        if errorlevel 1 (
            echo WARNING: Failed to copy local_users.json template
        ) else (
            echo Created local_users.json from template
        )
    ) else (
        echo WARNING: local_users.json.template not found in installation package
    )
)

echo Configuration files initialization completed.

REM Create desktop shortcut (direct to exe)
set DESKTOP=%USERPROFILE%\Desktop
set SHORTCUT_NAME=CollabTrans $packageType.lnk
set EXE_NAME=CollabTrans-$Version-win.exe
if "%packageType%"=="full" set EXE_NAME=CollabTrans_full-$Version-win.exe

REM Create shortcut using PowerShell with environment variables
powershell -Command "`$WshShell = New-Object -comObject WScript.Shell; `$Shortcut = `$WshShell.CreateShortcut('%DESKTOP%\%SHORTCUT_NAME%'); `$Shortcut.TargetPath = '%INSTALL_DIR%\bin\%EXE_NAME%'; `$Shortcut.WorkingDirectory = '%INSTALL_DIR%\bin'; `$Shortcut.Arguments = ''; `$Shortcut.Description = 'CollabTrans $packageType'; `$Shortcut.Save()"

echo Created desktop shortcut: %SHORTCUT_NAME%

REM Create start menu shortcut (direct to exe)
set START_MENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs
if not exist "%START_MENU%\CollabTrans" (
    mkdir "%START_MENU%\CollabTrans"
)

powershell -Command "`$WshShell = New-Object -comObject WScript.Shell; `$Shortcut = `$WshShell.CreateShortcut('%START_MENU%\CollabTrans\%SHORTCUT_NAME%'); `$Shortcut.TargetPath = '%INSTALL_DIR%\bin\%EXE_NAME%'; `$Shortcut.WorkingDirectory = '%INSTALL_DIR%\bin'; `$Shortcut.Arguments = ''; `$Shortcut.Description = 'CollabTrans $packageType'; `$Shortcut.Save()"

echo Created start menu shortcut

REM Register with Windows Programs and Features
echo Registering with Windows Programs and Features...
reg add "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\CollabTrans" /v "DisplayName" /t REG_SZ /d "CollabTrans $packageType" /f >nul 2>&1
reg add "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\CollabTrans" /v "DisplayVersion" /t REG_SZ /d "$Version" /f >nul 2>&1
reg add "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\CollabTrans" /v "Publisher" /t REG_SZ /d "CollabTrans Team" /f >nul 2>&1
reg add "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\CollabTrans" /v "InstallLocation" /t REG_SZ /d "%INSTALL_DIR%" /f >nul 2>&1
reg add "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\CollabTrans" /v "UninstallString" /t REG_SZ /d "\"%INSTALL_DIR%\uninstall.bat\"" /f >nul 2>&1
reg add "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\CollabTrans" /v "DisplayIcon" /t REG_SZ /d "%INSTALL_DIR%\bin\%EXE_NAME%" /f >nul 2>&1
reg add "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\CollabTrans" /v "NoModify" /t REG_DWORD /d 1 /f >nul 2>&1
reg add "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\CollabTrans" /v "NoRepair" /t REG_DWORD /d 1 /f >nul 2>&1
reg add "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\CollabTrans" /v "EstimatedSize" /t REG_DWORD /d 200000 /f >nul 2>&1
if errorlevel 1 (
    echo WARNING: Failed to register with Windows Programs and Features
    echo You may need to run as Administrator for proper registration
) else (
    echo Successfully registered with Windows Programs and Features
)

echo.
echo Installation completed!
echo.
echo Configuration files will be created at: C:\Users\Public\collabtrans
echo To start the application, run: %INSTALL_DIR%\$launcherName
echo Or use the desktop/start menu shortcuts.
echo.
echo You can now uninstall this program through:
echo - Control Panel > Programs and Features
echo - Or run: %INSTALL_DIR%\uninstall.bat
echo.
pause
"@
    
    $installScript | Out-File -FilePath "$packageRoot\install.bat" -Encoding ASCII
    
    # Create uninstall script
    $uninstallScript = @"
@echo off
setlocal

echo Uninstalling CollabTrans $packageType...

REM Remove Windows Programs and Features registration
echo Removing Windows Programs and Features registration...
reg delete "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\CollabTrans" /f >nul 2>&1
if errorlevel 1 (
    echo WARNING: Failed to remove Windows Programs and Features registration
    echo You may need to run as Administrator for proper cleanup
) else (
    echo Successfully removed Windows Programs and Features registration
)

REM Remove installation directory
set INSTALL_DIR=C:\Program Files\CollabTrans
if exist "%INSTALL_DIR%" (
    rmdir /S /Q "%INSTALL_DIR%"
    echo Removed installation directory: %INSTALL_DIR%
)

REM Remove shortcuts
set DESKTOP=%USERPROFILE%\Desktop
set SHORTCUT_NAME=CollabTrans $packageType.lnk
if exist "%DESKTOP%\%SHORTCUT_NAME%" (
    del "%DESKTOP%\%SHORTCUT_NAME%"
    echo Removed desktop shortcut
)

set START_MENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs\CollabTrans
if exist "%START_MENU%\%SHORTCUT_NAME%" (
    del "%START_MENU%\%SHORTCUT_NAME%"
    echo Removed start menu shortcut
)

REM Remove start menu folder if empty
if exist "%START_MENU%" (
    rmdir "%START_MENU%" 2>nul
)

echo.
echo Uninstallation completed!
echo.
echo Note: Configuration files at C:\Users\Public\collabtrans were not removed.
echo You may delete them manually if no longer needed.
echo.
pause
"@
    
    $uninstallScript | Out-File -FilePath "$packageRoot\uninstall.bat" -Encoding ASCII
    
    # Create README
    $readmeContent = @"
CollabTrans $packageType - Windows Package

INSTALLATION:
1. Run install.bat as Administrator
2. The application will be installed to C:\Program Files\CollabTrans
3. Configuration files will be created at C:\Users\Public\collabtrans
4. Desktop and Start Menu shortcuts will be created

USAGE:
- Start the application using the desktop shortcut or Start Menu
- Or run: C:\Program Files\CollabTrans\$launcherName
- The application will start on port 8010 by default
- Access the web interface at: http://localhost:8010

CONFIGURATION:
- Configuration files are stored in: C:\Users\Public\collabtrans
- Edit these files to customize the application:
  - global_config.json: Global settings
  - local_secrets.json: API keys and sensitive data
  - app_config.json: Application configuration

UNINSTALLATION:
- Run uninstall.bat as Administrator
- This will remove the application but keep configuration files

VERSION: $Version
BUILD DATE: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
"@
    
    $readmeContent | Out-File -FilePath "$packageRoot\README.txt" -Encoding UTF8
    
    Write-Host "[$packageType] Built Windows package: $packageRoot" -ForegroundColor Green
    return $true
}

# Main execution
try {
    Ensure-Venv
    $version = Get-Version
    Write-Host "Building version: $version" -ForegroundColor Cyan
    
    New-Item -ItemType Directory -Path "build\win" -Force | Out-Null
    
    if ($want_lite) {
        Write-Host "Building lite package..." -ForegroundColor Yellow
        # Clean up any existing lite package
        $litePackageDir = "build\win\collabtrans-lite-$version"
        if (Test-Path $litePackageDir) {
            Remove-Item -Recurse -Force $litePackageDir
            Write-Host "[lite] Cleaned up existing lite package" -ForegroundColor Yellow
        }
        Build-PyInstaller "lite.spec"
        Make-WinPackage $version $false
    }
    
    if ($want_full) {
        Write-Host "Building full package..." -ForegroundColor Yellow
        # Clean up any existing full package
        $fullPackageDir = "build\win\collabtrans-full-$version"
        if (Test-Path $fullPackageDir) {
            Remove-Item -Recurse -Force $fullPackageDir
            Write-Host "[full] Cleaned up existing full package" -ForegroundColor Yellow
        }
        Build-PyInstaller "full.spec"
        Make-WinPackage $version $true
    }
    
    Write-Host "Windows package build completed!" -ForegroundColor Green
    Write-Host "Packages are available in: build\win\" -ForegroundColor Cyan
    
} catch {
    Write-Host "Build failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
