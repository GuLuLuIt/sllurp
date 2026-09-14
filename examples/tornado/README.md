# Sllurp Tornado WebSocket demo

This example shows how to use Sllurp with Tornado and push RFID tag reads to a browser over WebSockets.

Start with the repository [Quick Start](../../QUICKSTART.md) and confirm normal CLI inventory works before running the web demo.

## Setup

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m pip install -r examples/tornado/requirements.txt
```

On Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m pip install -r examples\tornado\requirements.txt
```

Review the reader address/configuration in `main.py` before running.

## Run

```bash
cd examples/tornado
python main.py
```

Then open `http://localhost:8888` in a browser.

## What it demonstrates

- application-managed LLRP connection
- tag report callbacks
- WebSocket delivery to a browser
- simple reader start/stop interaction

For smaller feature-specific examples such as deduplication, RF telemetry, runtime configuration, TLS CLI recipes, and vendor management, see [`../README.md`](../README.md).
