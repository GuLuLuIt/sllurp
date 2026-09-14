# Sllurp FastAPI RFID reader demo

This example exposes a small FastAPI/WebSocket application around an LLRP reader and a simple browser UI. It is an application example, not the recommended starting point for first-time Sllurp setup.

Start with the repository [Quick Start](../../QUICKSTART.md) and confirm normal inventory works before running a web framework around the reader.

## What it demonstrates

- connect to an LLRP reader from an application lifecycle
- start and stop inventory
- receive tag callbacks
- expose reader/tag state through HTTP endpoints
- push tag updates to a browser over WebSockets

## Requirements

- Sllurp supports Python 3.10 or newer
- the included `uv.lock` / example `pyproject.toml` currently target Python 3.13 or newer
- FastAPI
- Uvicorn
- Pydantic
- WebSocket support

If you use the pip/requirements setup below rather than the included `uv` lock, use dependency versions compatible with your selected supported Python version.

## Setup with pip

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m pip install -r examples/fastapi/requirements.txt
```

On Windows PowerShell use:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m pip install -r examples\fastapi\requirements.txt
```

Before running, edit `READER_IP` in `app.py` or adapt the example to read the address from your application configuration.

## Run

```bash
cd examples/fastapi
python app.py
```

Or with `uv` and Python 3.13+:

```bash
cd examples/fastapi
uv run app.py
```

Open `index.html` in a browser to use the simple test UI.

## Endpoints

- `GET /start` — start inventory
- `GET /stop` — stop inventory
- `GET /last-read` — return the latest tag set
- `GET /status` — report connection status
- `GET /state` — report the Sllurp protocol state
- `GET /clear` — clear stored tag data
- `WS /ws` — stream tag updates

## Production notes

The demo intentionally keeps application structure simple. Before production use, configure reader address/credentials outside source code, restrict CORS, add authentication/authorization, validate WebSocket clients, and define your own reconnect/error policy.

For smaller feature-specific examples, see [`../README.md`](../README.md).
