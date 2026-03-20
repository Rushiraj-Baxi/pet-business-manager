@echo off
title PET Business Manager - First Time Setup
echo ============================================
echo    PET Business Manager - SETUP
echo ============================================
echo.
echo This will install all dependencies.
echo Make sure you have Python 3.10+ and Node.js 18+ installed.
echo.

cd /d "%~dp0"

:: Check Python
python --version
if errorlevel 1 (
    echo [ERROR] Python not found! 
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Check Node
node --version
if errorlevel 1 (
    echo [ERROR] Node.js not found!
    echo Download from: https://nodejs.org/
    pause
    exit /b 1
)

echo.
echo [1/2] Installing Python backend dependencies...
cd backend
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install Python dependencies
    pause
    exit /b 1
)
cd ..

echo.
echo [2/2] Installing Node.js frontend dependencies...
cd frontend
call npm install
if errorlevel 1 (
    echo [ERROR] Failed to install frontend dependencies
    pause
    exit /b 1
)
cd ..

echo.
echo ============================================
echo    SETUP COMPLETE!
echo ============================================
echo.
echo    Now run start.bat to launch the application.
echo.
pause
