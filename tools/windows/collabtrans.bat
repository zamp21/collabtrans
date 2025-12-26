@echo off
setlocal

REM CollabTrans Lite - Windows Launcher
REM This script sets up the Windows environment and launches CollabTrans
REM Note: This script uses RUNTIME configuration files, not template files

REM Set runtime configuration directory for Windows
set COLLABTRANS_CONFIG_DIR=C:\Users\Public\collabtrans
set COLLABTRANS_PORT=8020

REM Create config directory if it doesn't exist
if not exist "%COLLABTRANS_CONFIG_DIR%" (
    mkdir "%COLLABTRANS_CONFIG_DIR%"
    echo Created configuration directory: %COLLABTRANS_CONFIG_DIR%
)

REM Verify configuration directory exists (should be created during installation)
if not exist "%COLLABTRANS_CONFIG_DIR%" (
    echo ERROR: Configuration directory not found: %COLLABTRANS_CONFIG_DIR%
    echo Please run install.bat first to properly install the application.
    pause
    exit /b 1
)

REM Check if essential configuration files exist
if not exist "%COLLABTRANS_CONFIG_DIR%\global_config.json" (
    echo WARNING: global_config.json not found in configuration directory.
    echo Please ensure the application was properly installed.
)

if not exist "%COLLABTRANS_CONFIG_DIR%\local_secrets.json" (
    echo WARNING: local_secrets.json not found in configuration directory.
    echo Please ensure the application was properly installed.
)

REM Set environment variables for the application
set DOCUTRANSLATE_PORT=%COLLABTRANS_PORT%
set COLLABTRANS_CONFIG_PATH=%COLLABTRANS_CONFIG_DIR%

REM Change to the directory containing the executable
cd /d "%~dp0bin"

REM Find the executable (handle version numbers robustly)
set "EXE_NAME="
set "EXE_PATH="

REM Try to find lite version first
for %%f in (CollabTrans-*-win.exe) do (
    if not defined EXE_NAME (
        set "EXE_NAME=%%f"
        set "EXE_PATH=%%~f"
    )
)

REM If not found, try any CollabTrans executable
if not defined EXE_NAME (
    for %%f in (CollabTrans-*.exe) do (
        if not defined EXE_NAME (
            set "EXE_NAME=%%f"
            set "EXE_PATH=%%~f"
        )
    )
)

REM Check if executable exists and is accessible
if not defined EXE_NAME (
    echo Error: CollabTrans executable not found in ^"%cd%^".
    echo Expected: CollabTrans-*-win.exe
    echo Please ensure the application is properly installed under ^"%~dp0bin^".
    echo.
    echo Current directory: %cd%
    echo Available files:
    dir /b *.exe 2>nul
    pause
    exit /b 1
)

REM Verify the executable exists and is accessible
if not exist "%EXE_PATH%" (
    echo Error: CollabTrans executable not accessible: %EXE_PATH%
    echo Please check file permissions and ensure the file is not corrupted.
    pause
    exit /b 1
)

REM Run the application
echo Starting CollabTrans Lite...
echo Configuration directory: %COLLABTRANS_CONFIG_DIR%
echo Port: %COLLABTRANS_PORT%
echo Executable: %EXE_NAME%
echo Working directory: %cd%
echo.
echo Press Ctrl+C to stop the application
echo.

REM Set additional environment variables for debugging
set COLLABTRANS_DEBUG=1

REM Run the executable with error handling
"%EXE_NAME%" %*
set EXIT_CODE=%errorlevel%

if %EXIT_CODE% neq 0 (
    echo.
    echo Application exited with error code: %EXIT_CODE%
    echo Please check the configuration files and try again.
    echo Configuration directory: %COLLABTRANS_CONFIG_DIR%
    pause
)
