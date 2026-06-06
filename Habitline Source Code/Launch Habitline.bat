@echo off
setlocal
set "APP=%~dp0habit_tracker.py"
set "EXPECTED_VERSION=4.6"

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='SilentlyContinue'; $app=Invoke-RestMethod 'http://127.0.0.1:8779/api/version' -TimeoutSec 2; if ($app.name -eq 'Habitline' -and $app.version -ne '%EXPECTED_VERSION%') { $listener=Get-NetTCPConnection -LocalPort 8779 -State Listen | Select-Object -First 1; if ($listener) { Stop-Process -Id $listener.OwningProcess -Force; Start-Sleep -Milliseconds 600 } }"

set "BUNDLED=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\pythonw.exe"
if exist "%BUNDLED%" (
    start "" "%BUNDLED%" "%APP%"
    exit /b
)

where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw "%APP%"
    exit /b
)

where python >nul 2>nul
if %errorlevel%==0 (
    python "%APP%"
    exit /b
)

where py >nul 2>nul
if %errorlevel%==0 (
    py "%APP%"
    exit /b
)

set "BUNDLED=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%BUNDLED%" (
    start "" "%BUNDLED%" "%APP%"
    exit /b
)

echo Python 3 was not found. Install Python from python.org, then open this launcher again.
pause
