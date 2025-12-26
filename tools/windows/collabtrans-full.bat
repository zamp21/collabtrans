@echo off
setlocal

REM CollabTrans Full - Windows Launcher
REM This script sets up the Windows environment and launches CollabTrans Full

REM Set default configuration directory for Windows
set COLLABTRANS_CONFIG_DIR=C:\Users\Public\collabtrans
set COLLABTRANS_PORT=8020

REM Create config directory if it doesn't exist
if not exist "%COLLABTRANS_CONFIG_DIR%" (
    mkdir "%COLLABTRANS_CONFIG_DIR%"
    echo Created configuration directory: %COLLABTRANS_CONFIG_DIR%
)

REM Copy template files to config directory if they don't exist
if not exist "%COLLABTRANS_CONFIG_DIR%\global_config.json" (
    if exist "%~dp0config\global_config.json" (
        copy "%~dp0config\global_config.json" "%COLLABTRANS_CONFIG_DIR%\"
        echo Copied global_config.json to %COLLABTRANS_CONFIG_DIR%
    )
)

if not exist "%COLLABTRANS_CONFIG_DIR%\local_secrets.json" (
    if exist "%~dp0config\local_secrets.json.template" (
        copy "%~dp0config\local_secrets.json.template" "%COLLABTRANS_CONFIG_DIR%\local_secrets.json"
        echo Copied local_secrets.json template to %COLLABTRANS_CONFIG_DIR%
    )
)

if not exist "%COLLABTRANS_CONFIG_DIR%\app_config.json" (
    if exist "%~dp0config\app_config.json.template" (
        copy "%~dp0config\app_config.json.template" "%COLLABTRANS_CONFIG_DIR%\app_config.json"
    ) else if exist "%~dp0config\app_config.json" (
        copy "%~dp0config\app_config.json" "%COLLABTRANS_CONFIG_DIR%\"
    )
    echo Copied app_config.json to %COLLABTRANS_CONFIG_DIR%
)

REM Set environment variables for the application
set DOCUTRANSLATE_PORT=%COLLABTRANS_PORT%
set COLLABTRANS_CONFIG_PATH=%COLLABTRANS_CONFIG_DIR%

REM Change to the directory containing the executable
cd /d "%~dp0bin"

REM Check if executable exists
if not exist "CollabTrans_full-*-win.exe" (
    echo Error: CollabTrans Full executable not found in bin directory
    echo Please ensure the application is properly installed
    pause
    exit /b 1
)

REM Find the executable (handle version numbers)
for %%f in (CollabTrans_full-*-win.exe) do set EXE_NAME=%%f

REM Run the application
echo Starting CollabTrans Full...
echo Configuration directory: %COLLABTRANS_CONFIG_DIR%
echo Port: %COLLABTRANS_PORT%
echo Executable: %EXE_NAME%
echo.
"%EXE_NAME%" %*
