# Getting Started

Setup guide for `jl-lseg-toolkit` across macOS, Windows, and WSL2.

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| Python 3.12+ | Required by the project |
| `uv` | Recommended package manager / runner |
| LSEG Workspace Desktop | Must be running and logged in locally |

## Quick start

```bash
git clone git@github.com:jlipworth/jl-lseg-toolkit.git
cd jl-lseg-toolkit
uv sync
uv run lseg-setup
```

## Verify connectivity

```bash
# LSEG Workspace local API
curl -v --connect-timeout 5 http://localhost:9000
# Expected: 404 or 403, not "Connection refused"

# Python session check
uv run python -c "import lseg.data as rd; rd.open_session(); print('LSEG session opened successfully'); rd.close_session()"
```

## Try the main tools

```bash
uv run lseg-earnings
uv run lseg-screener --index NDX
uv run lseg-extract ZN ZB
uv run lseg-scheduler groups
```

## WSL2 notes

WSL2 should use **mirrored networking mode** so that `localhost` inside WSL can
reach LSEG Workspace running on Windows.

```powershell
# In PowerShell
wsl --version
```

- **Preferred:** WSL 2.0.0+ with mirrored networking
- For older WSL versions, manually enable `networkingMode=mirrored` in
  `%USERPROFILE%\.wslconfig`, then run `wsl --shutdown`

## Verification / contributor next step

If you plan to contribute code, also run:

```bash
make install-hooks
make ci-local
```

## Troubleshooting

- Connection/app-key issues: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- Timeseries/storage workflows: [TIMESERIES.md](TIMESERIES.md)
- Scheduler behavior: [SCHEDULER.md](SCHEDULER.md)

## Next docs to read

- [DEVELOPMENT.md](DEVELOPMENT.md) — contributor workflow after setup
- [TIMESERIES.md](TIMESERIES.md) — extraction/storage behavior
- [PREDICTION_MARKETS.md](PREDICTION_MARKETS.md) — Kalshi/Polymarket/FOMC workflows
