@echo off
setlocal

REM CollabTrans Simple Launcher
REM Minimal script that just sets environment and runs the executable

REM Set essential environment variables
set COLLABTRANS_CONFIG_PATH=C:\Users\Public\collabtrans
set DOCUTRANSLATE_PORT=8020

REM Change to executable directory
cd /d "%~dp0bin"

REM Run the executable directly
CollabTrans-*-win.exe %*
