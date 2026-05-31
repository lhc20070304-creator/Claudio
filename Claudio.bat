@echo off
cd /d "%~dp0"
echo Starting Claudio Desktop...

:: Start Netease API
start /B node node_modules/NeteaseCloudMusicApi/app.js > nul 2>&1

:: Wait for port 3000
:wait_netease
timeout /t 1 /nobreak > nul
curl -s http://localhost:3000/ > nul 2>&1
if errorlevel 1 goto wait_netease

:: Start Flask
start /B python app.py > nul 2>&1

:: Wait for port 8080
:wait_flask
timeout /t 1 /nobreak > nul
curl -s http://localhost:8080/ > nul 2>&1
if errorlevel 1 goto wait_flask

:: Open in Edge app mode (frameless window)
start msedge --app=http://127.0.0.1:8080?desktop=1 --window-size=585,1060
