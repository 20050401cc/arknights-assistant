@echo off
chcp 65001 >nul
title Arknights Assistant - MuMu Edition
echo ========================================
echo   Arknights Assistant - MuMu Edition
echo ========================================
echo.
cd /d "%~dp0"

set "MUMU_ROOT=E:\MuMuPlayer-12.0"
set "MUMU_CLI=%MUMU_ROOT%\nx_main\mumu-cli.exe"
set "ADB=%MUMU_ROOT%\nx_device\12.0\shell\adb.exe"

if not exist "%ADB%" (
    echo [ERROR] MuMu ADB not found: %ADB%
    pause
    exit /b 1
)

echo [INFO] MuMu ADB: %ADB%
if exist "%MUMU_CLI%" (
    echo [INFO] Starting MuMu instance 0 if needed...
    "%MUMU_CLI%" control --vmindex 0 launch >nul 2>&1
    timeout /t 8 /nobreak >nul
    "%MUMU_CLI%" adb --vmindex 0 --cmd connect
)

:: Check Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found! Please install Python 3.9+
    pause
    exit /b 1
)

:: Check dependencies
python -c "import PyQt5" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Installing dependencies...
    pip install -r requirements.txt
)

:: Launch
echo [INFO] Starting Arknights Assistant...
echo.
python main.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Application exited with error!
    pause
)
