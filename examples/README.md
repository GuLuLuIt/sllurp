# Sllurp examples

These examples are small, copyable starting points for the main Sllurp features. Replace reader addresses, credentials, certificate paths, antenna IDs, and vendor settings with values for your hardware.

## Start here

Install the current repository code from the repository root:

```bash
python -m pip install -e .
```

Or install directly from GitHub:

```bash
python -m pip install "git+https://github.com/GuLuLuIt/sllurp.git@main"
```

Run the CLI help before changing reader or tag state:

```bash
sllurp --help
sllurp inventory --help
sllurp access --help
```

## Examples by feature

| Feature | Example |
|---|---|
| Basic Python inventory | [`basic_inventory.py`](basic_inventory.py) |
| Timed software/hardware dedup | [`dedup_inventory.py`](dedup_inventory.py) |
| RF telemetry / per-antenna observations | [`rf_telemetry.py`](rf_telemetry.py) |
| Live runtime configuration | [`runtime_config.py`](runtime_config.py) |
| Generic HTTP/HTTPS management | [`reader_management_generic.py`](reader_management_generic.py) |
| Zebra RM / IoT Connector management | [`zebra_management.py`](zebra_management.py) |
| Impinj R700/R720 management | [`impinj_management.py`](impinj_management.py) |
| Honeywell/Intermec IF-series DCWS | [`intermec_management.py`](intermec_management.py) |
| CLI recipes: TLS, access, logging, multi-reader, Impinj extensions | [`cli-recipes.md`](cli-recipes.md) |
| FastAPI web application / WebSocket demo | [`fastapi/`](fastapi/) |

## Safety and protocol boundaries

- LLRP inventory normally uses TCP 5084; Secure LLRP commonly uses 5085.
- Vendor HTTP/HTTPS/SOAP management is separate from LLRP inventory.
- Do not disable TLS certificate verification in production just to make a connection work; configure the correct CA and hostname instead.
- Tag writes change tag memory. Test write operations on disposable/test tags first.
- Network, region, firmware, reboot, and reader-management changes can interrupt reader access. Read the vendor guide before applying them.

For installation and CLI onboarding, see [`../QUICKSTART.md`](../QUICKSTART.md). For the feature map, see [`../docs/index.rst`](../docs/index.rst).
