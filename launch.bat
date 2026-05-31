@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo   Claudio Launcher
echo ============================================
echo.

:: Check Node.js
where node >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found. Please install Node.js 18+
    pause
    exit /b 1
)
echo [OK] Node.js found

:: Check Python
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+
    pause
    exit /b 1
)
echo [OK] Python found

:: Check venv
if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Creating Python virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create venv
        pause
        exit /b 1
    )
)
echo [OK] venv ready

:: Install Python deps
echo [INFO] Checking Python dependencies...
.venv\Scripts\python.exe -c "import webview,flask,flask_cors,flask_sock,requests" 2>nul
if errorlevel 1 (
    echo [INFO] Installing Python packages...
    .venv\Scripts\pip.exe install flask flask-cors flask-sock requests websockets pywebview edge-tts --quiet
)
echo [OK] Python deps ready

:: Check Node modules
if not exist "node_modules\NeteaseCloudMusicApi" (
    echo [INFO] Installing Node dependencies...
    call npm install --silent
)
echo [OK] Node deps ready

:: Check config
if not exist "config.json" (
    echo [ERROR] config.json not found!
    echo Please copy config.example.json to config.json and fill in your API key.
    pause
    exit /b 1
)
echo [OK] config.json found

:: Launch
echo.
echo Starting Claudio...
echo.
start "" /B .venv\Scripts\python.exe desktop.py

echo Claudio is starting. This window will close in 3 seconds...
timeout /t 3 /nobreak >nul
exit
