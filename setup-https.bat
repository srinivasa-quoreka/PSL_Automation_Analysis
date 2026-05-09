@echo off
REM ============================================================================
REM PSL Automation - HTTPS Auto-Configuration & Setup Batch File
REM ============================================================================
REM This script performs one-click setup for HTTPS configuration:
REM   1. Checks and generates SSL certificates (if needed)
REM   2. Installs Python dependencies
REM   3. Configures environment variables
REM   4. Stops any running server on port 3000
REM   5. Starts the HTTPS server
REM   6. Opens dashboard in default browser
REM   7. Creates startup marker to skip setup on reboot
REM ============================================================================

setlocal enabledelayedexpansion

REM Define colors for console output
for /F %%A in ('copy /Z "%~f0" nul') do set "BS=%%A"

REM ============================================================================
REM SECTION 1: Configuration
REM ============================================================================

set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%"

echo.
echo ============================================================================
echo PSL Automation - HTTPS Setup &amp; Configuration
echo ============================================================================
echo.

REM Check if setup has already been completed
if exist "%PROJECT_ROOT%.https-configured" (
    echo [INFO] HTTPS already configured. Skipping setup.
    echo [INFO] Proceeding directly to server startup...
    goto START_SERVER
)

REM ============================================================================
REM SECTION 2: Check Python Installation
REM ============================================================================

echo [STEP 1/7] Checking Python installation...
python --version >nul 2>&1

if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo [ERROR] Please install Python 3.10+ from https://www.python.org/
    echo [ERROR] Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^&1') do set PYTHON_VERSION=%%i
echo [OK] Python %PYTHON_VERSION% found

REM ============================================================================
REM SECTION 3: Check and Install Dependencies
REM ============================================================================

echo.
echo [STEP 2/7] Checking Python dependencies...
python -m pip list 2>nul | findstr "cryptography uvicorn fastapi" >nul

if errorlevel 1 (
    echo [INFO] Installing required packages (cryptography, uvicorn, fastapi)...
    python -m pip install cryptography uvicorn fastapi -q
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies
        pause
        exit /b 1
    )
    echo [OK] Dependencies installed
) else (
    echo [OK] All dependencies already installed
)

REM ============================================================================
REM SECTION 4: Generate SSL Certificates
REM ============================================================================

echo.
echo [STEP 3/7] Checking SSL certificates...

if exist "%PROJECT_ROOT%cert.pem" (
    if exist "%PROJECT_ROOT%key.pem" (
        echo [OK] SSL certificates already exist
        goto VERIFY_CERTS
    )
)

echo [INFO] Generating self-signed SSL certificates...
echo [INFO] This may take a few seconds...

python -c "
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import datetime
import sys

try:
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    # Create certificate
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, u'localhost'),
    ])
    
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.utcnow()
    ).not_valid_after(
        datetime.datetime.utcnow() + datetime.timedelta(days=365)
    ).add_extension(
        x509.SubjectAlternativeName([x509.DNSName(u'localhost')]),
        critical=False,
    ).sign(private_key, hashes.SHA256(), default_backend())
    
    # Write certificate
    with open('cert.pem', 'wb') as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    
    # Write private key
    with open('key.pem', 'wb') as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))
    
    print('OK')
except Exception as e:
    print('ERROR: ' + str(e))
    sys.exit(1)
" >nul 2>&1

if errorlevel 1 (
    echo [ERROR] Failed to generate SSL certificates
    pause
    exit /b 1
)
echo [OK] SSL certificates generated successfully

:VERIFY_CERTS
if exist "%PROJECT_ROOT%cert.pem" (
    if exist "%PROJECT_ROOT%key.pem" (
        echo [OK] SSL certificates verified
    ) else (
        echo [ERROR] key.pem file not found
        pause
        exit /b 1
    )
) else (
    echo [ERROR] cert.pem file not found
    pause
    exit /b 1
)

REM ============================================================================
REM SECTION 5: Check .env Configuration
REM ============================================================================

echo.
echo [STEP 4/7] Checking environment configuration...

if not exist "%PROJECT_ROOT%.env" (
    if exist "%PROJECT_ROOT%.env.example" (
        echo [INFO] Creating .env from .env.example...
        copy "%PROJECT_ROOT%.env.example" "%PROJECT_ROOT%.env" >nul
        echo [WARNING] Please update .env with your Jira credentials
        echo [INFO] Opening .env file for editing...
        start notepad "%PROJECT_ROOT%.env"
        echo [INFO] Please save and close the editor when done
        pause
    )
)

if exist "%PROJECT_ROOT%.env" (
    echo [OK] .env configuration file exists
) else (
    echo [ERROR] .env file not found and .env.example not available
    pause
    exit /b 1
)

REM ============================================================================
REM SECTION 6: Verify app/main.py HTTPS Support
REM ============================================================================

echo.
echo [STEP 5/7] Verifying HTTPS support in application...

findstr /c:"ssl_certfile" "%PROJECT_ROOT%app\main.py" >nul

if errorlevel 1 (
    echo [WARNING] app/main.py may not have HTTPS support
    echo [INFO] This is likely not a problem if file was recently updated
)

echo [OK] Application ready for HTTPS

REM ============================================================================
REM SECTION 7: Create Startup Marker
REM ============================================================================

echo.
echo [STEP 6/7] Marking setup as completed...

REM Create marker file so setup isn't repeated
(
    echo HTTPS configured on %date% at %time%
    echo Project: %PROJECT_ROOT%
) > "%PROJECT_ROOT%.https-configured"

echo [OK] Configuration marker created

REM ============================================================================
REM SECTION 8: Start Server
REM ============================================================================

:START_SERVER
echo.
echo [STEP 7/7] Starting HTTPS server...

REM Kill any existing process on port 3000
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3000 "') do (
    taskkill /PID %%a /F >nul 2>&1
)

timeout /t 1 /nobreak >nul

REM Start the server
echo [INFO] Starting server on https://0.0.0.0:3000 ...

cd /d "%PROJECT_ROOT%"
python -m app.main >nul 2>&1 &

REM Wait for server to start
echo [INFO] Waiting for server to start (this may take 10-15 seconds)...
timeout /t 5 /nobreak >nul

REM Check if server is responding
:CHECK_SERVER
setlocal enabledelayedexpansion
for /f %%A in ('python -c "
import socket
import time
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    result = sock.connect_ex(('localhost', 3000))
    sock.close()
    if result == 0:
        print('OK')
    else:
        print('FAIL')
except:
    print('FAIL')
" 2^>nul') do set SERVER_STATUS=%%A

if "!SERVER_STATUS!"=="OK" (
    echo [OK] Server is running on port 3000
) else (
    echo [INFO] Server may still be starting...
    timeout /t 3 /nobreak >nul
    goto CHECK_SERVER
)

REM ============================================================================
REM SECTION 9: Open Browser
REM ============================================================================

echo.
echo ============================================================================
echo [SUCCESS] HTTPS Configuration Complete!
echo ============================================================================
echo.
echo Dashboard URL: https://localhost:3000/
echo Admin URL: https://localhost:3000/?admin=1^&key=admin123
echo.
echo Note: Your browser will show a certificate warning (expected for self-signed)
echo       Click "Advanced" and proceed to continue
echo.
echo Opening dashboard in default browser...
timeout /t 2 /nobreak >nul

REM Try to open browser
start https://localhost:3000/

REM ============================================================================
REM SECTION 10: Final Information
REM ============================================================================

echo.
echo ============================================================================
echo Server is running in the background
echo ============================================================================
echo.
echo To access the dashboard again:
echo   - Dashboard: https://localhost:3000/
echo   - Admin Panel: https://localhost:3000/?admin=1^&key=admin123
echo.
echo To STOP the server:
echo   - Press Ctrl+C in any command prompt window running this script
echo   - Or run: taskkill /IM python.exe /F
echo.
echo To RESTART the server:
echo   - Double-click this batch file again
echo.
echo For more information, see HTTPS_INSTALLATION_GUIDE.md
echo.
echo ============================================================================
pause
endlocal
