@echo off
REM ============================================================================
REM PSL Automation - Auto-Startup Batch File (Optional)
REM ============================================================================
REM This script starts the HTTPS server without setup prompts
REM Place this in Windows Startup folder for automatic startup on reboot
REM ============================================================================

setlocal enabledelayedexpansion

REM Project root directory (adjust if needed)
set "PROJECT_ROOT=%~dp0"

REM Navigate to project directory
cd /d "%PROJECT_ROOT%"

REM ============================================================================
REM Check if .https-configured marker exists
REM ============================================================================

if not exist "%PROJECT_ROOT%.https-configured" (
    echo [ERROR] Setup not completed. Please run setup-https.bat first.
    timeout /t 3 >nul
    exit /b 1
)

REM ============================================================================
REM Kill any existing process on port 3000
REM ============================================================================

for /f "tokens=5" %%a in ('netstat -aon 2>nul ^| findstr ":3000 "') do (
    taskkill /PID %%a /F >nul 2>&1
)

timeout /t 1 /nobreak >nul

REM ============================================================================
REM Start the server silently
REM ============================================================================

python -m app.main >"%PROJECT_ROOT%server.log" 2>&1 &

REM Wait briefly for server to start
timeout /t 3 /nobreak >nul

REM ============================================================================
REM Verify server is running
REM ============================================================================

for /f %%A in ('python -c "
import socket
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    result = sock.connect_ex(('localhost', 3000))
    sock.close()
    print('OK' if result == 0 else 'FAIL')
except:
    print('FAIL')
" 2^>nul') do set SERVER_STATUS=%%A

if "!SERVER_STATUS!"=="OK" (
    REM Server started successfully
    exit /b 0
) else (
    REM Server failed to start, log the error
    echo ERROR: Server failed to start at %date% %time% >> "%PROJECT_ROOT%startup.log"
    exit /b 1
)

endlocal
