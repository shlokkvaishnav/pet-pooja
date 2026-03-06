@echo off
title Pet Pooja - Starting Services

echo ========================================
echo   Starting Pet Pooja Services
echo ========================================
echo.

:: Start Backend (FastAPI + Uvicorn) in a new window with venv activated
echo [1/2] Starting Backend (port 8000)...
start "Pet Pooja - Backend" cmd /k "cd /d %~dp0 && call .venv\Scripts\activate.bat && cd backend && python main.py"

:: Small delay to let backend initialize first
timeout /t 2 /nobreak >nul

:: Start Frontend (Vite dev server) in a new window
echo [2/2] Starting Frontend (Vite)...
start "Pet Pooja - Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

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
