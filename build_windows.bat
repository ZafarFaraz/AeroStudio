@echo off
setlocal
cd /d "%~dp0"
title AeroStudio Windows Builder

echo.
echo ==================================================
echo             AeroStudio Windows Builder
echo ==================================================
echo.

set "PYTHON_CMD="
where py >nul 2>nul
if not errorlevel 1 (
    py -3.14 -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 14) else 1)" >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=py -3.14"
)

if not defined PYTHON_CMD (
    where python >nul 2>nul
    if not errorlevel 1 (
        python -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 14) else 1)" >nul 2>nul
        if not errorlevel 1 set "PYTHON_CMD=python"
    )
)

if not defined PYTHON_CMD goto :python_missing

if not exist ".venv-windows\Scripts\python.exe" (
    echo [1/4] Creating the Windows build environment...
    %PYTHON_CMD% -m venv .venv-windows
    if errorlevel 1 goto :failed
) else (
    echo [1/4] Using the existing Windows build environment.
)

call ".venv-windows\Scripts\activate.bat"
if errorlevel 1 goto :failed

echo [2/4] Installing build tools...
python -m pip install --upgrade pip
if errorlevel 1 goto :failed
python -m pip install -r requirements-build.txt
if errorlevel 1 goto :failed

echo [3/4] Building AeroStudio.exe...
python tools\build_app.py
if errorlevel 1 goto :failed

echo [4/4] Creating the distribution ZIP...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$zip='dist\AeroStudio-Windows.zip'; if (Test-Path $zip) { Remove-Item -Force $zip }; Compress-Archive -Path 'dist\AeroStudio' -DestinationPath $zip -CompressionLevel Optimal"
if errorlevel 1 goto :failed

echo.
echo Build complete.
echo.
echo EXE folder:
echo   %CD%\dist\AeroStudio\AeroStudio.exe
echo.
echo File to distribute:
echo   %CD%\dist\AeroStudio-Windows.zip
echo.
pause
exit /b 0

:python_missing
echo.
echo Python 3.14 was not found.
echo Install Python 3.14 from https://www.python.org/downloads/windows/
echo During installation, select "Add Python to PATH", then run this file again.
echo.
pause
exit /b 1

:failed
echo.
echo The build stopped because one of the steps failed.
echo Read the message above, fix the problem, then run build_windows.bat again.
echo.
pause
exit /b 1
