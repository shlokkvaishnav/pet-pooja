@echo off
title Pet Pooja - Starting Services

echo ========================================
echo   Starting Pet Pooja Services
echo ========================================
echo.

:: Start Backend (FastAPI + Uvicorn) in a new window
echo [1/2] Starting Backend (port 8000)...
cd /d "%~dp0backend"
start "Pet Pooja - Backend" cmd /k "(if exist ..\.venv\Scripts\activate.bat (call ..\.venv\Scripts\activate.bat) else if exist .venv\Scripts\activate.bat (call .venv\Scripts\activate.bat)) && python main.py"

:: Small delay to let backend initialize first
timeout /t 3 /nobreak >nul

:: Start Frontend (Vite dev server) in a new window
echo [2/2] Starting Frontend (Vite)...
cd /d "%~dp0frontend"
start "Pet Pooja - Frontend" cmd /k "npm run dev"

cd /d "%~dp0"

echo.
echo ========================================
echo   Both services are starting!
echo   Backend:  http://localhost:8000
echo   Frontend: check the Vite terminal
echo ========================================
echo.
echo You can close this window. The services
echo will keep running in their own windows.
pause
