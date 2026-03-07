@echo off
title Pet Pooja

:: Kill anything already on port 8000
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do taskkill /PID %%a /F >nul 2>&1

:: Start Backend
cd /d "%~dp0backend"
start "Backend" cmd /k "python main.py"

:: Wait for backend to be ready (poll health endpoint)
echo Waiting for backend...
:wait
timeout /t 2 /nobreak >nul
curl -s http://localhost:8000/health >nul 2>&1
if errorlevel 1 goto wait
echo Backend ready!

:: Start Frontend
cd /d "%~dp0frontend"
start "Frontend" cmd /k "npm run dev"

timeout /t 3 /nobreak >nul
start http://localhost:3000/
exit
