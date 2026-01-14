# WSL2 Setup Guide

> **This document has been consolidated into [GETTING_STARTED.md](GETTING_STARTED.md).**
>
> See the **Platform-Specific Setup > WSL2** section for WSL configuration.

## Quick Reference

WSL 2.0.0+ (Windows 11 22H2+) has mirrored networking enabled by default - no setup needed.

For older WSL versions, add to `~/.wslconfig` on Windows:
```ini
[wsl2]
networkingMode=mirrored
```

Then: `wsl --shutdown` and restart.

## Full Documentation

- **[Getting Started](GETTING_STARTED.md)** - Complete setup for all platforms
- **[Troubleshooting](TROUBLESHOOTING.md)** - Connection issues
