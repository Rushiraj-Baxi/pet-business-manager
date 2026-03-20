@echo off
setlocal EnableDelayedExpansion
title PET Business Manager
color 0B

:: Refresh PATH from registry (picks up installs since this terminal opened)
for /f "tokens=2*" %%A in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "USERPATH=%%B"
for /f "tokens=2*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "SYSPATH=%%B"
set "PATH=!SYSPATH!;!USERPATH!"

:: ─── AGGRESSIVE PYTHON SEARCH ───
:: Search every common Python install location (3.9 through 3.14)
set "PYTHONFOUND="
for %%V in (314 313 312 311 310 39) do (
    for %%D in (
        "%LOCALAPPDATA%\Programs\Python\Python%%V"
        "%PROGRAMFILES%\Python%%V"
        "%PROGRAMFILES(x86)%\Python%%V"
        "C:\Python%%V"
        "C:\Program Files\Python%%V"
        "C:\Program Files (x86)\Python%%V"
        "%USERPROFILE%\Python%%V"
        "%USERPROFILE%\AppData\Local\Programs\Python\Python%%V"
    ) do (
        if exist "%%~D\python.exe" (
            if not defined PYTHONFOUND (
                set "PYTHONFOUND=%%~D"
                set "PATH=%%~D;%%~D\Scripts;!PATH!"
            )
        )
    )
)

:: Also check Microsoft Store / WindowsApps location
if not defined PYTHONFOUND (
    for %%D in (
        "%LOCALAPPDATA%\Microsoft\WindowsApps"
    ) do (
        if exist "%%~D\python.exe" (
            set "PYTHONFOUND=%%~D"
            set "PATH=%%~D;!PATH!"
        )
        if exist "%%~D\python3.exe" (
            set "PYTHONFOUND=%%~D"
            set "PATH=%%~D;!PATH!"
        )
    )
)

:: Last resort: use WHERE to search entire C: drive for python.exe
if not defined PYTHONFOUND (
    for /f "delims=" %%F in ('where /r C:\ python.exe 2^>nul') do (
        if not defined PYTHONFOUND (
            for %%I in ("%%~dpF.") do set "PYTHONFOUND=%%~fI"
            set "PATH=!PYTHONFOUND!;!PYTHONFOUND!\Scripts;!PATH!"
        )
    )
)

:: ─── AGGRESSIVE NODE SEARCH ───
for %%N in (
    "%PROGRAMFILES%\nodejs"
    "C:\Program Files\nodejs"
    "%LOCALAPPDATA%\fnm_multishells"
    "%APPDATA%\npm"
    "%PROGRAMFILES(x86)%\nodejs"
) do (
    if exist "%%~N\node.exe" (
        set "PATH=%%~N;!PATH!"
    )
)

echo.
echo  ======================================================
echo       PET Business Manager - Starting...
echo  ======================================================
echo.

cd /d "%~dp0"

:: Check Python
set "PYCMD="
python --version >nul 2>&1
if not errorlevel 1 (
    set "PYCMD=python"
    goto :pythonfound
)
py --version >nul 2>&1
if not errorlevel 1 (
    set "PYCMD=py"
    goto :pythonfound
)
python3 --version >nul 2>&1
if not errorlevel 1 (
    set "PYCMD=python3"
    goto :pythonfound
)

:: If still not found, show exactly where we looked
echo [ERROR] Python not found anywhere on this computer!
echo.
if defined PYTHONFOUND (
    echo  Found python.exe at: !PYTHONFOUND!
    echo  But it still didn't work. Try running:
    echo    "!PYTHONFOUND!\python.exe" --version
) else (
    echo  Searched all common locations - no python.exe found.
    echo.
    echo  Please install Python manually:
    echo    1. Go to https://www.python.org/downloads/
    echo    2. Download Python 3.12
    echo    3. Run installer - IMPORTANT: Check "Add Python to PATH"
    echo    4. Restart PC
    echo    5. Run start.bat again
)
echo.
pause
exit /b 1

:pythonfound
:: Check Node
node --version >nul 2>&1
if errorlevel 1 (
    npx --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Node.js not found!
        echo.
        echo  Please install from https://nodejs.org/ ^(LTS version^)
        echo  Then restart PC and run start.bat again.
        echo.
        pause
        exit /b 1
    )
)

echo  Using Python: & !PYCMD! --version
echo  Using Node:   & node --version
if defined PYTHONFOUND echo  Python found at: !PYTHONFOUND!
echo.

:: Run database migration (adds new columns if needed)
echo  [1/3] Running database migration...
cd backend
!PYCMD! migrate.py
cd ..

:: Start backend
echo  [2/3] Starting backend server...
cd backend
start "PET-Backend" cmd /k "set PATH=!PATH! && !PYCMD! -m uvicorn main:app --host 127.0.0.1 --port 8000"
cd ..

:: Wait for backend
echo        Waiting for backend...
timeout /t 4 /nobreak >nul

:: Start frontend
echo  [3/3] Starting frontend...
cd frontend
start "PET-Frontend" cmd /k "set PATH=!PATH! && npm run dev"
cd ..

:: Wait for frontend
timeout /t 5 /nobreak >nul

echo.
echo  ======================================================
echo       PET Business Manager is RUNNING!
echo  ======================================================
echo.
echo       Open:  http://localhost:5173
echo       API:   http://127.0.0.1:8000
echo.
echo       Press any key to STOP all servers...
echo  ======================================================

:: Open browser automatically
start http://localhost:5173

pause

:: Kill servers
taskkill /FI "WINDOWTITLE eq PET-Backend" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq PET-Frontend" /F >nul 2>&1
echo  Servers stopped. Goodbye!
