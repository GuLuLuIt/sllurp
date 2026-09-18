# Sllurp 3.1.2 API reference

This reference covers the supported application-facing Python API in Sllurp
3.1.2. It is organized around tasks and includes copyable examples. For
installation and command-line use, start with [QUICKSTART.md](QUICKSTART.md).
For operating a long-running deployment, use [USER_GUIDE.md](USER_GUIDE.md).

All addresses, credentials, certificate names, EPCs, and settings below are
placeholders. Replace them with values for your reader and environment.

## API map

| Module | Use it for | Main interfaces |
|---|---|---|
| `sllurp.llrp` | Inventory, callbacks, live configuration, and tag access | `LLRPReaderConfig`, `LLRPReaderClient`, `LLRPReaderState`, `C1G2*` operations |
| `sllurp.secure` | Direct TLS client construction and custom SSL contexts | `LLRPTLSReaderClient`, `SecureLLRPReaderClient`, `create_ssl_context` |
| `sllurp.dedup` | Standalone timed deduplication | `TagReportDeduplicator`, `default_tag_key` |
| `sllurp.llrp_runtime` | Inspect live-configuration plans and results | `ConfigChange`, `ConfigTransitionPlan`, `ConfigTransition` |
| `sllurp.readers` | Look up known reader families and Secure LLRP status | `ReaderProfile`, `get_reader_profile`, `iter_reader_profiles` |
| `sllurp.reader_management` | Call documented HTTP/HTTPS management endpoints | `HTTPReaderManager`, `create_reader_manager` |
| `sllurp.zebra_management` | Zebra Reader Management and IoT Connector APIs | `ZebraRMManager`, `ZebraIoTConnectorManager`, `zebra_reader_manager` |
| `sllurp.impinj_management` | Impinj R700/R720 documented REST API | `ImpinjRESTManager` |
| `sllurp.intermec_management` | Honeywell/Intermec IF-series DCWS/SOAP API | `IntermecDCWSManager` |
| `sllurp.epc` | GTIN and SGTIN-96 conversion | GTIN helpers and `parse_sgtin_96*` |
| `sllurp.llrp_errors` | Catch protocol and configuration failures | `LLRPError`, `LLRPResponseError`, `ReaderConfigurationError` |

## Install and verify 3.1.2

Install the immutable GitHub release:

```bash
python -m pip install "git+https://github.com/GuLuLuIt/sllurp.git@v3.1.2"
sllurp --version
```

The expected version output contains `3.1.2`. The `sllurp` project on PyPI is
the upstream distribution, not this GuLuLuIT build.

## Minimal inventory client

This program inventories all reader-reported antennas until interrupted:

```python
from sllurp.llrp import LLRPReaderClient, LLRPReaderConfig


def on_tags(reader, tag_reports):
    host, port = reader.get_peername()
    for tag in tag_reports:
        epc = tag.get("EPC") or tag.get("EPCData")
        print(host, port, epc, tag.get("AntennaID"), tag.get("PeakRSSI"))


config = LLRPReaderConfig(
    {
        "antennas": [0],
        "ro_report_every_n_tags": 1,
        "tag_content_selector": {
            "EnableAntennaID": True,
            "EnablePeakRSSI": True,
            "EnableChannelIndex": True,
            "EnableLastSeenTimestamp": True,
            "EnableTagSeenCount": True,
        },
    }
)
reader = LLRPReaderClient("192.0.2.10", config=config)
reader.add_tag_report_callback(on_tags)
reader.connect()

try:
    reader.join()
except KeyboardInterrupt:
    pass
finally:
    reader.disconnect(timeout=2)
```

`connect()` starts the receive thread by default. `join()` waits for it, and
`disconnect()` requests a polite shutdown. A tag callback receives the client
and a list of decoded tag dictionaries. Keys are present only when the reader
reports them and the relevant selectors are enabled.

The complete runnable form is
[`examples/basic_inventory.py`](examples/basic_inventory.py).

## `LLRPReaderConfig`

Create a configuration with `LLRPReaderConfig(mapping)`. Unknown mapping keys
are ignored for backward compatibility; misspelled names therefore do not
raise an error. Prefer explicit, reviewed dictionaries and tests for shared
configuration.

### Session and lifecycle fields

| Field | Default | Meaning |
|---|---:|---|
| `antennas` | `[1]` | Antenna IDs. `[0]` means all reader-reported antennas and cannot be combined with other IDs. |
| `duration` | `None` | Inventory duration in seconds. Supplying a positive duration also enables disconnect-on-completion unless overridden. |
| `disconnect_when_done` | `False` | Disconnect after the configured duration finishes. |
| `start_inventory` | `True` | Start inventory during connection setup. |
| `reset_on_connect` | `True` | Clear conflicting reader state before configuring the session. |
| `reconnect` | `False` | Attempt reconnection after an unexpected disconnect. |
| `reconnect_retries` | `5` | Retry count; `-1` means unlimited retries. |
| `reconnect_delay` | `60.0` | Delay between retries, in seconds. |
| `request_timeout` | `None` | Optional positive per-request timeout, in seconds. |
| `keepalive_interval` | `60000` | Requested keepalive interval in milliseconds; `0` disables the request. |

### Reporting, deduplication, and observations

| Field | Default | Meaning |
|---|---:|---|
| `ro_report_every_n_tags` | `None` | Deliver a continuous report after N observations without ending the antenna inventory. Valid values are 1–65535. |
| `report_every_n_tags` | `None` | Compatibility field that stops the antenna inventory at the count boundary. Use `ro_report_every_n_tags` for continuous delivery. |
| `report_timeout_ms` | `0` | Compatibility timeout that stops the antenna inventory. |
| `dedup_seconds` | `None` | Positive integer suppression window in seconds; `None` disables timed deduplication. |
| `dedup_backend` | `"auto"` | `auto`, `hardware`, or `memory`. `auto` selects compatible hardware support or falls back to memory. |
| `dedup_max_entries` | `1000000` | Maximum client-side deduplication entries. |
| `rf_telemetry_mode` | `"off"` | `off`, `standard`, or `zebra`. Standard mode enables common RF fields; Zebra mode also requests supported Zebra observations. |
| `tag_content_selector` | mapping | Standard fields to request in tag reports. |
| `event_selector` | mapping | Reader events to request. |

Continuous cadence and timed deduplication solve different problems. Cadence
controls when reports are delivered; deduplication controls whether a repeated
observation is delivered:

```python
config = LLRPReaderConfig(
    {
        "antennas": [0],
        "ro_report_every_n_tags": 25,
        "dedup_seconds": 2,
        "dedup_backend": "auto",
        "dedup_max_entries": 100_000,
    }
)
```

### RF and air-protocol fields

| Field | Default | Meaning |
|---|---:|---|
| `session` | `2` | Gen2 session used for inventory. |
| `tari` | `0` | Tari in nanoseconds; `0` lets reader/mode selection supply it. |
| `mode_identifier` | `None` | Reader-advertised RF mode identifier. |
| `tag_population` | `4` | Estimated tag population used for singulation. |
| `tx_power` | `0` | Reader power-table index, as one integer or an antenna-to-index mapping. `0` uses the reader's selected/default entry. |
| `tx_power_dbm` | `None` | Requested dBm, as one number or an antenna-to-dBm mapping. Sllurp chooses the closest advertised value. |
| `tag_filter_mask` | `None` | Optional EPC filter mask used by inventory. |
| `frequencies` | mapping | Hop table, channel list, and automatic-selection settings. Multi-channel/fixed-frequency extensions require compatible Impinj support. |
| `gpi_ports_config` | `{}` | Mapping of GPI port number to enabled state. |

Power-table indexes are not dBm values. To request 27.0 dBm on antennas 1 and
2, use `tx_power_dbm`, not `tx_power`:

```python
config = LLRPReaderConfig(
    {
        "antennas": [1, 2],
        "tx_power_dbm": {1: 27.0, 2: 27.0},
        "session": 2,
        "tag_population": 32,
    }
)
```

### Transport and size fields

| Field | Default | Meaning |
|---|---:|---|
| `tls_enabled` | `False` | Use Secure LLRP/TLS. The client defaults to port 5085 when enabled. |
| `tls_verify` | `True` | Verify the certificate chain and hostname. |
| `tls_ca_file` | `None` | Private CA bundle path. |
| `tls_client_cert` | `None` | Client certificate for mutual TLS. |
| `tls_client_key` | `None` | Client private-key path; requires `tls_client_cert`. |
| `tls_server_hostname` | `None` | Certificate/SNI name when it differs from the connection address. |
| `socket_receive_buffer_bytes` | `1048576` | Requested OS socket receive buffer in bytes; `None` leaves it unchanged. |
| `max_message_size` | `16777216` | Maximum accepted LLRP frame size in bytes; `None` removes the application limit. |

The configuration also exposes documented Impinj and Zebra extension fields.
Use those only on compatible reader models; see
[`docs/readers.rst`](docs/readers.rst) and the focused feature pages in
[`docs/index.rst`](docs/index.rst).

Construction validates field combinations and raises `LLRPError` for invalid
values. It also normalizes a scalar `tx_power` or `tx_power_dbm` across every
selected antenna.

## `LLRPReaderClient`

Create a client with:

```python
LLRPReaderClient(host, port=None, config=None, timeout=5.0)
```

When `port` is omitted, the client uses TCP 5084 for plain LLRP or 5085 when
`config.tls_enabled` is true.

### Lifecycle methods

| Method or property | Result |
|---|---|
| `connect(start_main_loop=True)` | Connect and normally start the receive thread. |
| `disconnect(timeout=0)` | Request polite shutdown and optionally wait up to `timeout` seconds. |
| `hard_disconnect()` | Close the transport immediately and clear session state. |
| `join(timeout=None)` | Wait for the receive thread. |
| `is_alive()` | Report whether the receive thread is alive. |
| `get_peername()` | Return the configured `(host, port)` without resolving the hostname. |
| `dedup_backend_active` | Return `disabled`, `hardware`, or `memory` for the current session. |
| `disconnect_all_readers(timeout_per_reader=1, force=True)` | Class method that closes clients tracked by the process. |

Use `hard_disconnect()` for failed transports or shutdown recovery, not as the
normal first choice. Wrap normal sessions in `try`/`finally` so a raised
application exception does not leave the reader configured for inventory.

### Callbacks

| Registration | Callback signature | Data |
|---|---|---|
| `add_tag_report_callback(cb)` | `cb(reader, tag_reports)` | List of decoded `TagReportData` dictionaries. |
| `add_event_callback(cb)` | `cb(reader, event_data)` | Decoded reader-event mapping. |
| `add_state_callback(state, cb)` | `cb(reader, state)` | One `LLRPReaderState` transition. |
| `add_message_callback(name, cb)` | `cb(reader, message)` | Decoded `LLRPMessage` for the named message type. |
| `add_disconnected_callback(cb)` | `cb(reader)` | Final disconnect notification. |

Each `add_*` method has a matching `remove_*` method, and callback collections
also have `clear_*` methods. Registering the same callable twice does not
create duplicate registrations.

Callbacks normally run synchronously on the receive thread. Keep them short.
Do not call `ConfigTransition.wait()` or otherwise wait for a reader response
inside a callback: the blocked receive thread is the code that must process
that response. Hand longer work to a bounded application queue:

```python
from queue import Full, Queue

work = Queue(maxsize=1000)


def on_tags(reader, reports):
    try:
        work.put_nowait((reader.get_peername(), reports))
    except Full:
        # Record a metric or apply the application's overload policy.
        pass
```

## Live configuration

`update_config(new_config)` replaces configuration only while the client is
fully disconnected. `apply_config(new_config)` performs a controlled live
transition and returns a `ConfigTransition`.

```python
from sllurp.llrp import LLRPReaderClient, LLRPReaderConfig

reader = LLRPReaderClient(
    "192.0.2.10",
    config=LLRPReaderConfig({"antennas": [1], "tx_power_dbm": 24.0}),
)
reader.connect()

updated = LLRPReaderConfig(
    {"antennas": [1, 2], "tx_power_dbm": 27.0, "dedup_seconds": 2}
)
transition = reader.apply_config(updated)

if not transition.wait(timeout=10):
    print("configuration operation is still pending")
elif transition.succeeded:
    print("applied actions:", sorted(transition.plan.actions))
else:
    print("configuration failed:", transition.error)

print(reader.llrp.get_config_state())
reader.disconnect(timeout=2)
```

A transition action is one of:

| Action | What Sllurp must do |
|---|---|
| `client` | Change only local runtime behavior. |
| `rospec` | Restart/rebuild the inventory ROSpec. |
| `reader_config` | Send reader configuration. |
| `reconnect` | Establish a new transport/session. |

`get_config_state()` returns detached `desired`, `generated`, `applied`, and
reader-reported snapshots where available. Mutating the returned object does
not mutate the active session.

See [`examples/runtime_config.py`](examples/runtime_config.py) for a complete
runnable program.

## Secure LLRP/TLS

The easiest route is TLS fields in `LLRPReaderConfig`:

```python
config = LLRPReaderConfig(
    {
        "tls_enabled": True,
        "tls_ca_file": "reader-ca.pem",
        "tls_server_hostname": "reader.example",
        "antennas": [0],
    }
)
reader = LLRPReaderClient("192.0.2.10", config=config)
```

For a custom SSL context or direct secure-client construction:

```python
from sllurp.llrp import LLRPReaderConfig
from sllurp.secure import LLRPTLSReaderClient, create_ssl_context

context = create_ssl_context(
    cafile="reader-ca.pem",
    certfile="client-cert.pem",
    keyfile="client-key.pem",
)
reader = LLRPTLSReaderClient(
    "192.0.2.10",
    config=LLRPReaderConfig({"antennas": [0]}),
    ssl_context=context,
    server_hostname="reader.example",
)
```

`SecureLLRPReaderClient` is a supported descriptive alias for
`LLRPTLSReaderClient`. Certificate verification is enabled by default. A TLS
failure should be fixed by supplying the correct CA and hostname; disabling
verification is intended only for controlled diagnostics.

## Standalone report deduplication

Reader clients can enable deduplication through `LLRPReaderConfig`. To apply
the same bounded algorithm to reports received elsewhere, use:

```python
from sllurp.dedup import TagReportDeduplicator

deduplicator = TagReportDeduplicator(
    window_seconds=2,
    include_antenna=True,
    max_entries=100_000,
)

filtered = deduplicator.filter(tag_reports)
print("active identities:", deduplicator.entry_count)
print("capacity evictions:", deduplicator.evictions)
deduplicator.reset()
```

`default_tag_key(tag, include_antenna=False)` produces the standard identity.
Set `include_antenna=True` when the same EPC observed on two antennas must be
treated as two observations. `filter()` returns only reports not suppressed by
the current window.

## Tag-memory operations

`start_access_spec(op_spec, target_spec=None, stop_after_count=0,
access_spec_id=1)` asynchronously adds and starts one AccessSpec. Common
operation classes are `C1G2Read`, `C1G2Write`, `C1G2Lock`, and `C1G2Kill`;
block operations are also available for compatible readers/tags.

These operations can permanently alter or lock tag memory. Test with
disposable tags and non-production passwords first. The command-line access
workflow is the safest starting point because its installed help documents
the required word pointers, banks, counts, and passwords:

```bash
sllurp access --help
sllurp access --read-words 2 --count 1 192.0.2.10
```

For programmatic use, construct a typed operation and optional
`C1G2TargetTag`, register the relevant message callback, and call
`start_access_spec()`. Completion is asynchronous; the method does not return
the tag data directly.

## Reader compatibility registry

Use the registry when an application needs model-aware defaults without
hard-coding vendor names:

```python
from sllurp.readers import (
    default_llrp_port,
    get_reader_profile,
    iter_reader_profiles,
    supports_secure_llrp,
)

profile = get_reader_profile("R700")
if profile:
    print(profile.vendor, profile.family, profile.models)
    print(profile.secure_llrp, profile.notes)

print(default_llrp_port(secure=True))  # 5085
print(supports_secure_llrp("FX9600"))  # True

for known in iter_reader_profiles(secure_only=True):
    print(known.key, known.models)
```

`supports_secure_llrp()` returns `True`, `False`, or `None`. `None` means the
capability is unknown or not verified, not that TLS is unavailable.

## Reader management APIs

Management APIs configure the reader device; LLRP controls RFID inventory.
Only call endpoints documented for the exact model and firmware. Network,
service, certificate, region, reboot, and firmware operations can interrupt
access to the reader.

### Generic HTTP/HTTPS

```python
import os

from sllurp.reader_management import HTTPReaderManager, ReaderManagementError

manager = HTTPReaderManager(
    "https://reader.example",
    username=os.environ["READER_USERNAME"],
    password=os.environ["READER_PASSWORD"],
    ca_file="reader-ca.pem",
    timeout=5.0,
)

try:
    current = manager.get_settings("/documented/api/settings")
    updated = manager.update_settings(
        "/documented/api/settings",
        {"documentedField": "documentedValue"},
    )
except ReaderManagementError as exc:
    print(exc.status, exc.body)
    raise
```

`HTTPReaderManager` also supports a `bearer_token`, default headers, mutual-TLS
certificate files, `request(method, path, ...)`, and
`replace_settings(path, settings)`. Requests are restricted to the configured
origin so authentication is not forwarded to another host.

### Model-aware factory

```python
import os

from sllurp.reader_management import create_reader_manager

manager = create_reader_manager(
    "R700",
    "https://reader.example",
    username=os.environ["READER_USERNAME"],
    password=os.environ["READER_PASSWORD"],
    ca_file="reader-ca.pem",
)
print(manager.get_status())
```

`create_reader_manager(model, base_url, vendor=None, api="auto", **kwargs)`
selects a documented adapter for known Zebra, Impinj R700/R720, and
Honeywell/Intermec IF-series models. It deliberately rejects unsupported
private web interfaces instead of guessing endpoints.

Use the vendor-specific runnable examples for login/session rules and method
names:

- [`examples/zebra_management.py`](examples/zebra_management.py)
- [`examples/impinj_management.py`](examples/impinj_management.py)
- [`examples/intermec_management.py`](examples/intermec_management.py)
- [`examples/reader_management_generic.py`](examples/reader_management_generic.py)

## EPC utilities

```python
from sllurp.epc.gtin import calculate_check_digit, combine_gtin_with_check_digit
from sllurp.epc.sgtin_96 import parse_sgtin_96, parse_sgtin_96_to_uri

print(calculate_check_digit("061414100734"))
print(combine_gtin_with_check_digit("061414100734"))

decoded = parse_sgtin_96("3034257BF7194E4000001A85")
print(decoded["company_prefix"], decoded["item_reference"], decoded["serial"])
print(parse_sgtin_96_to_uri("3034257BF7194E4000001A85"))
```

Invalid length, hexadecimal content, header, or partition values raise
`ValueError`.

## Exceptions and failure handling

| Exception | Catch it when |
|---|---|
| `sllurp.llrp_errors.LLRPError` | Configuration, encoding, decoding, or general LLRP processing fails. |
| `sllurp.llrp_errors.LLRPResponseError` | A reader response reports a protocol failure. |
| `sllurp.llrp_errors.ReaderConfigurationError` | A requested state or configuration transition cannot be performed safely. |
| `sllurp.reader_management.ReaderManagementError` | An HTTP/SOAP management request or response fails. Inspect `status` and `body` when available. |
| `sllurp.reader_management.UnsupportedReaderOperation` | A requested model/API combination has no supported documented adapter. |

Do not catch `Exception` around the entire lifetime and continue as if the
reader were still configured. Log the operation and reader identity, perform
cleanup, and decide explicitly whether to retry or fail the service.

## Compatibility and API boundaries

No supported public API is scheduled for removal in 3.1.2.

- Use `ro_report_every_n_tags` for continuous report cadence.
  `report_every_n_tags` and `report_timeout_ms` remain supported for their
  historical antenna-inventory stop behavior.
- The legacy frequency key `Channelist` is accepted and normalized. New code
  should use `ChannelList`.
- `SecureLLRPReaderClient` and `LLRPTLSReaderClient` are both supported.
- Modules and names beginning with `_`, decoder compatibility helpers, and
  direct mutation of protocol state are implementation details, not the
  application API.
- Low-level message dictionaries mirror LLRP protocol names and therefore do
  not promise the same convenience-level stability as the client,
  configuration, registry, management, and EPC interfaces documented here.

For the cumulative feature and fix record, see [CHANGELOG.md](CHANGELOG.md).
For release-specific installation, artifacts, and compatibility notes, see
[RELEASE_NOTES.md](RELEASE_NOTES.md).

## Callback and thread-context contract

Each normally connected `LLRPReaderClient` owns one receive thread. It decodes
complete frames, advances the state machine, resolves request completions, and
invokes most application callbacks synchronously. Callback lists are copied
under a lock and invoked after the lock is released, so a callback may safely
add or remove callbacks while dispatch is in progress.

| Registration | Exact signature | Return value used? | Execution context |
|---|---|---:|---|
| `add_state_callback(state, cb)` | `cb(reader, state)` | No | Receive thread |
| `add_message_callback(name, cb)` | `cb(reader, message)` | No | Receive thread |
| `add_tag_report_callback(cb)` | `cb(reader, tag_reports)` | No | Receive thread, after optional memory dedup |
| `add_event_callback(cb)` | `cb(reader, event_data)` | No | Receive thread |
| `add_disconnected_callback(cb)` | `cb(reader)` | No | Receive thread, duration-timer thread, or cleanup caller |
| `apply_config(config, onCompletion=cb)` | `cb(transition)` | No | Caller for immediate completion; otherwise receive thread |
| Low-level protocol completion | `cb(state, is_success, *args)` | No | Receive thread |

Callback exceptions are logged and isolated; later callbacks still run. A
disconnect callback runs at most once for a transport session. Application data
shared between callbacks and other threads still needs application-level
synchronization.

Never call `join()`, `ConfigTransition.wait()`, or another operation that waits
for a reader response from a receive callback. The blocked thread is the thread
that must receive the response. Hand blocking work to a queue instead. A custom
key function supplied to `TagReportDeduplicator` may be called concurrently by
different reader threads and must also be thread-safe.

## Complete extension configuration fields

The main configuration tables above cover all standard and transport fields.
These vendor-extension fields complete the schema. They are not defined by the
GS1 base specification and require matching reader firmware.

| Field | Type/default | Meaning | Live action |
|---|---|---|---|
| `impinj_extended_configuration` | bool, `False` | Negotiate Impinj extensions during session setup. | Reconnect |
| `impinj_fixed_frequency` | bool, `False` | Use Impinj custom frequency configuration. Required by this implementation for automatic or multi-channel selection. | ROSpec restart |
| `impinj_search_mode` | value or `None`, `None` | Impinj inventory search-mode value. | ROSpec restart |
| `impinj_reports` | bool, `False` | Enable Impinj custom report parameters. | ROSpec restart |
| `impinj_tag_content_selector` | mapping or `None`, `None` | Impinj RF phase/RSSI/Doppler report selectors. Values are booleans. | ROSpec restart |
| `impinj_event_selector` | mapping or `None`, `None` | Impinj custom reader-event selectors. | `SET_READER_CONFIG` |
| `zebra_tag_content_selector` | mapping or `None`, `None` | Zebra zone, physical antenna port, phase, GPS, and MLT report selectors. Values are booleans. | ROSpec restart |

Unknown configuration fields are conservatively classified as requiring a
reconnect by the transition planner. This prevents a newly introduced field
from being silently treated as safe for a live session.

## Return values and failure behavior

| API | Return | Raises / asynchronous failure |
|---|---|---|
| `LLRPReaderClient.connect()` | `None` | `ReaderConfigurationError` if already connected; native `OSError` or `ssl.SSLError` when connection/retry fails. Setup continues asynchronously. |
| `disconnect()` / `hard_disconnect()` | `None` | Cleanup contains socket-shutdown errors. A finite disconnect timeout limits only the join; check `is_alive()`. |
| `start_access_spec()` | `None` | `ValueError` for wrong operation/target types. Reader acceptance and tag-operation results arrive asynchronously. |
| `update_config()` | `None` | Validation failure or `ReaderConfigurationError` if any transport/protocol state is live; no local partial update. |
| `apply_config()` | `ConfigTransition` | Reconnect-only live changes and invalid states raise `ReaderConfigurationError` before transition. Protocol failures appear in `transition.error`. |
| `ConfigTransition.wait(timeout)` | bool | `True` if terminal, `False` on timeout; does not raise the stored error. Timeout is seconds or `None`. |
| `LLRPMessage(msgdict=.../msgbytes=...)` | message object | `LLRPError` for missing, unknown, truncated, or invalid data. |
| Header decoders | tuples described below | `ValueError` for structurally impossible declared lengths; truncated streaming headers return an empty/no-value tuple. |
| `HTTPReaderManager.request()` | immutable `ReaderHTTPResponse` | `ValueError` for invalid local arguments; `ReaderManagementError` for transport or non-success HTTP response. |
| `ReaderHTTPResponse.json()` | decoded JSON or `None` | `json.JSONDecodeError` for a non-empty malformed body. |

`ReaderHTTPResponse.status` is an integer, `headers` is a string mapping,
`body` is bytes, and `text` is UTF-8 decoded with replacement. Management
methods are synchronous and run on the calling thread.

## Live-transition invariants and rollback

`apply_config()` classifies each changed field as `client`, `rospec`,
`reader_config`, or `reconnect`. Client-only changes commit immediately.
ROSpec and reader-configuration changes are serialized through stop, apply,
and restore steps. Reconnect fields are rejected while connected.

The old configuration remains authoritative until the transition succeeds. If
application of a new live configuration fails, the protocol client:

1. reinstalls the old runtime configuration;
2. restores the old `SET_READER_CONFIG` values if new reader configuration had
   reached the device;
3. removes a replacement ROSpec when needed;
4. restarts the former inventory or paused state; and
5. reports the original failure through the transition.

If any rollback step fails, the state is forced to `STATE_DISCONNECTED`. The
client never reports success while the local desired state and reader-applied
state may be mixed. `get_config_state()` returns detached `desired`,
`generated_rospec`, `applied`, and `reported_reader` snapshots for diagnosis.

## State-machine invariants

The following is the normal inventory path; additional sent states cover
AccessSpec deletion and Impinj-extension negotiation.

```text
DISCONNECTED
    │ TCP/TLS connection and connection event
    ▼
CONNECTED ─► SENT_GET_CAPABILITIES ─► SENT_GET_CONFIG ─► SENT_SET_CONFIG
                                                               │
                                                               ▼
            SENT_ADD_ROSPEC ─► SENT_ENABLE_ROSPEC ─► SENT_START_ROSPEC
                                                               │
                                                               ▼
                                                         INVENTORYING
                                                           │       │
                                                        PAUSING   stop
                                                           │       ▼
                                                           └──► PAUSED
```

- `LLRPReaderState` values are local runtime values, not numbers transmitted on
  the wire.
- A `STATE_SENT_*` value means a request is outstanding and its correlated
  response drives the next transition.
- At most one request for a symbolic response type can be pending.
- A new transport session clears partial frames, request callbacks, ROSpec
  cache, configuration snapshots, and disconnect flags before setup.
- Reconnect rebuilds reader-side state; it does not trust cache from the failed
  transport.
- A malformed complete frame ends the session. The decoder does not search the
  payload for a guessed next header because that could desynchronize framing.

The underlying sequences come from
[§11 ROSpec messages](https://ref.gs1.org/standards/llrp/1.1.0/),
[§12 AccessSpec messages](https://ref.gs1.org/standards/llrp/1.1.0/), and
[§13 reader configuration](https://ref.gs1.org/standards/llrp/1.1.0/).

## Timeout and request-correlation rules

Every outgoing request reserves a 32-bit message ID before transport write.
Its pending identity is the exact pair:

```text
(expected response message name, request message ID)
```

Registration occurs before writing, so an immediate response cannot race ahead
of the registry. If the write fails, the pending key, callback, and temporary
state are rolled back. Generated IDs increment and wrap from `0xffffffff` to
`1`; zero is not generated.

When `request_timeout` is set, expiry removes the pending request and remembers
its key in a bounded stale set. A late response therefore cannot complete a
newer request of the same type. Compatibility matching by response type alone
is permitted only when exactly one request of that type exists; ambiguous
matches remain unresolved. Timeout callbacks run after the registry lock is
released so they may safely register/cancel other requests.

The message ID and header layout are defined in
[§17.1 Messages](https://ref.gs1.org/standards/llrp/1.1.0/).

## Protocol bit layouts and wire order

All multi-byte integers are transmitted in network byte order (big-endian).
The decoder uses `struct` formats beginning with `!`; changing them to native
order would make frames platform-dependent.

### Message header

[LLRP 1.1 §17.1](https://ref.gs1.org/standards/llrp/1.1.0/) defines:

```text
bit 15            13 12          10 9                         0
+-------------------+--------------+---------------------------+
| Reserved (3 = 0)  | Version (3)  | Message Type (10)         |
+-------------------+--------------+---------------------------+
| Total message length, including header (32 bits)             |
+--------------------------------------------------------------+
| Message ID / request correlation ID (32 bits)                |
+--------------------------------------------------------------+
```

The common header is 10 bytes. Type 1023 (`CUSTOM_MESSAGE`) immediately adds a
32-bit vendor ID and 8-bit subtype. Total message length includes this custom
extension. `msg_header_encode()` accepts body length and adds the appropriate
header; `msg_header_decode()` returns header length and declared total length
separately.

### Parameter headers

[LLRP 1.1 §17.2.1, TLV and TV Encoding](https://ref.gs1.org/standards/llrp/1.1.0/)
defines:

```text
TLV: Reserved(6 = 0) | Type(10) | Total parameter length(16) | body...
TV:  1 marker bit    | Type(7)  | fixed-size body...
```

TLV total length includes its four-byte header. Custom TLV type 1023 adds a
32-bit vendor ID and 32-bit subtype; its length includes the 12-byte extended
header. TV has no length field, so body length comes from the standard's fixed
type table. `param_header_decode()` tests the TV marker first, then TLV.

`msg_header_decode()` returns
`(message_type, vendor_id, subtype, version, header_length, total_length,
message_id)`. `param_header_decode()` returns
`(parameter_type, vendor_id, subtype, header_length, total_length)`. All lengths
are bytes; vendor values are zero for standard messages/parameters.

## C1G2 operation units

The typed access-operation objects follow
[§16.2.1.3 Access Operation](https://ref.gs1.org/standards/llrp/1.1.0/).
Memory bank (`MB`) values are Reserved 0, EPC 1, TID 2, and User 3. Target
`Pointer` is a bit offset. Read/write `WordPtr`, `WordCount`, and
`WriteDataWordCount` are counts or offsets of 16-bit words; byte payload size
must agree with its word count. Access and kill passwords are 32-bit values.

`C1G2LockPayload` validates privilege 0–3 and data field 0–4. Lock, kill, and
permalock operations can be irreversible. Object construction does not contact
the tag; reader acceptance and tag results are asynchronous.

## Protocol section map

| Concern | Authoritative section | Main implementation surface |
|---|---|---|
| Messages, parameters, fields | [§7](https://ref.gs1.org/standards/llrp/1.1.0/) | Message dictionaries and registry |
| ROSpec/AISpec lifecycle | [§11](https://ref.gs1.org/standards/llrp/1.1.0/) | Inventory state machine, ROSpec generation |
| AccessSpec lifecycle | [§12](https://ref.gs1.org/standards/llrp/1.1.0/) | `start_access_spec()`, C1G2 objects |
| Reader configuration/state | [§13](https://ref.gs1.org/standards/llrp/1.1.0/) | Capabilities, events, GPI, keepalive |
| Reports/notifications | [§14](https://ref.gs1.org/standards/llrp/1.1.0/) | Callbacks, decoded report dictionaries |
| Errors and status | [§15](https://ref.gs1.org/standards/llrp/1.1.0/) | Success checks, response exceptions |
| C1G2 inventory/access | [§16.2.1](https://ref.gs1.org/standards/llrp/1.1.0/) | Filters, RF/singulation, OpSpecs |
| Message binary encoding | [§17.1](https://ref.gs1.org/standards/llrp/1.1.0/) | Message-header helpers |
| TLV/TV encoding | [§17.2.1](https://ref.gs1.org/standards/llrp/1.1.0/) | Parameter-header helpers |
| C1G2 binary encoding | [§17.3.1](https://ref.gs1.org/standards/llrp/1.1.0/) | C1G2 encoders/decoders |

For superseded protocol editions, use the
[official GS1 LLRP archive](https://ref.gs1.org/standards/llrp/archive).
