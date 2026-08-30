@echo off
setlocal
cd /d "%~dp0"
title AeroStudio Windows Builder

echo.
echo ==================================================
echo             AeroStudio Windows Builder
echo ==================================================
echo.

if not exist "packaging\AeroStudio.spec" goto :project_incomplete
if not exist "tools\build_app.py" goto :project_incomplete
if not exist "requirements-build.txt" goto :project_incomplete

set "PYTHON_CMD="
where py >nul 2>nul
if not errorlevel 1 (
    for %%V in (3.12 3.13 3.14 3.11 3.10) do (
        if not defined PYTHON_CMD (
            py -%%V -c "import sys; raise SystemExit(0 if (3, 10) le sys.version_info[:2] le (3, 14) else 1)" >nul 2>nul
            if not errorlevel 1 set "PYTHON_CMD=py -%%V"
        )
    )
)

if not defined PYTHON_CMD (
    where python >nul 2>nul
    if not errorlevel 1 (
        python -c "import sys; raise SystemExit(0 if (3, 10) le sys.version_info[:2] le (3, 14) else 1)" >nul 2>nul
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
if not defined CI pause
exit /b 0

:python_missing
echo.
echo A supported Python version was not found.
echo Install Python 3.12 from https://www.python.org/downloads/windows/
echo During installation, select "Add Python to PATH", then run this file again.
echo.
if not defined CI pause
exit /b 1

:project_incomplete
echo.
echo This project copy is incomplete.
echo The builder needs packaging\AeroStudio.spec, tools\build_app.py,
echo and requirements-build.txt in the same AeroStudio project folder.
echo Download or clone the complete repository, then run this file from there.
echo.
if not defined CI pause
exit /b 1

:failed
echo.
echo The build stopped because one of the steps failed.
echo Read the message above, fix the problem, then run build_windows.bat again.
echo.
if not defined CI pause
exit /b 1
