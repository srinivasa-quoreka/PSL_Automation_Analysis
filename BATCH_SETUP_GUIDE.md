# One-Click HTTPS Setup Guide

Complete guide for using the automated batch file to configure HTTPS and run the dashboard.

---

## Overview

The `setup-https.bat` file automates the entire HTTPS setup process with a single click:
- ✅ Checks Python installation
- ✅ Installs dependencies automatically
- ✅ Generates SSL certificates
- ✅ Configures environment
- ✅ Starts HTTPS server
- ✅ Opens dashboard in browser
- ✅ Remembers configuration (no repeat setup)

**First Run**: Full setup (2-3 minutes)  
**Subsequent Runs**: Just starts server (10-15 seconds)

---

## Quick Start

### Step 1: First-Time Setup (One Click)

1. Navigate to: `d:\Claude\PSL Automation\PSL Automation\`
2. **Double-click** → `setup-https.bat`
3. Wait for setup to complete (2-3 minutes)
4. Browser opens automatically to dashboard

**That's it!** ✅ HTTPS is configured and running

### Step 2 (Optional): Configure Jira Credentials

If prompted:
1. A Notepad window opens with `.env` file
2. Add your Jira credentials:
   ```
   JIRA_BASE_URL=https://jira.ekaplus.com
   JIRA_USERNAME=your-email@example.com
   JIRA_PASSWORD=your-api-token
   ADMIN_KEY=admin123
   ```
3. Save (`Ctrl+S`) and close Notepad
4. Back in batch window, press any key to continue

### Step 3: Access Dashboard

After setup completes:
- **Main Dashboard**: `https://localhost:3000/`
- **Admin Panel**: `https://localhost:3000/?admin=1&key=admin123`

**Certificate Warning** (Expected):
- Click **Advanced**
- Click **Proceed** (Chrome) or **Accept Risk** (Firefox)
- Connection is encrypted (safe)

---

## What Each Batch File Does

### `setup-https.bat` (Main Setup)

**Purpose**: One-click installation and server startup

**What it does**:
1. Checks Python is installed (3.10+)
2. Installs/verifies dependencies
3. Generates SSL certificates (if needed)
4. Checks .env configuration
5. Creates setup marker file
6. Starts HTTPS server
7. Opens dashboard in default browser

**When to use**:
- First-time setup
- After system reboot
- When configuration changes
- To start/restart server

**How to run**:
```
Double-click: setup-https.bat
OR
Command line: setup-https.bat
```

**Output** (normal first run):
```
============================================================================
PSL Automation - HTTPS Setup & Configuration
============================================================================

[STEP 1/7] Checking Python installation...
[OK] Python 3.10.x found

[STEP 2/7] Checking Python dependencies...
[OK] All dependencies already installed

[STEP 3/7] Checking SSL certificates...
[INFO] Generating self-signed SSL certificates...
[OK] SSL certificates generated successfully

[STEP 4/7] Checking environment configuration...
[OK] .env configuration file exists

[STEP 5/7] Verifying HTTPS support in application...
[OK] Application ready for HTTPS

[STEP 6/7] Marking setup as completed...
[OK] Configuration marker created

[STEP 7/7] Starting HTTPS server...
[INFO] Starting server on https://0.0.0.0:3000...
[INFO] Waiting for server to start (this may take 10-15 seconds)...
[OK] Server is running on port 3000

============================================================================
[SUCCESS] HTTPS Configuration Complete!
============================================================================

Dashboard URL: https://localhost:3000/
Admin URL: https://localhost:3000/?admin=1&key=admin123

Opening dashboard in default browser...
```

### `start-server-silent.bat` (Silent Startup)

**Purpose**: Start server without setup prompts (for automation/scheduling)

**When to use**:
- Automated startup on system reboot
- Scheduled startup
- After setup is already complete
- Running from Startup folder

**How to run**:
```
start-server-silent.bat
```

**Does NOT show**:
- Setup prompts
- Interactive steps
- Browser open (silent mode)

**Logs output to**:
- `server.log` — Server output
- `startup.log` — Startup errors

---

## Persistent Configuration (Auto-Start on Reboot)

### Option A: Windows Startup Folder (Easiest)

1. **Create shortcut to batch file**:
   - Right-click `start-server-silent.bat`
   - Select **Send to** → **Desktop (create shortcut)**

2. **Move to Startup folder**:
   - Press `Win+R`
   - Type: `shell:startup`
   - Press Enter
   - Copy the shortcut here

3. **Test**:
   - Restart computer
   - Server should start automatically
   - Check `https://localhost:3000/`

### Option B: Windows Task Scheduler

1. **Open Task Scheduler**:
   - Press `Win+R`
   - Type: `taskschd.msc`
   - Press Enter

2. **Create Basic Task**:
   - Right-click → **Create Basic Task**
   - Name: "PSL Automation Server"
   - Description: "Auto-start HTTPS dashboard"

3. **Trigger**:
   - Click **Trigger** tab
   - New → **At system startup**

4. **Action**:
   - Click **Action** tab
   - New → **Start a program**
   - Program: `start-server-silent.bat`
   - Start in: `d:\Claude\PSL Automation\PSL Automation\`

5. **Finish** and save

6. **Test**:
   - Restart computer
   - Server should start automatically

### Option C: Batch File in Startup Folder

1. **Copy batch file to Startup**:
   ```powershell
   copy "start-server-silent.bat" "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\"
   ```

2. **Verify**:
   - Open Startup folder: `shell:startup`
   - `start-server-silent.bat` should be there

3. **Test**:
   - Restart computer
   - Server should start automatically

---

## Configuration Files Explained

### `.https-configured` Marker File

- **Location**: Project root directory
- **Purpose**: Remembers that setup has been completed
- **Content**: Timestamp of setup completion
- **Why**: Prevents re-running setup on every boot

**Example content**:
```
HTTPS configured on Fri 05/09/2026 at 10:30:45.23
Project: d:\Claude\PSL Automation\PSL Automation\
```

### `.env` Configuration

**Location**: Project root directory

**What it contains**:
```
JIRA_BASE_URL=https://jira.ekaplus.com
JIRA_USERNAME=your-email@example.com
JIRA_PASSWORD=your-api-token
ADMIN_KEY=admin123
PORT=3000
```

**Edit anytime**:
```
1. Open: d:\Claude\PSL Automation\PSL Automation\.env
2. Make changes
3. Save
4. Restart batch file
```

### `cert.pem` & `key.pem`

**Location**: Project root directory

**Purpose**: SSL certificate files

**Auto-generated**: First run of batch file

**Not in git**: Listed in `.gitignore` for security

**Valid for**: 365 days

**When to replace**:
- For production: Use CA-signed certificate
- If expired: Re-run setup batch file

---

## Troubleshooting

### Issue 1: Python Not Found

**Error**: `Python is not installed or not in PATH`

**Solution**:
1. Install Python from https://www.python.org/
2. **Important**: Check "Add Python to PATH" during installation
3. Restart computer
4. Run batch file again

### Issue 2: Port 3000 Already in Use

**Error**: `Address already in use`

**Solution**:
```powershell
# Kill existing process
taskkill /IM python.exe /F

# Wait a moment
Start-Sleep -Seconds 2

# Run batch file again
.\setup-https.bat
```

### Issue 3: Certificate Generation Failed

**Error**: `Failed to generate SSL certificates`

**Solution**:
1. Verify cryptography package: `pip install cryptography`
2. Delete existing certificate files:
   ```
   del cert.pem
   del key.pem
   ```
3. Run batch file again

### Issue 4: Server Won't Start

**Error**: Server not responding after setup

**Solution**:
1. Check Python is working:
   ```
   python -c "print('OK')"
   ```
2. Check dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Check for port conflicts:
   ```
   netstat -ano | findstr ":3000"
   ```
4. Run batch file with admin rights:
   - Right-click `setup-https.bat`
   - Select **Run as administrator**

### Issue 5: Certificate Warning in Browser

**Error**: "Your connection is not private"

**This is NORMAL** for self-signed certificates

**Solution**:
1. Click **Advanced**
2. Click **Proceed to localhost** (Chrome) or **Accept Risk** (Firefox)
3. Connection is still encrypted (safe)

### Issue 6: Batch File Closes Immediately

**Error**: Window closes too fast to read errors

**Solution**:
1. Open Command Prompt
2. Navigate to project folder:
   ```
   cd "d:\Claude\PSL Automation\PSL Automation"
   ```
3. Run batch file:
   ```
   setup-https.bat
   ```
4. Errors will stay visible

---

## Advanced Usage

### Manual Server Control

**Start server in Command Prompt** (see console output):
```powershell
cd "d:\Claude\PSL Automation\PSL Automation"
python -m app.main
```

**Stop server**:
- Press `Ctrl+C` in the command prompt

**Check if server is running**:
```powershell
netstat -ano | findstr ":3000"
```

**Kill server process**:
```powershell
taskkill /IM python.exe /F
```

### Customize Admin Key

1. Edit `.env` file:
   ```
   ADMIN_KEY=your-secure-key-here
   ```
2. Save and restart batch file
3. Access admin panel:
   ```
   https://localhost:3000/?admin=1&key=your-secure-key-here
   ```

### Change Port

1. Edit `.env` file:
   ```
   PORT=8443
   ```
2. Save and restart batch file
3. Access dashboard:
   ```
   https://localhost:8443/
   ```

### View Server Logs

**Real-time logs** (if started with silent batch):
```powershell
tail -f "server.log"
```

**View startup errors**:
```powershell
type "startup.log"
```

---

## Security Checklist

### ✅ Before First Run

- [ ] Python 3.10+ installed
- [ ] Jira credentials ready
- [ ] .env file will be created automatically

### ✅ After Setup

- [ ] .env has Jira credentials (check file)
- [ ] Certificates generated (cert.pem, key.pem)
- [ ] Setup marker created (.https-configured)
- [ ] Dashboard accessible via HTTPS
- [ ] Admin key configured in .env

### ✅ For Production

- [ ] Replace self-signed cert with CA-signed (Let's Encrypt recommended)
- [ ] Change default admin key
- [ ] Enable firewall rules for port 3000
- [ ] Set up automatic certificate renewal
- [ ] Configure backup strategy
- [ ] Enable monitoring/logging

---

## File Locations

**Setup Batch File**:
```
d:\Claude\PSL Automation\PSL Automation\setup-https.bat
```

**Silent Startup Batch**:
```
d:\Claude\PSL Automation\PSL Automation\start-server-silent.bat
```

**Configuration Files**:
```
d:\Claude\PSL Automation\PSL Automation\.env
d:\Claude\PSL Automation\PSL Automation\.https-configured (created after first setup)
```

**Certificate Files** (Auto-generated):
```
d:\Claude\PSL Automation\PSL Automation\cert.pem
d:\Claude\PSL Automation\PSL Automation\key.pem
```

**Log Files** (If using silent batch):
```
d:\Claude\PSL Automation\PSL Automation\server.log
d:\Claude\PSL Automation\PSL Automation\startup.log
```

---

## Summary

| Step | File | Time | Action |
|------|------|------|--------|
| 1 | setup-https.bat | 2-3 min | Double-click for full setup |
| 2 | (auto) | - | Setup wizard runs automatically |
| 3 | (browser) | - | Dashboard opens in HTTPS |
| Reboot | start-server-silent.bat | 15 sec | (Optional) Auto-start on reboot |
| Next boot | (auto) | 15 sec | Server auto-starts silently |

**One-time setup**: 2-3 minutes  
**Permanent**: Never configure again  
**Reboot**: Server starts automatically (if configured)

---

## Support

### Need Help?

1. Check [HTTPS_INSTALLATION_GUIDE.md](HTTPS_INSTALLATION_GUIDE.md) for detailed HTTPS info
2. Check [README.md](README.md) for project overview
3. Review error message in Command Prompt
4. Check log files (server.log, startup.log)

### Common Links

- **Main Dashboard**: `https://localhost:3000/`
- **Admin Panel**: `https://localhost:3000/?admin=1&key=admin123`
- **Jira**: `https://jira.ekaplus.com`

---

**Last Updated**: May 9, 2026  
**Batch Version**: 1.0  
**Works On**: Windows 7+
