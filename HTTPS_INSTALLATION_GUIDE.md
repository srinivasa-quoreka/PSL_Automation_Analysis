# HTTPS Installation & Configuration Guide

Complete step-by-step guide for setting up and running the PSL Automation Dashboard on HTTPS.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Understanding HTTPS in PSL Automation](#understanding-https-in-psl-automation)
3. [Certificate Files](#certificate-files)
4. [Step-by-Step Setup](#step-by-step-setup)
5. [Running in HTTPS Mode](#running-in-https-mode)
6. [Accessing the Dashboard](#accessing-the-dashboard)
7. [Certificate Management](#certificate-management)
8. [Troubleshooting](#troubleshooting)
9. [Production Deployment](#production-deployment)

---

## Prerequisites

### System Requirements
- **Operating System**: Windows 10+, macOS, or Linux
- **Python**: 3.10 or higher (verify: `python --version`)
- **Port**: 3000 (must be available/open)
- **Network**: Local network or internal network access

### Required Python Packages
The following packages are already included in `requirements.txt`:
- `cryptography` — For SSL certificate handling
- `uvicorn` — ASGI server with HTTPS support
- `fastapi` — Web framework

Verify installation:
```bash
pip list | findstr cryptography uvicorn fastapi
```

---

## Understanding HTTPS in PSL Automation

### How It Works

The PSL Automation server automatically detects SSL certificate files and enables HTTPS:

```
┌─ Server Startup ─────────────────────────┐
│                                          │
│  1. Check for cert.pem & key.pem        │
│  2. If both exist → Enable HTTPS        │
│  3. If missing → Run on HTTP            │
│                                          │
└──────────────────────────────────────────┘
```

### Certificate Types

| Type | Best For | Cost | Validation |
|------|----------|------|-----------|
| **Self-Signed** | Internal networks, testing, development | Free | Manual acceptance |
| **CA-Signed** | Production, public internet | $$ | Automatic trust |
| **Let's Encrypt** | Production, public internet | Free | Automatic trust |

**Current Setup**: Self-signed certificates (suitable for internal networks)

---

## Certificate Files

### What You Need

Two files must be present in the **project root directory** (`d:\Claude\PSL Automation\PSL Automation\`):

| File | Purpose | Size | Format |
|------|---------|------|--------|
| `cert.pem` | SSL Certificate (public) | ~1 KB | PEM-encoded X.509 |
| `key.pem` | Private Key | ~2 KB | PEM-encoded RSA |

### File Locations

**Correct Location**:
```
d:\Claude\PSL Automation\PSL Automation\
├── cert.pem           ← Certificate file
├── key.pem            ← Private key file
├── app/
├── README.md
├── requirements.txt
└── start.ps1
```

**Verify Files Exist**:
```powershell
Get-Item "d:\Claude\PSL Automation\PSL Automation\cert.pem", "d:\Claude\PSL Automation\PSL Automation\key.pem"
```

Expected output:
```
FullName                                         Length
--------                                         ------
D:\Claude\PSL Automation\PSL Automation\cert.pem   1050
D:\Claude\PSL Automation\PSL Automation\key.pem    1675
```

### What NOT to Do

❌ **Do NOT**:
- Store certificates in `app/` folder
- Rename the files
- Share the `key.pem` file publicly
- Commit `key.pem` to git
- Edit certificates manually

✅ **DO**:
- Store both files in the project root
- Keep filenames exactly as `cert.pem` and `key.pem`
- Add certificates to `.gitignore` (already done)
- Regenerate if compromised

---

## Step-by-Step Setup

### Step 1: Navigate to Project Directory

```powershell
cd "d:\Claude\PSL Automation\PSL Automation"
```

### Step 2: Check for Existing Certificates

```powershell
Test-Path "cert.pem" -PathType Leaf
Test-Path "key.pem" -PathType Leaf
```

**If both return `True`**: Skip to Step 4 (certificates already exist)

**If either returns `False`**: Continue to Step 3 (generate certificates)

### Step 3: Generate Self-Signed Certificates

#### Option A: Using Python (Recommended)

```powershell
python -c "
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import datetime

print('Generating self-signed SSL certificate...')

# Generate private key (RSA 2048-bit)
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

# Write certificate file
with open('cert.pem', 'wb') as f:
    f.write(cert.public_bytes(serialization.Encoding.PEM))
    print('✓ cert.pem created')

# Write private key file
with open('key.pem', 'wb') as f:
    f.write(private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    ))
    print('✓ key.pem created')

print('✓ SSL certificates generated successfully')
print('✓ Valid for 365 days')
"
```

**Expected Output**:
```
Generating self-signed SSL certificate...
✓ cert.pem created
✓ key.pem created
✓ SSL certificates generated successfully
✓ Valid for 365 days
```

#### Option B: Using OpenSSL (If Python fails)

```bash
# Generate private key
openssl genrsa -out key.pem 2048

# Generate certificate (valid 365 days)
openssl req -new -x509 -key key.pem -out cert.pem -days 365 \
  -subj "/CN=localhost"
```

#### Option C: Using PowerShell (.NET)

```powershell
# This requires .NET installed
$cert = New-SelfSignedCertificate -CertStoreLocation cert:\CurrentUser\My `
  -DnsName "localhost" -NotAfter (Get-Date).AddDays(365)

# Export certificate
Export-Certificate -Cert $cert -FilePath "cert.pem"

# Export private key
$mypwd = ConvertTo-SecureString -String "password" -Force -AsPlainText
Export-PfxCertificate -Cert $cert -FilePath "temp.pfx" -Password $mypwd
```

### Step 4: Verify Certificate Installation

```powershell
# Verify files exist and have correct size
Get-Item cert.pem, key.pem | Format-Table Name, Length

# View certificate details
openssl x509 -in cert.pem -text -noout
```

**Expected Output**:
```
    Name    Length
    ----    ------
cert.pem   1050
key.pem    1675

Subject: CN = localhost
Not Before: May  9 10:00:00 2026 GMT
Not After : May  9 10:00:00 2027 GMT
```

### Step 5: Update .env Configuration (Optional)

Verify `.env` file has the correct port:

```bash
cat .env | findstr PORT
```

Example `.env`:
```
PORT=3000
JIRA_BASE_URL=https://jira.ekaplus.com
JIRA_USERNAME=your-email@example.com
JIRA_PASSWORD=your-api-token
```

### Step 6: Verify app/main.py Has HTTPS Support

Check that `app/main.py` includes the HTTPS configuration:

```powershell
findstr "ssl_certfile" app/main.py
```

Expected output:
```
ssl_certfile=str(cert_file),
ssl_keyfile=str(key_file),
ssl_version=17  # TLS 1.2
```

If missing, the file should already have this from the current codebase.

---

## Running in HTTPS Mode

### Method 1: Using start.ps1 (Recommended)

The `start.ps1` script automatically detects certificates and enables HTTPS:

```powershell
cd "d:\Claude\PSL Automation\PSL Automation"
.\start.ps1
```

**Expected Output**:
```
PSL Automation - Starting Dashboard...
Working directory: D:\Claude\PSL Automation\PSL Automation
Jira Base URL: https://jira.ekaplus.com
Port: 3000

Starting server...
INFO:     Started server process [28736]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on https://0.0.0.0:3000 (Press CTRL+C to quit)
```

✅ **If you see `https://0.0.0.0:3000`**: HTTPS is enabled!
❌ **If you see `http://0.0.0.0:3000`**: Certificates are missing or invalid

### Method 2: Direct Python Execution

```powershell
python -m app.main
```

### Method 3: Using Uvicorn Directly

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 3000 --ssl-certfile=cert.pem --ssl-keyfile=key.pem
```

### Method 4: Using PowerShell with Environment Variables

```powershell
$env:PORT=3000
python -m app.main
```

### Stop the Server

```powershell
# Method 1: Press Ctrl+C in the terminal

# Method 2: Kill the process
Get-NetTCPConnection -LocalPort 3000 -State Listen | ForEach-Object { 
    Stop-Process -Id $_.OwningProcess -Force 
}
```

---

## Accessing the Dashboard

### Browser Access (All Platforms)

The dashboard will show a **certificate warning** (this is expected for self-signed certificates).

#### Chrome/Edge:
1. Navigate to `https://localhost:3000` or `https://172.16.0.140:3000`
2. You'll see: **"Your connection is not private"**
3. Click **Advanced**
4. Click **Proceed to https://localhost:3000 (unsafe)**
5. Dashboard loads (connection is still encrypted)

#### Firefox:
1. Navigate to `https://localhost:3000` or `https://172.16.0.140:3000`
2. You'll see: **"Warning: Potential Security Risk Ahead"**
3. Click **Advanced**
4. Click **Accept the Risk and Continue**
5. Dashboard loads

#### Safari (macOS):
1. Navigate to `https://localhost:3000`
2. Click **Show Details**
3. Click **visit this website**
4. Dashboard loads

### Public URL Access

**Local Network (recommended for internal use)**:
```
https://172.16.0.140:3000/
```

**Localhost (same computer)**:
```
https://localhost:3000/
```

### Admin Access

Add the admin key parameter:
```
https://172.16.0.140:3000/?admin=1&key=admin123
```

Replace `admin123` with your admin key from `.env` file.

### API Access via cURL

```bash
# Bypass certificate validation (self-signed)
curl -k https://localhost:3000/api/published-state

# With verbose output
curl -v -k https://localhost:3000/api/health
```

### API Access via Python

```python
import requests
from urllib3.exceptions import InsecureRequestWarning

# Disable certificate warnings (self-signed)
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Make request
response = requests.get(
    'https://localhost:3000/api/published-state',
    verify=False,  # Ignore certificate validation
    timeout=10
)

print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
```

### API Access via PowerShell

```powershell
# Bypass certificate validation
[System.Net.ServicePointManager]::ServerCertificateValidationCallback = { $true }

# Make request
$response = Invoke-RestMethod -Uri "https://localhost:3000/api/published-state" -Method GET

$response | ConvertTo-Json | Write-Host
```

---

## Certificate Management

### View Certificate Details

```powershell
# Using OpenSSL (if installed)
openssl x509 -in cert.pem -text -noout

# Using Python
python -c "
from cryptography import x509
from cryptography.hazmat.backends import default_backend

with open('cert.pem', 'rb') as f:
    cert = x509.load_pem_x509_certificate(f.read(), default_backend())
    print(f'Subject: {cert.subject}')
    print(f'Issuer: {cert.issuer}')
    print(f'Not Before: {cert.not_valid_before}')
    print(f'Not After: {cert.not_valid_after}')
    print(f'Serial Number: {cert.serial_number}')
"
```

### Regenerate Certificates (If Expired or Compromised)

```powershell
# 1. Remove old certificates
Remove-Item cert.pem, key.pem

# 2. Regenerate (run Python script from Step 3)
python -c "
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import datetime

private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
    backend=default_backend()
)

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

with open('cert.pem', 'wb') as f:
    f.write(cert.public_bytes(serialization.Encoding.PEM))

with open('key.pem', 'wb') as f:
    f.write(private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    ))

print('✓ New certificates generated (365 days validity)')
"

# 3. Restart server
Get-NetTCPConnection -LocalPort 3000 -State Listen | ForEach-Object { 
    Stop-Process -Id $_.OwningProcess -Force 
}
Start-Sleep -Milliseconds 500
.\start.ps1
```

### Use CA-Signed Certificates (Production)

To upgrade from self-signed to CA-signed certificates:

```powershell
# 1. Obtain certificate from Certificate Authority
#    - Let's Encrypt (free): https://letsencrypt.org/
#    - DigiCert, Sectigo, etc. (paid)
#    - Your organization's CA

# 2. Download certificate and private key files
#    Files should be in PEM format (.pem or .crt extension)

# 3. Replace local certificates
Copy-Item "path/to/new-cert.pem" "cert.pem" -Force
Copy-Item "path/to/new-key.pem" "key.pem" -Force

# 4. Verify
openssl x509 -in cert.pem -text -noout | findstr "Subject"

# 5. Restart server
Get-NetTCPConnection -LocalPort 3000 -State Listen | ForEach-Object { 
    Stop-Process -Id $_.OwningProcess -Force 
}
.\start.ps1
```

---

## Troubleshooting

### Issue 1: Server Running on HTTP Instead of HTTPS

**Problem**: Output shows `http://0.0.0.0:3000` instead of `https://0.0.0.0:3000`

**Causes**:
- Certificate files missing
- Files in wrong location
- Wrong filenames

**Solution**:
```powershell
# Check file existence
Test-Path cert.pem
Test-Path key.pem

# Correct location should be:
Get-Location  # Should show: D:\Claude\PSL Automation\PSL Automation

# Verify file content (should start with "-----BEGIN")
Get-Content cert.pem -Head 3
Get-Content key.pem -Head 3
```

### Issue 2: Certificate Warning in Browser

**Problem**: "Your connection is not private" error

**Solution**: This is **normal and expected** for self-signed certificates:
1. Click **Advanced**
2. Click **Proceed** (Chrome) or **Accept Risk** (Firefox)
3. Connection is still encrypted

### Issue 3: "Address already in use" Error

**Problem**: Port 3000 is already in use

**Solution**:
```powershell
# Kill existing process on port 3000
Get-NetTCPConnection -LocalPort 3000 -State Listen | ForEach-Object { 
    Stop-Process -Id $_.OwningProcess -Force 
}

# Wait and restart
Start-Sleep -Seconds 2
.\start.ps1
```

### Issue 4: "Module cryptography not found"

**Problem**: Import error when generating certificates

**Solution**:
```powershell
# Install missing package
pip install cryptography

# Or reinstall all requirements
pip install -r requirements.txt
```

### Issue 5: Certificate Validation Error in API Clients

**Problem**: Python/cURL requests fail with SSL verification error

**Solution**:
```python
# Python - Disable verification for self-signed
requests.get(url, verify=False)

# Python - Disable warnings
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# cURL
curl -k https://localhost:3000/api/health
```

### Issue 6: File Permissions Error

**Problem**: "Permission denied" when creating certificates

**Solution**:
```powershell
# Run PowerShell as Administrator
# Right-click PowerShell → "Run as administrator"

# Then retry certificate generation
python -c "..."
```

---

## Production Deployment

### Before Going to Production

✅ **Checklist**:
- [ ] Replace self-signed with CA-signed certificate (Let's Encrypt recommended)
- [ ] Update `.env` with production Jira instance
- [ ] Test all dashboard functionality over HTTPS
- [ ] Update firewall rules to allow port 3000/HTTPS
- [ ] Set up monitoring/alerting for certificate expiration
- [ ] Backup certificate files securely
- [ ] Document certificate renewal procedure
- [ ] Test disaster recovery (certificate regeneration)

### Certificate Renewal

**Self-Signed** (if keeping):
- Expires every 365 days
- Regenerate using the Python script above
- Update any browser/client caches

**Let's Encrypt** (recommended):
- Auto-renews every 90 days
- Use certbot or similar tool
- See: https://certbot.eff.org/

### Security Considerations

| Aspect | Development | Production |
|--------|-------------|-----------|
| **Certificate Type** | Self-signed | CA-signed |
| **Encryption** | TLS 1.2 | TLS 1.3+ |
| **Admin Key** | Simple (admin123) | Strong, rotate regularly |
| **Backup** | Optional | Daily encrypted backup |
| **Monitoring** | Optional | Enable logging & alerts |
| **Network** | Internal only | Firewall rules required |

### Recommended Production Settings

Update `.env` for production:

```env
# Server
PORT=3000
HOST=0.0.0.0

# Jira
JIRA_BASE_URL=https://your-production-jira.com
JIRA_USERNAME=service-account@company.com
JIRA_PASSWORD=secure-api-token-here

# Admin
ADMIN_KEY=your-secure-admin-key-here

# Logging
LOG_LEVEL=INFO
```

### Setting Up Auto-Renewal with Let's Encrypt

```bash
# 1. Install certbot
pip install certbot

# 2. Generate certificate
certbot certonly --standalone \
  -d yourdomain.com \
  --email admin@yourdomain.com

# 3. Copy to PSL Automation directory
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem cert.pem
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem key.pem

# 4. Set up auto-renewal cron job (Linux)
certbot renew --quiet --no-eff-email

# Add to crontab: 0 12 * * * certbot renew --quiet
```

---

## Quick Reference

### Start Server on HTTPS
```powershell
cd "d:\Claude\PSL Automation\PSL Automation"
.\start.ps1
```

### Verify HTTPS is Running
```bash
curl -k https://localhost:3000/api/health
```

### Access Dashboard
```
https://172.16.0.140:3000/?key=admin123
```

### Generate New Certificates
```powershell
python -c "
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import datetime

private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, u'localhost')])
cert = x509.CertificateBuilder().subject_name(subject).issuer_name(issuer).public_key(private_key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(datetime.datetime.utcnow()).not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365)).add_extension(x509.SubjectAlternativeName([x509.DNSName(u'localhost')]), critical=False).sign(private_key, hashes.SHA256(), default_backend())

with open('cert.pem', 'wb') as f:
    f.write(cert.public_bytes(serialization.Encoding.PEM))
with open('key.pem', 'wb') as f:
    f.write(private_key.private_bytes(encoding=serialization.Encoding.PEM, format=serialization.PrivateFormat.TraditionalOpenSSL, encryption_algorithm=serialization.NoEncryption()))
print('✓ Certificates generated')
"
```

### Check Certificate Validity
```bash
openssl x509 -in cert.pem -text -noout
```

---

## Support & Resources

### Documentation
- [HTTPS_SETUP.md](HTTPS_SETUP.md) - Quick reference guide
- [README.md](README.md) - Project overview
- [Cryptography Library](https://cryptography.io/) - Certificate generation

### External Links
- [Let's Encrypt](https://letsencrypt.org/) - Free CA-signed certificates
- [certbot](https://certbot.eff.org/) - Certificate automation
- [OpenSSL Documentation](https://www.openssl.org/docs/) - Certificate tools
- [RFC 5280](https://tools.ietf.org/html/rfc5280) - X.509 Certificate Standard

---

**Last Updated**: May 9, 2026  
**HTTPS Status**: ✅ Enabled  
**Certificate Type**: Self-Signed (365 days)  
**TLS Version**: 1.2+
