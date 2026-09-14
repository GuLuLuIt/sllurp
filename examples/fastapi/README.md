# Sllurp FastAPI RFID reader demo

This example exposes a small FastAPI/WebSocket application around an LLRP reader and serves a same-origin browser UI. It is an application example, not the recommended starting point for first-time Sllurp setup.

Start with the repository [Quick Start](../../QUICKSTART.md) and confirm normal inventory works before running a web framework around the reader.

## What it demonstrates

- connect to an LLRP reader from an application lifecycle
- start and stop inventory through HTTP endpoints
- receive tag callbacks
- expose reader/tag state through HTTP
- push tag updates to a browser over WebSockets
- configure reader/web addresses with environment variables instead of editing source

## Requirements

- Python 3.10 or newer
- Sllurp installed from this repository
- dependencies in `requirements.txt`

The example deliberately does **not** list `sllurp` in `requirements.txt`; install the repository itself first so the example cannot accidentally pull the upstream PyPI distribution.

## Setup

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m pip install -r examples/fastapi/requirements.txt
```

On Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m pip install -r examples\fastapi\requirements.txt
```

## Configure

Set the reader address before starting the demo:

```bash
export SLLURP_READER_HOST=192.168.1.50
export SLLURP_READER_PORT=5084
```

PowerShell:

```powershell
$env:SLLURP_READER_HOST = "192.168.1.50"
$env:SLLURP_READER_PORT = "5084"
```

Optional web listener settings are `SLLURP_WEB_HOST` (default `127.0.0.1`) and `SLLURP_WEB_PORT` (default `4000`).

## Run

From the repository root:

```bash
python examples/fastapi/app.py
```

Then open <http://127.0.0.1:4000/>. The application serves `index.html` itself, so the browser UI, HTTP calls, and WebSocket all use the same origin.

## Endpoints

- `POST /start` — start inventory
- `POST /stop` — stop inventory
- `POST /start-stop` — inventory for one second
- `GET /last-read` — return the latest tag set
- `GET /status` — report connection status
- `GET /state` — report the Sllurp protocol state
- `POST /clear` — clear stored tag data
- `WS /ws` — stream tag updates

## Production notes

The demo intentionally keeps application structure small. Before production use, add authentication/authorization, restrict network exposure, validate WebSocket clients, move secrets into a proper secret/configuration system, and define your own reconnect/error policy.

For smaller feature-specific examples, see [`../README.md`](../README.md).
