@echo off
REM ── Launch Chrome with CDP debug port for JARVIS ──
REM Uses your REAL Chrome profile so all logins (WhatsApp, Gmail, etc.) persist!

set CHROME_PATH="C:\Program Files\Google\Chrome\Application\chrome.exe"
set CDP_PORT=9222
set PROFILE_DIR=%LOCALAPPDATA%\Google\Chrome\User Data

echo.
echo ======================================
echo   JARVIS - Chrome CDP Launcher
echo   Port: %CDP_PORT%
echo   Profile: %PROFILE_DIR%
echo ======================================
echo.

REM Check if Chrome is already running
tasklist /FI "IMAGENAME eq chrome.exe" 2>NUL | find /I /N "chrome.exe" >NUL
if %errorlevel%==0 (
    echo [WARN] Chrome is already running.
    echo [WARN] Closing Chrome to relaunch with CDP...
    taskkill /IM chrome.exe /F >NUL 2>&1
    timeout /t 3 >NUL
)

echo [INFO] Starting Chrome with remote debugging...
start "" %CHROME_PATH% --remote-debugging-port=%CDP_PORT% --user-data-dir="%PROFILE_DIR%" --no-first-run --no-default-browser-check --start-maximized --restore-last-session

echo.
echo [OK] Chrome launched with CDP on port %CDP_PORT%!
echo [OK] All your logins (WhatsApp, Gmail, LinkedIn) are preserved.
echo.
echo Now run: python -m jarvis --cli
echo.
pause
