# HTTPS Setup

The PSL Automation Dashboard now supports **HTTPS/TLS encryption** for secure data transmission.

## Current Setup

A **self-signed SSL certificate** has been generated:
- `cert.pem` - Certificate (valid for 365 days)
- `key.pem` - Private key

The server automatically detects these files and runs on **HTTPS** if they exist.

## Starting the Server

```bash
# HTTPS enabled (if cert.pem and key.pem exist)
python -m app.main

# Or with PowerShell
.\start.ps1
```

Expected output:
```
Uvicorn running on https://0.0.0.0:3000
```

## Accessing the Dashboard

### Browser Access (Self-Signed Certificate)

When accessing via browser, you'll see a certificate warning:

1. **Chrome/Edge**: Click "Advanced" → "Proceed to https://..."
2. **Firefox**: Click "Advanced" → "Accept the Risk and Continue"
3. **Safari**: Click "Show Details" → "visit this website"

Once accepted, the connection is encrypted with the same security as a CA-signed certificate.

### Using HTTPS with API Clients

#### Python `requests`
```python
import requests
from urllib3.exceptions import InsecureRequestWarning

# Bypass self-signed cert warning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

response = requests.get(
    'https://172.16.0.140:3000/api/published-state',
    verify=False  # Ignore certificate validation
)
```

#### curl
```bash
curl -k https://172.16.0.140:3000/api/published-state
```

#### PowerShell
```powershell
[System.Net.ServicePointManager]::ServerCertificateValidationCallback = { $true }
Invoke-RestMethod -Uri "https://172.16.0.140:3000/api/published-state" -Method GET
```

## Using CA-Signed Certificates (Production)

For production deployments, replace the self-signed cert with a CA-signed certificate:

1. **Obtain a certificate** from a Certificate Authority (Let's Encrypt, DigiCert, etc.)
2. **Replace files**:
   ```bash
   cp your-certificate.pem cert.pem
   cp your-private-key.pem key.pem
   ```
3. **Restart server** - it will use the new certificate

## Regenerating Self-Signed Certificate

To regenerate a new certificate (if expired or compromised):

```bash
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

print('✓ New SSL certificate generated')
"
```

## Security Notes

- **Self-signed certificates** are suitable for internal networks and testing
- **Production** should use CA-signed certificates
- **HTTPS encrypts data in transit** - admin key and test data are protected
- Certificates are **not stored in git** (added to `.gitignore`)
- Each server should **generate its own certificate**

## Verification

To verify HTTPS is working:

```bash
# Check if server is running on HTTPS
python -c "
import requests
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
r = requests.get('https://localhost:3000/api/published-state', verify=False)
print(f'✓ HTTPS OK - Status: {r.status_code}')
"
```

Expected output: `✓ HTTPS OK - Status: 200`
