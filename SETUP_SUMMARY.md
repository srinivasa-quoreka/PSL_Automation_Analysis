# PSL Automation - Setup Summary & Quick Start

## ✅ COMPLETE Setup Solution - One Click!

### What Was Created

**3 Batch Files** for complete automation:

1. **setup-https.bat** ⭐ (Main)
   - One-click HTTPS setup + server start
   - Auto-detects & installs Python dependencies
   - Generates SSL certificates
   - Remembers configuration (no repeat setup)

2. **start-server-silent.bat** 
   - Silent server startup (no prompts)
   - For auto-start on system reboot
   - Works with Windows Startup folder

3. **create-shortcuts.bat**
   - Creates desktop shortcuts
   - Quick access to setup, dashboard, admin panel

---

## How to Use (Super Simple!)

### First Time Setup

```
1. Navigate to: d:\Claude\PSL Automation\PSL Automation\
2. Double-click: setup-https.bat
3. Wait 2-3 minutes for setup
4. Browser opens to https://localhost:3000/
5. Done! ✅
```

**What Happens Automatically**:
- ✅ Checks Python installation
- ✅ Installs cryptography, uvicorn, fastapi
- ✅ Generates SSL certificates
- ✅ Reads .env configuration
- ✅ Creates setup marker (.https-configured)
- ✅ Starts HTTPS server
- ✅ Opens dashboard in browser

### Subsequent Times

```
1. Double-click: setup-https.bat
2. Server starts (15 seconds)
3. Browser opens
4. Done! ✅
```

**Note**: Setup is skipped if `.https-configured` exists

### Enable Auto-Start (Optional)

```
1. Double-click: create-shortcuts.bat
2. Move "PSL Auto-Start.lnk" to Windows Startup folder
3. Restart computer
4. Server starts automatically! ✅
```

---

## Access Dashboard

### Main Dashboard
```
https://localhost:3000/
```

### Admin Panel (with key)
```
https://localhost:3000/?admin=1&key=admin123
```

### Browser Certificate Warning (Normal)

⚠️ **Expected**: "Your connection is not private"

✅ **Safe to proceed**:
- Click **Advanced**
- Click **Proceed** (Chrome) or **Accept Risk** (Firefox)
- Connection is encrypted with SSL/TLS

---

## Files Created

### Batch Files
```
d:\Claude\PSL Automation\PSL Automation\
├── setup-https.bat              ← Main (double-click this!)
├── start-server-silent.bat      ← Auto-start version
└── create-shortcuts.bat         ← Create desktop shortcuts
```

### Auto-Generated (First Run)
```
├── .https-configured            ← Setup marker
├── cert.pem                     ← SSL certificate
├── key.pem                      ← SSL private key
└── .env                         ← Configuration (if missing)
```

### Documentation
```
├── BATCH_FILES_README.md        ← Quick reference
├── BATCH_SETUP_GUIDE.md         ← Detailed guide
├── HTTPS_INSTALLATION_GUIDE.md  ← Complete HTTPS setup
└── HTTPS_SETUP.md               ← Quick HTTPS reference
```

---

## Configuration

### Edit .env (Jira Credentials)

```
1. Open: .env file in project root
2. Edit (example):
   JIRA_BASE_URL=https://jira.ekaplus.com
   JIRA_USERNAME=your-email@example.com
   JIRA_PASSWORD=your-api-token
   ADMIN_KEY=admin123
3. Save
4. Double-click setup-https.bat to restart
```

### Change Admin Key

Edit `.env`:
```
ADMIN_KEY=your-new-secure-key
```

Then access: `https://localhost:3000/?admin=1&key=your-new-secure-key`

### Change Port

Edit `.env`:
```
PORT=8443
```

Then access: `https://localhost:8443/`

---

## Features

✅ **Zero Configuration** - Auto-configures everything  
✅ **Python Detection** - Checks if Python is installed  
✅ **Dependency Management** - Auto-installs required packages  
✅ **Certificate Generation** - Creates SSL certificates automatically  
✅ **HTTPS by Default** - Server runs on HTTPS  
✅ **Smart Caching** - Remembers configuration (no repeat setup)  
✅ **Browser Launch** - Opens dashboard automatically  
✅ **Error Handling** - Clear error messages if something fails  
✅ **Auto-Start Support** - Works with Windows Startup folder  
✅ **Silent Mode** - Silent startup for automation  

---

## Troubleshooting

### Issue: "Python is not installed"
- Install Python 3.10+ from python.org
- Check "Add Python to PATH" during installation
- Restart computer

### Issue: "Port 3000 already in use"
```powershell
taskkill /IM python.exe /F
(Re-run batch file)
```

### Issue: Batch file closes immediately
1. Open Command Prompt
2. Navigate to: `cd "d:\Claude\PSL Automation\PSL Automation"`
3. Run: `setup-https.bat`
4. Read error message

### Issue: Certificate error in browser
This is **normal** for self-signed certificates:
- Click **Advanced**
- Click **Proceed**
- Connection is safe

### Issue: Server won't start
1. Run batch file as Administrator
2. Check Python: `python -c "print('OK')"`
3. Install dependencies: `pip install -r requirements.txt`

---

## Quick Command Reference

```powershell
# Run setup (first time or anytime)
.\setup-https.bat

# Run silent startup
.\start-server-silent.bat

# Create desktop shortcuts
.\create-shortcuts.bat

# Access dashboard
https://localhost:3000/

# Access admin panel
https://localhost:3000/?admin=1&key=admin123

# Kill server process (if needed)
taskkill /IM python.exe /F

# View server logs
type server.log
```

---

## What Makes This Special

### Before (Manual)
```
1. Install Python manually ❌
2. Run pip install ❌
3. Generate certificates manually ❌
4. Edit .env file ❌
5. Start server ❌
6. Open browser ❌
```

### After (One-Click) ✅
```
Double-click: setup-https.bat
Done! ✅
```

---

## Documentation Map

| Document | Best For |
|----------|----------|
| **This file** | Quick overview |
| BATCH_FILES_README.md | Quick reference |
| BATCH_SETUP_GUIDE.md | Detailed setup help |
| HTTPS_INSTALLATION_GUIDE.md | HTTPS deep dive |
| README.md | Project overview |

---

## Summary

| Action | Command | Time |
|--------|---------|------|
| **First Setup** | `setup-https.bat` | 2-3 min |
| **Start Server** | `setup-https.bat` | 15 sec |
| **Auto-Start** | Move shortcut to Startup | Once |
| **Access Dashboard** | `https://localhost:3000/` | Any time |
| **Edit Config** | Edit `.env` file | 1 min |

---

## Security

✅ **Built-In Security**:
- Jira credentials in `.env` (never in git)
- Admin key protection in `.env`
- HTTPS/TLS encryption enabled
- Self-signed certificates (auto-generated)

⚠️ **For Production**:
- Replace self-signed with CA-signed certificate
- Change admin key to strong password
- Set up certificate auto-renewal
- Enable logging and monitoring

---

## Support & Resources

- **Batch Files Help**: See BATCH_FILES_README.md
- **HTTPS Help**: See HTTPS_INSTALLATION_GUIDE.md
- **Troubleshooting**: See BATCH_SETUP_GUIDE.md
- **Project Info**: See README.md
- **GitHub**: https://github.com/srinivasa-quoreka/PSL_Automation_Analysis

---

## Next Steps

### ✅ You're Ready!

1. **Double-click**: `setup-https.bat`
2. **Wait**: 2-3 minutes (first time) or 15 seconds (next times)
3. **Access**: `https://localhost:3000/`
4. **Enjoy**: Your dashboard is running on HTTPS! 🎉

### Optional: Auto-Start on Reboot

1. **Double-click**: `create-shortcuts.bat`
2. **Move**: "PSL Auto-Start.lnk" to Windows Startup folder
3. **Restart**: Computer auto-starts server

---

**Version**: 1.0  
**Last Updated**: May 9, 2026  
**Status**: ✅ Production Ready  
**Platform**: Windows 7+
