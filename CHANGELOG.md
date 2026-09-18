# Changelog

Sllurp 3.1.2 is the first complete, supported GuLuLuIT package baseline. This
entry is cumulative: it records the maintained feature set and material fixes
shipped in the package rather than relying on incomplete pre-release notices.

## 3.1.2 — 2026-09-17

### Start here: what 3.1.2 lets you do

The technical lists below are the permanent release record. If you are trying
to decide whether a feature solves your problem, start with these examples.
Replace `192.0.2.10` and the certificate path with values for your reader.

| Goal | What it means in practice | Try it |
|---|---|---|
| Read tags from one reader | Connect, configure inventory, and print observations. | `sllurp inventory -a 0 -t 10 192.0.2.10` |
| Read several readers | Keep independent sessions and counts in one process. | `sllurp inventory -a 0 192.0.2.10 192.0.2.11` |
| Encrypt the reader connection | Verify the reader certificate and use Secure LLRP. | `sllurp inventory --tls --tls-ca-file reader-ca.pem reader.example` |
| Receive reports without stopping inventory | Ask for a report every N observations while the antenna inventory continues. | `sllurp inventory --ro-report-every-n-tags 25 192.0.2.10` |
| Suppress repeated reads briefly | Emit one observation per deduplication identity during a time window. | `sllurp inventory --dedup-seconds 2 --dedup-backend auto -a 0 192.0.2.10` |
| Capture RF evidence | Request antenna, RSSI, channel, timestamps, counts, and supported vendor observations. | `python examples/rf_telemetry.py 192.0.2.10 --mode standard --antenna 1` |
| Change a running session | Apply a validated configuration transition with success/failure state and rollback. | `python examples/runtime_config.py 192.0.2.10` |
| Read device settings | Use only the management API documented for the reader model. | `python examples/reader_management_generic.py https://reader.example /documented/api/settings --username READER_USERNAME` |

Minimal Python inventory:

```python
from sllurp.llrp import LLRPReaderClient, LLRPReaderConfig


def on_tags(_reader, reports):
    for tag in reports:
        print(tag.get("EPC") or tag.get("EPCData"), tag.get("AntennaID"))


reader = LLRPReaderClient(
    "192.0.2.10",
    config=LLRPReaderConfig(
        {"antennas": [0], "ro_report_every_n_tags": 1}
    ),
)
reader.add_tag_report_callback(on_tags)
reader.connect()

try:
    reader.join()
except KeyboardInterrupt:
    pass
finally:
    reader.disconnect(timeout=2)
```

Expected result: each callback receives a list of decoded tag observations.
The exact fields depend on the configured selectors and reader support.

Why the less visible fixes matter:

| Fix area | Problem it prevents |
|---|---|
| Bounded and strict decoding | A malformed or oversized reader frame consuming excessive memory or desynchronizing the connection. |
| Exact request correlation | A late response incorrectly completing a newer request of the same type. |
| Transactional configuration | A rejected live change leaving application state different from reader state. |
| Deterministic disconnect cleanup | Duplicate notifications, abandoned timers, or stale requests during reconnect and shutdown. |
| Serialized streaming output | Corrupted multi-reader CSV and unbounded memory use in long sessions. |
| Same-origin management security | Reader credentials being forwarded to a different host after a redirect. |

For every supported Python interface, its inputs, callbacks, return values,
exceptions, and additional examples, use the
[Sllurp 3.1.2 API reference](API_REFERENCE.md). The
[examples index](examples/README.md) contains complete runnable programs, and
the [user guide](USER_GUIDE.md) explains production decisions and recovery.

### Core LLRP and application features

- Standard LLRP message and parameter encoding/decoding for reader inventory,
  reader events, reports, configuration, and C1G2 tag operations.
- Reader lifecycle management covering connection, reset, capability
  discovery, inventory start/stop, polite shutdown, forced disconnect,
  reconnect policy, timed operation, pause, and automatic resume.
- Python callback APIs for tag reports, reader events, state changes, and
  disconnect notifications, with stable callback snapshots and exception
  isolation.
- C1G2 tag-memory read, write, lock, and kill operations, including one or two
  target filters, explicit antenna selection, operation counts, and access
  timing.
- Multi-reader operation with independent reader state, counts, reconnect
  behavior, callbacks, deduplication, and serialized downstream logging.
- Command-line workflows for inventory, CSV logging, tag access, reader reset,
  installed-version reporting, TLS, filters, antennas, reconnects, duration,
  reporting cadence, and vendor inventory extensions.
- Capability-driven antenna selection, transmit-power mapping, mode selection,
  Tari validation, frequency/channel configuration, and vendor-extension
  opt-in.

### Secure transport and reader compatibility

- Plain LLRP and Secure LLRP/TLS clients, with encrypted port selection,
  certificate and hostname verification, private certificate authorities,
  mutual TLS, Server Name Indication, custom SSL contexts, and configurable
  endpoints.
- A machine-readable reader registry with normalized model lookup, aliases,
  antenna capabilities, vendor-extension metadata, and conservative Secure
  LLRP support status.
- Documented compatibility for supported Zebra/Motorola, Impinj,
  Honeywell/Intermec, ThingMagic, and Alien reader families, with
  firmware-dependent claims identified explicitly.
- IPv4, IPv6, fragmented TCP frames, multiple frames per read, buffered TLS
  data, and bounded incoming-message handling.

### Reporting, deduplication, and telemetry

- Explicit continuous report cadence through `ro_report_every_n_tags` and the
  corresponding command-line option, independent from antenna-inventory stop
  conditions.
- Timed tag deduplication with automatic backend selection, reader-side
  hardware suppression where compatible, and a bounded-memory client backend.
- Deduplication keys that can include EPC, antenna, and configured observation
  fields; deterministic freezing of nested mappings and sets; eviction and
  capacity accounting.
- Standard RF observations including antenna, peak RSSI, channel, first-seen
  time, last-seen time, and seen count.
- Supported Zebra telemetry extensions for phase and physical antenna-port
  information, with antenna-aware behavior for single- and multi-antenna
  deployments.
- Impinj inventory extensions for fixed-frequency operation and requested tag
  report content.

### Runtime configuration and request handling

- Validated `LLRPReaderConfig` construction, scalar transmit-power expansion,
  finite/range checking, incompatible-option rejection, and safe defaults.
- Transactional `apply_config()` transitions that classify changes as
  client-only, inventory restart, reader reconfiguration, or reconnect
  required.
- `get_config_state()` snapshots for desired, generated, applied, and
  reader-reported configuration, returned as detached data.
- Exact pending-request correlation by response type and message ID, with
  deterministic timeouts, cancellation, duplicate-request rejection, and
  safe legacy fallback only when one unambiguous request exists.
- Runtime pause/resume scheduling, duration-based disconnect, state reset, and
  stale-session invalidation.

### Reader management

- A vendor-neutral HTTP/HTTPS management transport with Basic authentication,
  JSON/text/binary handling, bounded timeouts, TLS verification, same-origin
  credential protection, and cross-origin redirect blocking.
- Zebra fixed-reader Reader Management XML operations for supported device,
  network, service, certificate, firmware, reboot, region, and LLRP settings.
- Zebra IoT Connector Local REST operations for status, applications,
  configuration, start/stop control, and response/error normalization.
- Impinj R700/R720 REST management for status, documented settings resources,
  MQTT, power, certificates, service assignment, and diagnostic bundles.
- Honeywell/Intermec IF-series WSDL/DCWS discovery and SOAP 1.1/1.2 operations,
  including endpoint overrides and XML hardening.
- Unified manager selection with explicit rejection of undocumented private
  web interfaces on legacy reader platforms.

### Packaging, platforms, examples, and documentation

- An independently installable `sllurp-3.1.2-py3-none-any.whl` and source
  distribution for Python 3.10 through 3.14 on Windows, Linux, and macOS.
- A generated `sllurp` command wrapper whose version is sourced from the
  package, plus release guards requiring tags, artifact names, and metadata to
  agree.
- Release checksums, workflow artifacts, and build-provenance attestations.
- Runnable examples for basic inventory, timed deduplication, RF telemetry,
  live configuration, generic management, Zebra management, Impinj management,
  Honeywell/Intermec management, FastAPI, WebSocket delivery, and command-line
  recipes.
- A task-oriented user guide and architecture-oriented developer guide with
  source-native diagrams for session lifecycle, callback/worker boundaries,
  multi-reader flow, runtime architecture, and configuration transitions.
- Cross-platform Quick Start instructions, reader compatibility guidance,
  security expectations, troubleshooting, contribution guidance, and release
  procedures.

### Protocol and wire-format fixes

- Reject truncated or internally inconsistent LLRP message, TLV, TV, and
  custom-parameter headers before unpacking or allocating invalid payloads.
- Bound the default accepted message size while allowing an explicit override.
- Correct GET_READER_CONFIG field order, regulatory-capability packing, GPI
  trigger typing, Motorola filter-tag decoding, and malformed C1G2 metadata.
- Accept standard and known legacy singulation-detail layouts without
  confusing them with report cadence or inventory lifetime.
- Preserve repeated custom protocol parameters rather than overwriting earlier
  values.
- Preserve complete Impinj GPS sentence payloads and correct the 32-bit
  frequency-table decoding stride.
- Correlate KEEPALIVE acknowledgements with the reader's incoming message ID
  without advancing the client request counter.
- Reassemble fragmented frames and decode multiple messages received in one
  socket read.

### State-machine, concurrency, and lifecycle fixes

- Roll back rejected reader and inventory configuration transitions without
  leaving replacement specifications or mutated desired state behind.
- Preserve existing inventory/report behavior when configuration changes are
  rejected, and restore the correct prior state after partial failures.
- Reset protocol state, pending requests, mode caches, timers, and session
  generation data on hard disconnect or reconnect.
- Deliver disconnect notification exactly once even when socket shutdown,
  close, peer EOF, or repeated cleanup paths overlap.
- Prevent request timeout and response handling from completing the same
  operation twice.
- Make timed pause/resume and timeout behavior event-driven and
  scheduler-independent.
- Protect callback iteration when callbacks add or remove callbacks during
  dispatch.
- Bound asynchronous FastAPI tag updates and cleanly stop reader threads during
  application shutdown.

### CLI, logging, data, and validation fixes

- Return nonzero status for access connection and operation failures.
- Keep normal logs off standard output so CSV and pipeline output remain clean.
- Preserve application-owned logging handlers across logging
  reinitialization.
- Emit UTC timestamps consistently, including correct millisecond formatting.
- Stream CSV rows rather than accumulating an unbounded in-memory list.
- Serialize multi-reader CSV writes, normalize byte EPC filters, format IPv6
  reader addresses correctly, and fall back safely when reader timestamps are
  unavailable.
- Track inventory counts independently per reader and reuse a tag-write payload
  safely across multiple readers.
- Validate deduplication windows/capacities, management timeouts, pause
  durations, reconnect settings, tag selectors, SGTIN-96 input, lock fields,
  power indices, channels, and telemetry combinations.
- Use hardened XML parsing for untrusted reader responses and prevent
  credentials from crossing configured management origins.

### Compatibility and deprecation status

- No supported public API emits a deprecation warning in 3.1.2, and no public
  API is scheduled for removal by this release.
- `report_every_n_tags`, `report_timeout_ms`, and their command-line forms
  are retained for compatibility. Despite their historical names, they stop an
  antenna inventory and cause accumulated observations to be returned at that
  boundary. New code that wants continuous N-tag delivery should use
  `ro_report_every_n_tags`.
- The misspelled legacy frequency key `Channelist` is accepted and normalized
  to `ChannelList`; new configurations should use `ChannelList`.
- `SecureLLRPReaderClient` remains a supported descriptive alias of
  `LLRPTLSReaderClient`; neither name is deprecated.
- Internal low-level decoder compatibility helpers marked as legacy are not
  part of the supported public API and may be refactored in a future release.
- Private Impinj Speedway web-interface endpoints are intentionally unsupported;
  use standard LLRP for RFID control and vendor-documented RShell/SSH for device
  administration.
- Obsolete repository wrappers and the superseded Tornado demonstration are
  not shipped. The maintained web example uses FastAPI and WebSockets.
