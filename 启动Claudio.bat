@echo off
chcp 65001 >nul
title Claudio · 启动中...
cd /d "%~dp0"

echo.
echo ╔══════════════════════════════════╗
echo ║     Claudio · AI Music Radio     ║
echo ╚══════════════════════════════════╝
echo.

:: ── 1. Node modules ──
if not exist "node_modules\NeteaseCloudMusicApi" (
    echo [1/4] Installing Node dependencies...
    call npm install --silent 2>nul
)

:: ── 2. Python venv ──
if not exist ".venv\Scripts\python.exe" (
    echo [2/4] Creating Python virtual environment...
    python -m venv .venv 2>nul
    if errorlevel 1 (
        echo ERROR: Python not found. Please install Python 3.10+
        pause
        exit /b 1
    )
)

:: ── 3. Python dependencies ──
echo [3/4] Checking Python dependencies...
.venv\Scripts\python.exe -c "import webview, flask, flask_cors, flask_sock, requests" 2>nul
if errorlevel 1 (
    echo Installing Python packages...
    .venv\Scripts\pip.exe install flask flask-cors flask-sock requests websockets pywebview edge-tts --quiet 2>nul
)

:: ── 4. Launch ──
echo [4/4] Starting Claudio...
start "" /B .venv\Scripts\python.exe desktop.py
echo.
echo Claudio is running. Close this window to stop.
echo.
pause
