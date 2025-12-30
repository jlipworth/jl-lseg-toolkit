# Troubleshooting Guide

Common issues and solutions for jl-lseg-toolkit.

## Quick Diagnostics

Before diving into specific issues, run these quick checks:

```bash
# 1. Test LSEG connection (from your terminal)
curl -v --connect-timeout 5 http://localhost:9000

# Expected: HTTP 404 or 403 (not "Connection refused")
# If "Connection refused" -> LSEG Workspace not running

# 2. Test Python session
uv run python -c "
import lseg.data as rd
rd.open_session()
print('Session opened successfully')
rd.close_session()
"
```

---

## Connection Issues

### "Connection refused" Error

**Symptoms:**
```
ConnectionRefusedError: [Errno 111] Connection refused
Failed to open LSEG session: Connection refused
```

**Cause:** LSEG Workspace Desktop is not running or not logged in.

**Solution:**
1. Open LSEG Workspace Desktop on your machine (Windows/macOS)
2. Ensure you are logged in (not just the app open)
3. Verify LSEG is listening on expected ports:

   **Windows (PowerShell):**
   ```powershell
   netstat -ano | findstr ":9000"
   netstat -ano | findstr ":9060"
   ```

   **macOS/Linux:**
   ```bash
   lsof -i :9000
   lsof -i :9060
   ```

   **Expected:** Should show LISTENING/LISTEN status

4. If ports are not listening, restart LSEG Workspace Desktop

---

### "Only 127.0.0.1 and localhost are allowed" Error

**Symptoms:**
```
Only 127.0.0.1 and localhost are allowed
```

**Cause:** WSL2 mirrored networking is not enabled or not working correctly.

**Solution:**
1. Verify you're on WSL 2.0.0+ (check with `wsl --version` in PowerShell)
2. Enable mirrored networking - see `docs/WSL_SETUP.md`
3. Restart WSL after configuration: `wsl --shutdown` (in PowerShell)
4. Test connection again

---

### "Backend error. 400 Bad Request" Error

**Symptoms:**
```
Backend error. 400 Bad Request. Invalid ApplicationId
```

**Cause:** Invalid or missing app key configuration.

**Solution:**
1. Run the setup command to configure your app key:
   ```bash
   uv run lseg-setup
   ```
2. Or manually create config file at `~/.lseg/config.json`:
   ```json
   {
     "app_key": "your-app-key-here"
   }
   ```
3. To get an app key from LSEG Workspace:

   **Option A: App Key Generator (Recommended)**
   1. Open LSEG Workspace Desktop
   2. In the search bar, type `APP KEY` and press Enter
   3. Select "App Key Generator" from results
   4. Click "Register New App"
   5. Enter an app name (e.g., "My Python Scripts")
   6. Select "Desktop" as the application type
   7. Click "Register" and copy the generated key

   **Option B: API Playground**
   1. Open LSEG Workspace Desktop
   2. Search for `API PLAYGROUND`
   3. Look for your app key in the settings/configuration panel

   **Note:** App keys are tied to your LSEG account. Each user needs their own key.

---

## Session Errors

### "Failed to open LSEG session" Error

**Symptoms:**
```
SessionError: Failed to open LSEG session: <error details>
```

**Common causes and solutions:**

1. **LSEG Workspace not running** - Start LSEG Workspace Desktop and log in

2. **App key not configured** - Run `uv run lseg-setup`

3. **WSL networking issues** - See WSL_SETUP.md

4. **Session timeout** - LSEG sessions can expire if idle too long. Restart the CLI command.

5. **Multiple sessions** - LSEG may limit concurrent sessions. Close other apps using LSEG API.

---

### Session Hangs or Freezes

**Symptoms:**
- CLI appears frozen
- No response for extended period
- Eventually times out

**Possible causes and solutions:**

1. **Network latency** - Check your internet connection

2. **Large data request** - Some queries (e.g., all S&P 500 with full financials) take 30-60 seconds

3. **LSEG server issues** - Try again in a few minutes

4. **Hung session** - Restart LSEG Workspace Desktop

---

## API Errors

### "Failed to get data" Error

**Symptoms:**
```
DataRetrievalError: Failed to get <data_type>: <error>
```

**Common causes:**

1. **Invalid RIC/Ticker** - Verify the ticker exists in LSEG
   ```bash
   # Test a single ticker
   uv run python -c "
   import lseg.data as rd
   rd.open_session()
   print(rd.get_data('AAPL.O', ['TR.CommonName']))
   rd.close_session()
   "
   ```

2. **Invalid field name** - Check `docs/LSEG_API_REFERENCE.md` for valid field names

3. **Date format issues** - Use YYYY-MM-DD format for dates

4. **No data available** - Some fields may be empty for certain companies

---

### "No constituents found for index" Error

**Symptoms:**
```
DataRetrievalError: No constituents found for index <INDEX>
```

**Solution:**
1. Verify the index code is correct (e.g., SPX, NDX, GDAXI)
2. List available indices:
   ```bash
   uv run lseg-earnings --list-indices
   uv run lseg-screener --list-indices
   ```
3. Check `docs/LSEG_API_REFERENCE.md` for supported indices

---

### Empty Results

**Symptoms:**
- Command runs successfully but returns empty results
- Excel file has no data

**Possible causes:**

1. **Date range too narrow** - Expand start/end dates
   ```bash
   # Use a wider date range
   uv run lseg-earnings --timeframe month
   ```

2. **Market cap filters too strict**
   ```bash
   # Remove market cap filters
   uv run lseg-earnings --min-cap 0
   ```

3. **No earnings in period** - Some indices have few earnings in certain weeks

---

## App Key Configuration Issues

### "No app key found" Warning

**Symptoms:**
- Warning about missing app key
- Uses default app key (may have rate limits)

**Solution:**
1. Run the setup command:
   ```bash
   uv run lseg-setup
   ```

2. Or manually create config file:

   **Global config (recommended):**
   ```bash
   mkdir -p ~/.lseg
   echo '{"app_key": "your-app-key-here"}' > ~/.lseg/config.json
   ```

   **Project-local config:**
   ```bash
   echo '{"app_key": "your-app-key-here"}' > .lseg-config.json
   ```

3. Config file search order:
   1. `.lseg-config.json` (current directory, up to 10 parent directories)
   2. `~/.lseg/config.json` (global)
   3. LSEG default (if no config found)

---

### App Key Not Being Used

**Symptoms:**
- Created config file but still getting app key errors

**Debugging steps:**
1. Verify config file location and format:
   ```bash
   cat ~/.lseg/config.json
   # Should output: {"app_key": "your-key-here"}
   ```

2. Check file permissions:
   ```bash
   ls -la ~/.lseg/config.json
   # Should be readable by your user
   ```

3. Verify JSON is valid:
   ```bash
   python -c "import json; json.load(open('$HOME/.lseg/config.json'))"
   ```

4. Test app key loading:
   ```bash
   uv run python -c "
   from lseg_toolkit.client.config import load_app_key
   print(f'Loaded app key: {load_app_key()[:10]}...' if load_app_key() else 'No app key found')
   "
   ```

---

## WSL2-Specific Issues

For comprehensive WSL2 setup and troubleshooting, see `docs/WSL_SETUP.md`.

### Quick WSL2 Checklist

1. **Verify WSL version:** `wsl --version` (need 2.0.0+)
2. **Verify mirrored networking:** `cat /etc/wsl.conf` or `cat $HOME/.wslconfig`
3. **Test localhost:** `curl -v http://localhost:9000`
4. **Restart if needed:** `wsl --shutdown` (in PowerShell)

---

## Performance Issues

### Slow Data Fetching

**Normal expected times:**
- Index constituents: 2-5 seconds
- Earnings data (500 companies): 5-10 seconds
- Full report generation: 30-60 seconds

**If significantly slower:**

1. **Check internet connection** - API requires stable connection

2. **Reduce query size:**
   ```bash
   # Filter by market cap to reduce universe
   uv run lseg-earnings --min-cap 10000  # $10B+ only
   ```

3. **Use narrower date range:**
   ```bash
   uv run lseg-earnings --timeframe today
   ```

---

## Getting Help

If you're still stuck:

1. **Check the logs** - Add `--verbose` flag if available
2. **Review documentation:**
   - `docs/LSEG_API_REFERENCE.md` - API fields and patterns
   - `docs/WSL_SETUP.md` - WSL2 networking
   - `CLAUDE.md` - Project overview
3. **Test with minimal example:**
   ```bash
   uv run python -c "
   import lseg.data as rd
   rd.open_session()
   df = rd.get_data('AAPL.O', ['TR.CommonName', 'TR.CompanyMarketCap'])
   print(df)
   rd.close_session()
   "
   ```
