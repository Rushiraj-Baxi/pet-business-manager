@echo off
setlocal EnableDelayedExpansion
title PET Business Manager - One-Click Installer
color 0A

echo.
echo  ======================================================
echo       PET Business Manager - One-Click Setup
echo       Preforms and Caps Business Dashboard
echo  ======================================================
echo.

set "APP_DIR=%~dp0"
set "APP_DIR=%APP_DIR:~0,-1%"
set "BACKEND=%APP_DIR%\backend"
set "FRONTEND=%APP_DIR%\frontend"

:: ── Helper: Refresh PATH from registry ──
for /f "tokens=2*" %%A in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "USERPATH=%%B"
for /f "tokens=2*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "SYSPATH=%%B"
set "PATH=!SYSPATH!;!USERPATH!"

:: ── Helper: Search all common Python dirs ──
set "PYCMD="
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
            if not defined PYCMD (
                set "PYCMD=%%~D\python.exe"
                set "PATH=%%~D;%%~D\Scripts;!PATH!"
            )
        )
    )
)
:: Check WindowsApps
if not defined PYCMD (
    if exist "%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe" (
        set "PYCMD=%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe"
        set "PATH=%LOCALAPPDATA%\Microsoft\WindowsApps;!PATH!"
    )
)
:: Check standard PATH
if not defined PYCMD (
    python --version >nul 2>&1
    if not errorlevel 1 set "PYCMD=python"
)
if not defined PYCMD (
    py --version >nul 2>&1
    if not errorlevel 1 set "PYCMD=py"
)

:: ============================================
:: STEP 1: Check/Install Python
:: ============================================
echo [1/5] Checking Python...
if defined PYCMD (
    echo       Python found: !PYCMD!
) else (
    echo       Python not found. Installing Python 3.12...
    echo       This may take a few minutes...
    winget install Python.Python.3.12 --scope user --accept-source-agreements --accept-package-agreements --silent
    :: Re-search after install
    for /f "tokens=2*" %%A in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "USERPATH=%%B"
    for /f "tokens=2*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "SYSPATH=%%B"
    set "PATH=!SYSPATH!;!USERPATH!"
    for %%V in (314 313 312 311 310 39) do (
        for %%D in (
            "%LOCALAPPDATA%\Programs\Python\Python%%V"
            "%PROGRAMFILES%\Python%%V"
            "C:\Python%%V"
        ) do (
            if exist "%%~D\python.exe" (
                if not defined PYCMD (
                    set "PYCMD=%%~D\python.exe"
                    set "PATH=%%~D;%%~D\Scripts;!PATH!"
                )
            )
        )
    )
    if not defined PYCMD (
        python --version >nul 2>&1
        if not errorlevel 1 set "PYCMD=python"
    )
    if defined PYCMD (
        echo       Python installed: !PYCMD!
    ) else (
        echo.
        echo  [ERROR] Could not install Python automatically.
        echo      Please install Python 3.12 manually from:
        echo      https://www.python.org/downloads/
        echo      IMPORTANT: Check "Add Python to PATH" during install!
        echo      Then run install.bat again.
        echo.
        pause
        exit /b 1
    )
)

:: ============================================
:: STEP 2: Check/Install Node.js
:: ============================================
echo [2/5] Checking Node.js...
:: Search common Node locations
for %%N in (
    "%PROGRAMFILES%\nodejs"
    "C:\Program Files\nodejs"
    "%PROGRAMFILES(x86)%\nodejs"
    "%LOCALAPPDATA%\fnm_multishells"
    "%APPDATA%\npm"
) do (
    if exist "%%~N\node.exe" set "PATH=%%~N;!PATH!"
)
node --version >nul 2>&1
if errorlevel 1 (
    echo       Node.js not found. Installing Node.js 20 LTS...
    echo       This may take a few minutes...
    winget install OpenJS.NodeJS.LTS --scope user --accept-source-agreements --accept-package-agreements --silent
    :: Re-search after install
    for /f "tokens=2*" %%A in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "USERPATH=%%B"
    for /f "tokens=2*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "SYSPATH=%%B"
    set "PATH=!SYSPATH!;!USERPATH!"
    if exist "%PROGRAMFILES%\nodejs\node.exe" set "PATH=%PROGRAMFILES%\nodejs;!PATH!"
    node --version >nul 2>&1
    if errorlevel 1 (
        echo.
        echo  [ERROR] Could not install Node.js automatically.
        echo      Please install from: https://nodejs.org/
        echo      Then run install.bat again.
        echo.
        pause
        exit /b 1
    )
    echo       Node.js installed!
) else (
    for /f "tokens=*" %%i in ('node --version 2^>^&1') do echo       Node.js %%i found.
)

:: ============================================
:: STEP 3: Install Backend Dependencies
:: ============================================
echo [3/5] Installing backend (Python) packages...
cd /d "%BACKEND%"
!PYCMD! -m pip install --upgrade pip --quiet >nul 2>&1
!PYCMD! -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo       Retrying pip install...
    !PYCMD! -m pip install -r requirements.txt
)
echo       Backend packages installed!

:: ============================================
:: STEP 4: Install Frontend Dependencies
:: ============================================
echo [4/5] Installing frontend (Node.js) packages...
cd /d "%FRONTEND%"
call npm install --silent >nul 2>&1
echo       Frontend packages installed!

:: ============================================
:: STEP 5: Setup .env config
:: ============================================
echo [5/6] Checking AI configuration...
if not exist "%BACKEND%\.env" (
    if exist "%BACKEND%\.env.example" (
        copy "%BACKEND%\.env.example" "%BACKEND%\.env" >nul
        echo       .env created from template.
        echo       [!] Edit backend\.env with your Azure OpenAI keys for AI chat to work.
    )
) else (
    echo       AI configuration found.
)

:: ============================================
:: STEP 6: Create Desktop Shortcut
:: ============================================
echo [6/6] Creating desktop shortcut...
set "DESKTOP=%USERPROFILE%\Desktop"
set "SHORTCUT=%DESKTOP%\PET Business Manager.lnk"

:: Create VBS to make shortcut
set "VBS=%TEMP%\create_shortcut.vbs"
(
echo Set oWS = WScript.CreateObject("WScript.Shell"^)
echo sLinkFile = "%SHORTCUT%"
echo Set oLink = oWS.CreateShortcut(sLinkFile^)
echo oLink.TargetPath = "%APP_DIR%\start.bat"
echo oLink.WorkingDirectory = "%APP_DIR%"
echo oLink.Description = "PET Business Manager - Preforms and Caps Dashboard"
echo oLink.WindowStyle = 1
echo oLink.Save
) > "%VBS%"
cscript //nologo "%VBS%"
del "%VBS%" >nul 2>&1
echo       Desktop shortcut created!

:: ============================================
:: DONE
:: ============================================
echo.
echo  ======================================================
echo       INSTALLATION COMPLETE!
echo  ======================================================
echo.
echo  A shortcut "PET Business Manager" has been
echo  placed on your Desktop.
echo.
echo  You can also run start.bat from this folder.
echo  ======================================================

set /p LAUNCH="  Launch the app now? (Y/N): "
if /i "%LAUNCH%"=="Y" (
    echo  Starting PET Business Manager...
    call "%APP_DIR%\start.bat"
)

pause
