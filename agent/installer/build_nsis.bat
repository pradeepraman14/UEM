@echo off
REM ============================================================
REM  Build UEM Agent installer using NSIS
REM  Prerequisites:
REM    1. NSIS 3.x installed (makensis on PATH)
REM    2. UEMAgent.exe built by build_installer.py (in ..\dist\)
REM    3. Optional: ca.crt placed next to this script to bundle CA cert
REM ============================================================

setlocal

SET SCRIPT_DIR=%~dp0
SET DIST_DIR=%SCRIPT_DIR%..\dist

echo [*] Checking prerequisites...

where makensis >nul 2>&1
if errorlevel 1 (
    echo [!] makensis not found. Install NSIS from https://nsis.sourceforge.io/
    exit /b 1
)

if not exist "%DIST_DIR%\UEMAgent.exe" (
    echo [!] UEMAgent.exe not found at %DIST_DIR%\UEMAgent.exe
    echo [!] Run "python build_installer.py" first.
    exit /b 1
)

echo [*] Building NSIS installer...
makensis "%SCRIPT_DIR%uem_agent.nsi"

if errorlevel 1 (
    echo [!] NSIS build failed.
    exit /b 1
)

echo [+] Installer built: %SCRIPT_DIR%UEMAgentSetup-1.0.0.exe
echo.
echo Usage:
echo   Interactive:  UEMAgentSetup-1.0.0.exe
echo   Silent:       UEMAgentSetup-1.0.0.exe /S /SERVER=https://your-server /TOKEN=your-token

endlocal
