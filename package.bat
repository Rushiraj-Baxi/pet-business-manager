@echo off
title PET Business Manager - Create Portable Package
echo.
echo  Creating portable package for sharing...
echo.

cd /d "%~dp0"

set "ZIPNAME=PET-Business-Manager.zip"
set "DEST=%USERPROFILE%\Desktop\%ZIPNAME%"

:: Remove old zip if exists
if exist "%DEST%" del "%DEST%"

:: Use PowerShell to create ZIP excluding node_modules, __pycache__, data, uploads
powershell -NoProfile -Command ^
  "$source = '%~dp0'.TrimEnd('\');" ^
  "$dest = '%DEST%';" ^
  "$temp = Join-Path $env:TEMP 'pet_package';" ^
  "if (Test-Path $temp) { Remove-Item $temp -Recurse -Force };" ^
  "New-Item $temp -ItemType Directory | Out-Null;" ^
  "$exclude = @('node_modules','__pycache__','data','uploads','.git','package.zip','PET-Business-Manager.zip','tally_check.py','tally_check2.py','migrate_taxable.py');" ^
  "Get-ChildItem $source -Recurse | Where-Object { $rel = $_.FullName.Substring($source.Length+1); $skip = $false; foreach($e in $exclude) { if ($rel -like \"$e*\" -or $rel -like \"*\$e*\") { $skip = $true; break } }; -not $skip } | ForEach-Object { $destPath = Join-Path $temp $_.FullName.Substring($source.Length+1); if ($_.PSIsContainer) { New-Item $destPath -ItemType Directory -Force | Out-Null } else { $parent = Split-Path $destPath -Parent; if (!(Test-Path $parent)) { New-Item $parent -ItemType Directory -Force | Out-Null }; Copy-Item $_.FullName $destPath } };" ^
  "Compress-Archive -Path \"$temp\*\" -DestinationPath $dest -Force;" ^
  "Remove-Item $temp -Recurse -Force;" ^
  "Write-Host \"Package created: $dest\";"

echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║  Package created on your Desktop:                 ║
echo  ║  %ZIPNAME%                              ║
echo  ║                                                   ║
echo  ║  TO INSTALL ON ANOTHER PC:                        ║
echo  ║  1. Copy the ZIP to the other PC                  ║
echo  ║  2. Extract it anywhere                           ║
echo  ║  3. Double-click install.bat                      ║
echo  ║     (it installs everything automatically)        ║
echo  ║  4. Double-click start.bat to launch              ║
echo  ╚══════════════════════════════════════════════════╝
echo.
pause
