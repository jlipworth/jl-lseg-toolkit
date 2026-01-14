# Getting Started

Setup guide for jl-lseg-toolkit across all platforms.

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.12+ | Required |
| uv | Latest | Package manager ([install](https://docs.astral.sh/uv/getting-started/installation/)) |
| LSEG Workspace | Desktop app | Must be running and logged in |

## Quick Start

### 1. Clone and Install

```bash
git clone <repo-url>
cd jl-lseg-toolkit

# Install dependencies (creates venv automatically)
uv sync
```

### 2. Start LSEG Workspace

Launch **LSEG Workspace Desktop** and log in. The toolkit connects to:
- `localhost:9000` (primary)
- `localhost:9060` (alternative)

### 3. Verify Connection

```bash
# Quick test
curl -v --connect-timeout 5 http://localhost:9000
```

**Expected:** HTTP 404 or 403 (not "Connection refused")

### 4. Run the Tools

```bash
# Earnings report for this week's S&P 500 earnings
uv run lseg-earnings

# Equity screener
uv run lseg-screener

# Time series extraction
uv run lseg-extract ZN ZB --asset-class futures
```

---

## Platform-Specific Setup

### macOS / Native Windows

No additional setup required. LSEG Workspace runs locally and `localhost` works out of the box.

### WSL2 (Windows Subsystem for Linux)

WSL2 requires **mirrored networking mode** to access LSEG Workspace running on Windows.

#### Check Your WSL Version

```powershell
# In PowerShell on Windows
wsl --version
```

**Required:** WSL 2.0.0+ (default on Windows 11 22H2+)

#### Mirrored Networking

**WSL 2.0.0+ (Windows 11 22H2+):** Mirrored networking is enabled by default. No action needed.

**Older WSL versions:** Enable manually:

```powershell
# In PowerShell on Windows
notepad $env:USERPROFILE\.wslconfig
```

Add:
```ini
[wsl2]
networkingMode=mirrored
```

Then restart WSL:
```powershell
wsl --shutdown
```

#### Verify Mirrored Networking

```bash
# In WSL
curl -v --connect-timeout 5 http://localhost:9000
```

If you get "Connection refused", see [Troubleshooting](#wsl-connection-refused).

#### Platform Summary

| Platform | Setup Required | Notes |
|----------|----------------|-------|
| macOS | None | LSEG runs locally |
| Windows | None | LSEG runs locally |
| WSL2 (2.0.0+) | None | Mirrored networking is default |
| WSL2 (older) | `.wslconfig` edit | Enable mirrored networking |
| WSL1 | None | Shares Windows network (rare) |

---

## Verification

### Test Python Connection

```bash
uv run python -c "
import lseg.data as rd
rd.open_session()
print('LSEG session opened successfully')
rd.close_session()
"
```

### Run Tests

```bash
# All tests (requires LSEG connection)
uv run pytest tests/ --no-cov

# Unit tests only (no LSEG needed)
uv run pytest tests/ -m "not integration"
```

---

## Troubleshooting

### "Connection refused"

**Cause:** LSEG Workspace is not running or not logged in.

**Solution:**
1. Open LSEG Workspace Desktop
2. Ensure you are logged in
3. Verify LSEG is listening:

```powershell
# PowerShell on Windows
netstat -ano | findstr ":9000"
```

**Expected:**
```
TCP    127.0.0.1:9000    0.0.0.0:0    LISTENING    <PID>
```

### WSL "Connection refused"

**Cause:** Mirrored networking not enabled or not working.

**Solution:**
1. Check WSL version: `wsl --version` (need 2.0.0+)
2. Verify `.wslconfig` has `networkingMode=mirrored`
3. Restart WSL: `wsl --shutdown`
4. Check localhost resolves correctly:

```bash
# In WSL
getent hosts localhost
# Expected: 127.0.0.1    localhost
```

### "Failed to open LSEG session"

**Solution:**
1. Ensure LSEG Workspace is running and logged in
2. Configure app key: `uv run lseg-setup`

### Older Windows / WSL < 2.0.0

For Windows 10 or older WSL versions, see `dev_scripts/archive/old_wsl_tunnel/README.md` for legacy tunnel setup. Consider upgrading to Windows 11 for native mirrored networking support.

---

## Next Steps

- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Testing, linting, contributing
- **[TIMESERIES.md](TIMESERIES.md)** - Time series extraction guide
- **[LSEG_API_REFERENCE.md](LSEG_API_REFERENCE.md)** - API patterns and fields
