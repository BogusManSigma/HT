@echo off
setlocal
net session >nul 2>nul
if %errorlevel% neq 0 (
  powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)

netsh advfirewall firewall delete rule name="Habitline Phone Sync" >nul 2>nul
netsh advfirewall firewall add rule name="Habitline Phone Sync" dir=in action=allow protocol=TCP localport=8779-8799 profile=private

echo.
echo Habitline phone access is enabled on private Wi-Fi networks.
echo Open Habitline, select Phone sync, and use the private link shown there.
pause
