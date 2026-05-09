@echo off
REM ============================================================================
REM Quick Shortcut Creator for PSL Automation
REM ============================================================================
REM This script creates desktop shortcuts for easy access
REM Run once to create shortcuts, then use shortcuts anytime
REM ============================================================================

setlocal enabledelayedexpansion

set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%"

echo.
echo ============================================================================
echo PSL Automation - Shortcut Creator
echo ============================================================================
echo.

REM Get desktop path
for /f "tokens=3" %%a in ('reg query "HKEY_CURRENT_USER\Shell Folders" /v Desktop 2^>nul ^| findstr Desktop') do (
    set "DESKTOP=%%a"
)

if not defined DESKTOP (
    echo [ERROR] Could not find Desktop path
    pause
    exit /b 1
)

echo [INFO] Desktop location: %DESKTOP%

REM ============================================================================
REM Create VBScript to generate shortcuts
REM ============================================================================

set "VBS_FILE=%TEMP%\create-shortcuts.vbs"

(
    echo Set objWS = CreateObject("WScript.Shell"^)
    echo Set objFSO = CreateObject("Scripting.FileSystemObject"^)
    
    echo.
    echo REM Setup Shortcut
    echo Set objShortcut = objWS.CreateShortcut("%DESKTOP%\PSL Automation Setup.lnk"^)
    echo objShortcut.TargetPath = "%PROJECT_ROOT%setup-https.bat"
    echo objShortcut.WorkingDirectory = "%PROJECT_ROOT%"
    echo objShortcut.Description = "One-click HTTPS setup and server start"
    echo objShortcut.IconLocation = "%SystemRoot%\System32\shell32.dll, 108"
    echo objShortcut.WindowStyle = 1
    echo objShortcut.Save
    
    echo.
    echo REM Auto-Start Shortcut (for startup folder^)
    echo Set objShortcut2 = objWS.CreateShortcut("%DESKTOP%\PSL Auto-Start.lnk"^)
    echo objShortcut2.TargetPath = "%PROJECT_ROOT%start-server-silent.bat"
    echo objShortcut2.WorkingDirectory = "%PROJECT_ROOT%"
    echo objShortcut2.Description = "Auto-start HTTPS server (place in Startup folder^)"
    echo objShortcut2.IconLocation = "%SystemRoot%\System32\shell32.dll, 107"
    echo objShortcut2.WindowStyle = 7
    echo objShortcut2.Save
    
    echo.
    echo REM Dashboard Shortcut
    echo Set objShortcut3 = objWS.CreateShortcut("%DESKTOP%\PSL Dashboard.lnk"^)
    echo objShortcut3.TargetPath = "https://localhost:3000/"
    echo objShortcut3.Description = "Open PSL Automation Dashboard"
    echo objShortcut3.IconLocation = "%SystemRoot%\System32\shell32.dll, 69"
    echo objShortcut3.Save
    
    echo.
    echo REM Admin Dashboard Shortcut
    echo Set objShortcut4 = objWS.CreateShortcut("%DESKTOP%\PSL Admin Panel.lnk"^)
    echo objShortcut4.TargetPath = "https://localhost:3000/?admin=1^&key=admin123"
    echo objShortcut4.Description = "Open PSL Automation Admin Panel"
    echo objShortcut4.IconLocation = "%SystemRoot%\System32\shell32.dll, 12"
    echo objShortcut4.Save
    
    echo.
    echo WScript.Echo "Shortcuts created successfully"
) > "%VBS_FILE%"

echo [INFO] Running VBScript to create shortcuts...

cscript.exe "%VBS_FILE%" >nul 2>&1

if errorlevel 1 (
    echo [ERROR] Failed to create shortcuts
    pause
    exit /b 1
)

echo [OK] Shortcuts created on Desktop:
echo   - PSL Automation Setup.lnk       (Run full setup^)
echo   - PSL Auto-Start.lnk             (Place in Startup folder^)
echo   - PSL Dashboard.lnk              (Quick link to dashboard^)
echo   - PSL Admin Panel.lnk            (Quick link to admin^)

REM Clean up temp file
del "%VBS_FILE%" >nul 2>&1

echo.
echo ============================================================================
echo [SUCCESS] Shortcuts created!
echo ============================================================================
echo.
echo Next steps:
echo   1. Double-click "PSL Automation Setup.lnk" to run full setup
echo   2. (Optional) Move "PSL Auto-Start.lnk" to Windows Startup folder
echo      for automatic server start on reboot
echo.
echo To access Startup folder:
echo   - Press: Win+R
echo   - Type: shell:startup
echo   - Click: OK
echo   - Paste "PSL Auto-Start.lnk" there
echo.

pause
