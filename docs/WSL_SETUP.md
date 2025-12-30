# WSL2 Setup Guide for jl-lseg-toolkit

Quick reference for setting up LSEG connectivity on WSL2 with mirrored networking.

## Overview

This project requires **WSL mirrored networking mode**, where `localhost` in WSL is the same as `localhost` in Windows. This is the default in WSL 2.0.0+ (Windows 11 22H2 or later).

With mirrored networking:
- ✅ `localhost` in WSL = `localhost` in Windows
- ✅ No port forwarding needed
- ✅ No tunnel scripts needed
- ✅ Direct connection to LSEG Desktop

## Prerequisites

- **Windows 11 22H2 or later** (for default mirrored networking)
- **WSL 2.0.0+** (check with `wsl --version`)
- **LSEG Workspace Desktop** running and logged in on Windows

## Verify Mirrored Networking

**Check your WSL version (in PowerShell on Windows):**
```powershell
wsl --version
```

**Expected output:**
```
WSL version: 2.0.0 or higher
Kernel version: 5.15.0 or higher
WSLg version: 1.0.0 or higher
```

**Verify mirrored networking is enabled (in WSL):**
```bash
cat /etc/wsl.conf
```

**Expected output (if explicitly configured):**
```
[network]
networkingMode=mirrored
```

**Note:** If `/etc/wsl.conf` doesn't exist or doesn't have this setting, and you're on WSL 2.0.0+, mirrored networking is likely enabled by default.

## Enable Mirrored Networking

If you're not on WSL 2.0.0+ or mirrored networking is not enabled by default:

**1. Create/edit `.wslconfig` in Windows** (in PowerShell on Windows):
```powershell
notepad $env:USERPROFILE\.wslconfig
```

**2. Add the following content:**
```
[wsl2]
networkingMode=mirrored
```

**3. Restart WSL** (in PowerShell on Windows):
```powershell
wsl --shutdown
```

**4. Restart your WSL distribution:**
```bash
# Just start a new WSL terminal
```

## Setup Instructions

### Step 1: Environment Setup (WSL)

```bash
# 1. Navigate to project (replace <USERNAME> with your Windows username)
cd "/mnt/c/Users/<USERNAME>/path/to/jl-lseg-toolkit"

# 2. Install dependencies (creates virtual environment automatically)
uv sync
```

### Step 2: Start LSEG Workspace

1. Launch **LSEG Workspace Desktop** on Windows
2. Ensure you are logged in

### Step 3: Verify Connection

```bash
# Test connection to LSEG endpoints
curl -v --connect-timeout 5 http://localhost:9000
```

**Expected output:** HTTP 404 or 403 (not "Connection refused")

If you get "Connection refused", LSEG Workspace is not running or not logged in.

### Step 4: Use the CLI

```bash
# Run CLI commands directly
uv run lseg-earnings
uv run lseg-screener

# Run tests
uv run pytest tests/
```

## Troubleshooting

### "Connection refused" Error

**Cause:** LSEG Workspace Desktop is not running or not logged in.

**Solution:**
1. Open LSEG Workspace Desktop on Windows
2. Ensure you are logged in
3. Verify LSEG is listening (on Windows PowerShell):
```powershell
netstat -ano | findstr ":9000"
netstat -ano | findstr ":9060"
```

**Expected output:**
```
TCP    127.0.0.1:9000         0.0.0.0:0              LISTENING       <PID>
TCP    127.0.0.1:9060         0.0.0.0:0              LISTENING       <PID>
```

### Mirrored Networking Not Working

**Check if mirrored networking is actually enabled:**
```bash
# In WSL, check if localhost resolves to 127.0.0.1
getent hosts localhost
```

**Expected output:**
```
127.0.0.1       localhost
```

**If you see an IPv6 address or different IP:**
1. Double-check `.wslconfig` on Windows (see "Enable Mirrored Networking" above)
2. Ensure you ran `wsl --shutdown` after editing
3. Try creating `/etc/wsl.conf` in WSL:
```bash
sudo tee /etc/wsl.conf > /dev/null <<EOF
[network]
networkingMode=mirrored
EOF
```
4. Restart WSL: `wsl --shutdown` (in PowerShell)

### "Only 127.0.0.1 and localhost are allowed" Error

**Cause:** Mirrored networking is not enabled or not working correctly.

**Solution:**
1. Follow "Enable Mirrored Networking" steps above
2. Ensure WSL has been restarted after configuration changes
3. Verify with `curl -v http://localhost:9000`

### Older WSL Version / Windows 10

If you're on Windows 10 or WSL < 2.0.0, you'll need to use the legacy tunnel approach:

1. See `dev_scripts/archive/old_wsl_tunnel/README.md` for the legacy tunnel code
2. Follow the old setup instructions (port forwarding + Python tunnel)
3. Consider upgrading to Windows 11 for better WSL support

## Platform Differences

| Platform | Setup Required | Notes |
|----------|----------------|-------|
| **macOS** | None | LSEG runs locally |
| **Native Windows** | None | LSEG runs locally |
| **WSL2 (mirrored)** | Mirrored networking | Modern WSL (default on 2.0.0+) |
| **WSL2 (NAT)** | Port forwarding + tunnel | Legacy WSL (see archive) |
| **WSL1** | None | Shares Windows network (rare) |

## Testing Connection

**Test LSEG connection from Python:**
```bash
# In WSL
uv run python -c "
import lseg.data as rd
rd.open_session()
print('LSEG session opened successfully')
rd.close_session()
"
```

**Expected output:**
```
✓ LSEG session opened successfully
```

## Additional Resources

- **WSL Documentation:** https://learn.microsoft.com/en-us/windows/wsl/
- **Mirrored Networking:** https://learn.microsoft.com/en-us/windows/wsl/networking#mirrored-mode-networking
- **Legacy Tunnel Setup:** `dev_scripts/archive/old_wsl_tunnel/README.md`
- **Project Documentation:** `CLAUDE.md`

---

**Summary:** With mirrored networking, WSL2 setup is straightforward - just ensure LSEG Workspace is running on Windows and you can connect directly via `localhost`. No complex networking setup required!
