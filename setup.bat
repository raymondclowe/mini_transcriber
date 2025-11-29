@echo off
REM Windows setup script for mini_transcriber (batch file wrapper)
REM This script runs setup.ps1 using PowerShell
REM For full functionality, run setup.ps1 directly in PowerShell

echo === mini_transcriber Windows Setup ===
echo.

REM Check if PowerShell is available
where powershell >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: PowerShell is required but not found.
    echo Please run setup.ps1 directly in PowerShell or install PowerShell.
    exit /b 1
)

REM Run the PowerShell setup script
powershell -ExecutionPolicy Bypass -File "%~dp0setup.ps1" %*

if %ERRORLEVEL% neq 0 (
    echo.
    echo Setup failed. Please check the error messages above.
    exit /b 1
)

echo.
echo Setup completed successfully.
