# Sllurp Quick Start

Use this guide to go from a new computer to a working LLRP inventory, then enable the features you need: Secure LLRP/TLS, timed deduplication, reader management, runtime configuration, RF telemetry, Impinj extensions, tag access, logging, and multi-reader inventory.

For the features documented in this repository, install the immutable `GuLuLuIt/sllurp` release tag `v3.1.2` or download its wheel from the [v3.1.2 GitHub Release](https://github.com/GuLuLuIt/sllurp/releases/tag/v3.1.2). The `sllurp` package on PyPI is a separately maintained distribution and is not an equivalent installation path for GuLuLuIT features.

For supported Python classes, configuration fields, callbacks, return values,
exceptions, and short examples, use the
[`Sllurp 3.1.2 API reference`](API_REFERENCE.md).

## 1. Requirements

- Python **3.10 or newer**
- Network access to the RFID reader
- LLRP enabled on the reader
- TCP **5084** for normal LLRP unless the reader uses another configured port
- TCP **5085** for Secure LLRP/TLS when the reader exposes the standard encrypted endpoint
- HTTP/HTTPS access only when using a vendor reader-management API

Check Python:

```text
python --version
```

On Linux/macOS the command may be `python3 --version`.

## 2. Windows 10/11

### PowerShell

Install Python and Git if needed:

```powershell
winget install Python.Python.3.12
winget install Git.Git
```

Open a new PowerShell window:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install "git+https://github.com/GuLuLuIt/sllurp.git@v3.1.2"
```

If script activation is restricted, use the environment directly:

```powershell
.\.venv\Scripts\python.exe -m pip install "git+https://github.com/GuLuLuIt/sllurp.git@v3.1.2"
.\.venv\Scripts\sllurp.exe --version
.\.venv\Scripts\sllurp.exe --help
```

### Command Prompt

```bat
py -3.12 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install "git+https://github.com/GuLuLuIt/sllurp.git@v3.1.2"
```

## 3. Ubuntu / Debian / Linux Mint / Raspberry Pi OS

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install "git+https://github.com/GuLuLuIt/sllurp.git@v3.1.2"
```

## 4. Fedora / RHEL / Rocky Linux / AlmaLinux

```bash
sudo dnf install -y python3 python3-pip git
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install "git+https://github.com/GuLuLuIt/sllurp.git@v3.1.2"
```

## 5. Arch Linux / Manjaro

```bash
sudo pacman -S --needed python python-pip git
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install "git+https://github.com/GuLuLuIt/sllurp.git@v3.1.2"
```

## 6. openSUSE / SUSE

```bash
sudo zypper install python3 python3-pip git
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install "git+https://github.com/GuLuLuIt/sllurp.git@v3.1.2"
```

## 7. macOS

With Homebrew:

```bash
brew install python git
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install "git+https://github.com/GuLuLuIt/sllurp.git@v3.1.2"
```

## 8. Development/source checkout

```bash
git clone https://github.com/GuLuLuIt/sllurp.git
cd sllurp
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
pytest -W error
```

On Windows, activate with `.\.venv\Scripts\Activate.ps1`.

## 9. Verify installation

```bash
sllurp --version
sllurp --help
sllurp inventory --help
```

The source tree currently identifies as version **3.1.2**. If `sllurp --version` reports a different version, confirm which environment and executable are active before troubleshooting reader behavior.

## 10. First inventory

Replace `192.168.1.50` with the reader address:

```bash
sllurp inventory 192.168.1.50
```

Use all reader-reported antennas:

```bash
sllurp inventory -a 0 192.168.1.50
```

Run for 10 seconds:

```bash
sllurp inventory -t 10 -a 0 192.168.1.50
```

Inventory multiple readers:

```bash
sllurp inventory -a 0 192.168.1.50 192.168.1.51
```

Reset LLRP state after an interrupted debugging session:

```bash
sllurp reset 192.168.1.50
```

## 11. Timed tag deduplication

Suppress repeated EPC callbacks for two seconds:

```bash
sllurp inventory --dedup-seconds 2 --dedup-backend auto -a 0 192.168.1.50
```

Backends:

- `auto` prefers supported reader-side behavior and otherwise uses memory
- `hardware` requires the necessary reader capability
- `memory` always deduplicates in the client

For RF telemetry, prefer raw observations or memory deduplication so cross-antenna observations are not collapsed.

Runnable Python example: [`examples/dedup_inventory.py`](examples/dedup_inventory.py).

## 12. Secure LLRP / TLS

Normal LLRP defaults to TCP 5084. `--tls` defaults to TCP 5085 unless `--port` is supplied.

Trusted reader certificate:

```bash
sllurp inventory --tls reader.example.com
```

Private/internal CA:

```bash
sllurp inventory --tls --tls-ca-file reader-ca.pem reader.example.com
```

Mutual TLS:

```bash
sllurp inventory \
  --tls \
  --tls-ca-file reader-ca.pem \
  --tls-client-cert client.pem \
  --tls-client-key client.key \
  reader.example.com
```

Connect by IP while validating a certificate issued to a DNS name:

```bash
sllurp inventory \
  --tls \
  --tls-server-hostname reader.example.com \
  192.168.1.50
```

`--tls-no-verify` is for controlled testing. Prefer the correct CA for normal deployments.

See [Secure LLRP](docs/secure_llrp.rst) and the [CLI recipes](examples/cli-recipes.md).

## 13. Impinj inventory extensions

Dual-target search mode:

```bash
sllurp inventory --impinj-search-mode 2 192.168.1.50
```

Phase/RSSI/Doppler extensions:

```bash
sllurp inventory --impinj-reports -a 0 192.168.1.50
```

Fixed-frequency extension where supported:

```bash
sllurp inventory --impinj-fixed-frequency -f 1,2 -a 0 192.168.1.50
```

More command examples: [`examples/cli-recipes.md`](examples/cli-recipes.md).

## 14. Tag memory access

Read two 16-bit words:

```bash
sllurp access --read-words 2 --count 1 192.168.1.50
```

Choose a memory bank and word pointer:

```bash
sllurp access --read-words 2 --memory-bank 2 --word-ptr 0 --count 1 192.168.1.50
```

Use `sllurp access --help` before write operations. Test writes with disposable/test tags first.

More examples: [`examples/cli-recipes.md`](examples/cli-recipes.md).

## 15. Stream tag data

```bash
sllurp log -a 0 -o tags.csv 192.168.1.50
```

Use reader timestamps:

```bash
sllurp log -a 0 --reader-timestamp -o tags.csv 192.168.1.50
```

## 16. Minimal Python API

```python
from sllurp.llrp import LLRPReaderClient, LLRPReaderConfig, LLRP_DEFAULT_PORT


def on_tags(reader, tag_reports):
    for tag in tag_reports:
        print(tag)


config = LLRPReaderConfig({"antennas": [0]})
reader = LLRPReaderClient("192.168.1.50", LLRP_DEFAULT_PORT, config)
reader.add_tag_report_callback(on_tags)
reader.connect()

try:
    reader.join(None)
finally:
    reader.disconnect()
```

Runnable version: [`examples/basic_inventory.py`](examples/basic_inventory.py).

## 17. RF telemetry

Use `standard` for portable LLRP telemetry or `zebra` for supported Zebra/Motorola phase and physical-port extensions:

```python
from sllurp.llrp import LLRPReaderConfig

config = LLRPReaderConfig({
    "antennas": [1, 2],
    "rf_telemetry_mode": "zebra",
    "dedup_seconds": None,
})
```

Sllurp acquires and normalizes observations; localization/vector math belongs in the consuming application or a higher-level library.

See [RF telemetry](docs/rf-telemetry.rst) and [`examples/rf_telemetry.py`](examples/rf_telemetry.py).

## 18. Dynamic runtime configuration

Use `apply_config()` for controlled runtime changes:

```python
from sllurp.llrp import LLRPReaderConfig

new_config = LLRPReaderConfig({
    "antennas": [1, 2],
    "tx_power": 0,
})

transition = reader.apply_config(new_config)
print(transition)
```

Inspect desired/generated/applied/reported state:

```python
state = reader.llrp.get_config_state()
print(state)
```

See [Runtime state and dynamic configuration](docs/runtime-state.rst) and [`examples/runtime_config.py`](examples/runtime_config.py).

## 19. Generic HTTP/HTTPS reader management

LLRP inventory and vendor web management are separate protocols:

```python
from sllurp.reader_management import HTTPReaderManager

manager = HTTPReaderManager(
    "https://reader.example",
    username="admin",
    password="secret",
)

settings = manager.get_settings("/api/settings")
manager.update_settings(
    "/api/settings",
    {"rfid": {"enabled": True}},
    method="PATCH",
)
```

See [Reader management and deduplication](docs/reader-management.rst) and [`examples/reader_management_generic.py`](examples/reader_management_generic.py).

## 20. Zebra management

```python
from sllurp.zebra_management import zebra_reader_manager

manager = zebra_reader_manager(
    "FXR90",
    "https://reader.example",
    username="admin",
    password="secret",
)

print(manager.get_info())
print(manager.get_status())
```

See [Reader management](docs/reader-management.rst) and [`examples/zebra_management.py`](examples/zebra_management.py).

## 21. Impinj R700/R720 management

```python
from sllurp.impinj_management import ImpinjRESTManager

manager = ImpinjRESTManager(
    "https://impinj-r700.example",
    model="R700",
    username="root",
    password="your-reader-password",
)

print(manager.get_status())
```

See [Impinj management](docs/impinj-management.rst) and [`examples/impinj_management.py`](examples/impinj_management.py).

## 22. Honeywell / Intermec IF-series management

IF1/IF2/IF61 management uses the reader-published DCWS WSDL and SOAP operations:

```python
from sllurp.reader_management import create_reader_manager

manager = create_reader_manager(
    "IF2",
    "https://reader.example",
    username="admin",
    password="secret",
)

print(manager.list_operations())
```

See [Honeywell / Intermec management](docs/intermec-management.rst) and [`examples/intermec_management.py`](examples/intermec_management.py).

## 23. Reader compatibility

Reader support is capability-driven. Do not assume all SKUs expose the same antenna count, TLS service, web-management API, or vendor telemetry.

See [Reader compatibility](docs/readers.rst).

## 24. Runnable examples

The [`examples/README.md`](examples/README.md) index groups the runnable examples by feature. It includes Python inventory, deduplication, RF telemetry, runtime configuration, generic and vendor management, CLI recipes, and a FastAPI/WebSocket integration demo.

The documentation-oriented map is in [`docs/examples.rst`](docs/examples.rst).

## 25. Troubleshooting

### Connection refused or timeout

- Confirm the reader IP/DNS name.
- Confirm LLRP is enabled.
- Confirm the computer can reach the reader network.
- Check firewall/VLAN rules.
- Confirm port 5084 for plain LLRP or the reader's configured port.
- For TLS, confirm the secure service and port, normally 5085.

### TLS certificate errors

Prefer the correct CA bundle and `--tls-server-hostname` when connecting by IP to a certificate issued to a DNS name.

### Reader left in an unexpected LLRP state

```bash
sllurp reset READER_HOST
```

### Detailed diagnostics

```bash
sllurp --debug inventory READER_HOST
sllurp --debug --logfile sllurp.log inventory READER_HOST
```

## 26. Documentation

- [User guide](USER_GUIDE.md)
- [Developer guide](DEVELOPER_GUIDE.md)
- [Documentation index](docs/index.rst)
- [Example guide](docs/examples.rst)
- [Reader compatibility](docs/readers.rst)
- [Secure LLRP](docs/secure_llrp.rst)
- [Reader management and deduplication](docs/reader-management.rst)
- [Impinj management](docs/impinj-management.rst)
- [Honeywell / Intermec management](docs/intermec-management.rst)
- [RF telemetry](docs/rf-telemetry.rst)
- [Runtime state and dynamic configuration](docs/runtime-state.rst)

For every CLI command, `--help` is authoritative for the installed version:

```bash
sllurp --version
sllurp --help
sllurp inventory --help
sllurp access --help
sllurp log --help
sllurp reset --help
```

