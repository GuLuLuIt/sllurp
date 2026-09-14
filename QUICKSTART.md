# Sllurp Quick Start

This guide is the fastest path from a new computer to a working LLRP inventory, and then into the advanced features included in this fork: secure LLRP/TLS, timed deduplication, reader management, runtime configuration, RF telemetry, Impinj extensions, tag access, logging, and multi-reader use.

> **Need the full feature set from this repository?** Install from `GuLuLuIt/sllurp` `main`. The package currently published as `sllurp` on PyPI may lag the feature set in this fork.

## 1. Requirements

- Python **3.10 or newer**
- Network access from your computer to the RFID reader
- LLRP enabled on the reader
- TCP **5084** for normal LLRP, unless the reader uses another configured port
- TCP **5085** for Secure LLRP/TLS when the reader exposes the standard encrypted endpoint
- HTTP/HTTPS access only when you use a vendor reader-management API

Check Python first:

```text
python --version
```

On Linux/macOS the command may be `python3 --version`.

## 2. Install on Windows

### Windows 10/11 with PowerShell

Install Python and Git with `winget` if you do not already have them:

```powershell
winget install Python.Python.3.12
winget install Git.Git
```

Open a new PowerShell window, then create an isolated environment:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

Install the current full-feature fork:

```powershell
python -m pip install "git+https://github.com/GuLuLuIt/sllurp.git@main"
```

Or install the currently published PyPI release:

```powershell
python -m pip install sllurp
```

If PowerShell activation is restricted, use the virtual-environment Python directly:

```powershell
.\.venv\Scripts\python.exe -m pip install "git+https://github.com/GuLuLuIt/sllurp.git@main"
.\.venv\Scripts\sllurp.exe --help
```

### Windows Command Prompt

```bat
py -3.12 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install "git+https://github.com/GuLuLuIt/sllurp.git@main"
```

## 3. Install on Linux

### Ubuntu / Debian / Linux Mint / Raspberry Pi OS

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install "git+https://github.com/GuLuLuIt/sllurp.git@main"
```

### Fedora / RHEL / Rocky Linux / AlmaLinux

```bash
sudo dnf install -y python3 python3-pip git
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install "git+https://github.com/GuLuLuIt/sllurp.git@main"
```

### Arch Linux / Manjaro

```bash
sudo pacman -S --needed python python-pip git
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install "git+https://github.com/GuLuLuIt/sllurp.git@main"
```

### openSUSE / SUSE

```bash
sudo zypper install python3 python3-pip git
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install "git+https://github.com/GuLuLuIt/sllurp.git@main"
```

## 4. Install on macOS

With Homebrew:

```bash
brew install python git
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install "git+https://github.com/GuLuLuIt/sllurp.git@main"
```

## 5. Install from a source checkout

Use this when developing Sllurp itself:

```bash
git clone https://github.com/GuLuLuIt/sllurp.git
cd sllurp
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

On Windows, replace the activation command with `.\.venv\Scripts\Activate.ps1`.

Run the test suite after a development install:

```bash
python -m pip install -e ".[test]"
pytest -q
```

## 6. Verify the installation

```bash
sllurp --help
sllurp inventory --help
```

If the `sllurp` launcher is not on your shell PATH, run it through the virtual environment or reinstall while the environment is activated.

## 7. First inventory in 60 seconds

Replace `192.168.1.50` with your reader address:

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

Use multiple readers in the same command:

```bash
sllurp inventory -a 0 192.168.1.50 192.168.1.51
```

If a debugging session leaves a reader in an unexpected LLRP state:

```bash
sllurp reset 192.168.1.50
```

## 8. Timed tag deduplication

Suppress repeated EPC callbacks for two seconds:

```bash
sllurp inventory --dedup-seconds 2 --dedup-backend auto -a 0 192.168.1.50
```

Backends:

- `auto` prefers supported reader-side behavior and otherwise uses memory
- `hardware` requires the necessary advertised reader capability
- `memory` always deduplicates in the client

For RF telemetry, prefer raw observations (`dedup_seconds=None`) or memory deduplication so cross-antenna observations are not collapsed.

## 9. Secure LLRP / TLS

Normal LLRP defaults to TCP 5084. `--tls` defaults to TCP 5085 unless you also pass `--port`.

Reader certificate signed by a trusted CA:

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

`--tls-no-verify` is intended for controlled testing only. Prefer installing/supplying the correct CA for normal deployments.

See [Secure LLRP](docs/secure_llrp.rst).

## 10. Impinj inventory extensions

Single-target or dual-target search mode:

```bash
sllurp inventory --impinj-search-mode 2 192.168.1.50
```

Request Impinj phase/RSSI/Doppler report extensions:

```bash
sllurp inventory --impinj-reports -a 0 192.168.1.50
```

Fixed-frequency extension where supported:

```bash
sllurp inventory --impinj-fixed-frequency -f 1,2 -a 0 192.168.1.50
```

## 11. Tag memory access

Read two 16-bit words from the default User memory bank:

```bash
sllurp access --read-words 2 --count 1 192.168.1.50
```

Select another bank and word pointer when required:

```bash
sllurp access --read-words 2 --memory-bank 2 --word-ptr 0 --count 1 192.168.1.50
```

Use `sllurp access --help` before write operations. Tag writes change tag memory and should be tested with disposable/test tags first.

## 12. Stream tag data to a file

```bash
sllurp log -a 0 -o tags.csv 192.168.1.50
```

Use reader-provided timestamps:

```bash
sllurp log -a 0 --reader-timestamp -o tags.csv 192.168.1.50
```

## 13. Minimal Python API

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

## 14. RF telemetry mode

Use `standard` for portable LLRP telemetry or `zebra` for Zebra/Motorola phase and physical-port extensions where firmware supports them:

```python
from sllurp.llrp import LLRPReaderConfig

config = LLRPReaderConfig({
    "antennas": [1, 2],
    "rf_telemetry_mode": "zebra",
    "dedup_seconds": None,
})
```

Telemetry mode preserves per-antenna observations for RF analysis. Sllurp acquires and normalizes observations; localization/vector math belongs in the consuming application or a higher-level library.

See [RF telemetry](docs/rf-telemetry.rst).

## 15. Dynamic runtime configuration

Use `apply_config()` for controlled changes while the client is running:

```python
from sllurp.llrp import LLRPReaderConfig

new_config = LLRPReaderConfig({
    "antennas": [1, 2],
    "tx_power": 0,
})

transition = reader.apply_config(new_config)
print(transition)
```

Sllurp classifies changes as client-only, ROSpec, reader-configuration, or reconnect-required changes so settings are not silently half-applied.

Inspect desired/generated/applied/reported state with:

```python
state = reader.llrp.get_config_state()
print(state)
```

See [Runtime state and dynamic configuration](docs/runtime-state.rst).

## 16. Generic HTTP/HTTPS reader management

LLRP inventory and vendor web management are separate protocols. For a documented HTTP/HTTPS API:

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

The transport supports Basic/Bearer authentication, verified TLS, custom CAs, client certificates, safe same-origin handling, and normalized management errors.

See [Reader management and deduplication](docs/reader-management.rst).

## 17. Zebra management

Use the model-aware factory so unsupported operations are rejected rather than guessed:

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

Supported adapters cover classic Zebra Reader Management XML where documented and Zebra IoT Connector local REST on supported firmware/models.

See [Reader management](docs/reader-management.rst).

## 18. Impinj R700/R720 management

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

The R700-series adapter exposes documented `/api/v1` settings plus generic methods for firmware-documented resources. Legacy Speedway-family readers are not falsely treated as R700 REST devices.

See [Impinj management](docs/impinj-management.rst).

## 19. Honeywell / Intermec IF-series management

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

The exact commands are discovered from that reader's `DeviceConfiguration.wsdl` instead of being invented in Sllurp.

See [Honeywell / Intermec management](docs/intermec-management.rst).

## 20. Reader compatibility and capabilities

Reader support is capability-driven. Do not assume all SKUs expose the same antenna count, TLS service, web-management API, or vendor telemetry.

See [Reader compatibility](docs/readers.rst) for Zebra/Motorola, Impinj, Honeywell/Intermec, ThingMagic/JADAK, and Alien families.

## 21. Troubleshooting

### Connection refused or timeout

- Confirm the reader IP/DNS name.
- Confirm LLRP is enabled.
- Confirm your PC can reach the reader network.
- Check firewall/VLAN rules.
- Confirm port 5084 for plain LLRP or the reader's configured LLRP port.
- For TLS, confirm the secure service and port (normally 5085).

### TLS certificate errors

Do not immediately disable verification. Prefer the correct CA bundle and `--tls-server-hostname` when connecting by IP to a certificate issued to a DNS name.

### Reader left in a strange LLRP state

```bash
sllurp reset READER_HOST
```

### Need detailed diagnostics

```bash
sllurp --debug inventory READER_HOST
```

Write logs to a file:

```bash
sllurp --debug --logfile sllurp.log inventory READER_HOST
```

## 22. Where to go next

- [Documentation index](docs/index.rst)
- [Reader compatibility](docs/readers.rst)
- [Secure LLRP](docs/secure_llrp.rst)
- [Reader management and deduplication](docs/reader-management.rst)
- [Impinj management](docs/impinj-management.rst)
- [Honeywell / Intermec management](docs/intermec-management.rst)
- [RF telemetry](docs/rf-telemetry.rst)
- [Runtime state and dynamic configuration](docs/runtime-state.rst)

For every CLI command, `--help` is the authoritative list of options for the installed version:

```bash
sllurp --help
sllurp inventory --help
sllurp access --help
sllurp log --help
sllurp reset --help
```
