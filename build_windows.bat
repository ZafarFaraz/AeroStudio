@echo off
setlocal
cd /d "%~dp0"
title AeroStudio Windows Builder

set "BUILD_ONLY="
if /I "%~1"=="--build-only" set "BUILD_ONLY=1"

echo.
echo ==================================================
echo             AeroStudio Windows Builder
echo ==================================================
echo.

if not exist "packaging\AeroStudio.spec" goto :project_incomplete
if not exist "tools\build_app.py" goto :project_incomplete
if not exist "tools\check_build_python.py" goto :project_incomplete
if not exist "requirements-build.txt" goto :project_incomplete

set "PYTHON_CMD="
where py >nul 2>nul
if not errorlevel 1 (
    for %%V in (3.12 3.13 3.14 3.11 3.10) do (
        if not defined PYTHON_CMD (
            py -%%V tools\check_build_python.py >nul 2>nul
            if not errorlevel 1 set "PYTHON_CMD=py -%%V"
        )
    )
)

if not defined PYTHON_CMD (
    where python >nul 2>nul
    if not errorlevel 1 (
        python tools\check_build_python.py >nul 2>nul
        if not errorlevel 1 set "PYTHON_CMD=python"
    )
)

if not defined PYTHON_CMD goto :python_missing

if not exist ".venv-windows\Scripts\python.exe" (
    echo [1/5] Creating the Windows build environment...
    %PYTHON_CMD% -m venv .venv-windows
    if errorlevel 1 goto :failed
) else (
    echo [1/5] Using the existing Windows build environment.
)

call ".venv-windows\Scripts\activate.bat"
if errorlevel 1 goto :failed
python tools\check_build_python.py
if errorlevel 1 goto :python_unsupported

echo [2/5] Installing build tools...
python -m pip install --upgrade pip
if errorlevel 1 goto :failed
python -m pip install -r requirements-build.txt
if errorlevel 1 goto :failed

echo [3/5] Building AeroStudio.exe...
python tools\build_app.py
if errorlevel 1 goto :failed

if defined BUILD_ONLY goto :build_complete

echo [4/5] Smoke-testing AeroStudio.exe...
start "" /wait "dist\AeroStudio\AeroStudio.exe" --startup-smoke-test --startup-smoke-report "build\windows-startup-smoke.log"
if errorlevel 1 (
    type "build\windows-startup-smoke.log" 2>nul
    goto :failed
)
type "build\windows-startup-smoke.log"

echo [5/5] Creating the distribution ZIP...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$zip='dist\AeroStudio-Windows.zip'; if (Test-Path $zip) { Remove-Item -Force $zip }; Compress-Archive -Path 'dist\AeroStudio' -DestinationPath $zip -CompressionLevel Optimal"
if errorlevel 1 goto :failed

:build_complete
echo.
echo Build complete.
echo.
echo EXE folder:
echo   %CD%\dist\AeroStudio\AeroStudio.exe
echo.
if defined BUILD_ONLY goto :success
echo File to distribute:
echo   %CD%\dist\AeroStudio-Windows.zip
echo.
:success
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

:python_unsupported
echo.
echo The existing Windows build environment uses an unsupported Python version.
echo Python 3.10.0 cannot be used by the current PyInstaller release.
echo Delete .venv-windows and install Python 3.10.1 or newer, then run this file again.
echo.
if not defined CI pause
exit /b 1

:project_incomplete
echo.
echo This project copy is incomplete.
echo The builder needs packaging\AeroStudio.spec, tools\build_app.py,
echo tools\check_build_python.py, and requirements-build.txt in the same project folder.
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
