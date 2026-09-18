# Sllurp v3.1.2

Sllurp 3.1.2 is the first complete, supported GuLuLuIT package baseline. It is
a cumulative release containing the complete maintained feature set, material
bug fixes, compatibility behavior, packaging, examples, and documentation.
It is not merely a documentation update over an earlier public package.

## What is included

### LLRP inventory and tag operations

- Standard LLRP connection, reset, capability discovery, inventory,
  pause/resume, reconnect, timed operation, and shutdown lifecycles.
- Python callbacks for reports, reader events, state changes, and disconnects.
- C1G2 tag-memory read, write, lock, and kill operations with antenna and
  target-filter control.
- One or two AccessSpec target filters and validated operation construction.
- Multi-reader sessions with independent state, counts, recovery, and output
  coordination.
- Command-line inventory, CSV logging, access, reset, version, diagnostics,
  TLS, filtering, duration, reconnect, and vendor-extension controls.

### Secure transport

- Secure LLRP/TLS with certificate and hostname verification enabled by
  default.
- Private certificate authorities, mutual TLS, Server Name Indication, custom
  SSL contexts, configurable endpoints, and encrypted-port defaults.
- IPv4 and IPv6 connections, fragmented/coalesced TCP frames, buffered TLS
  data, and bounded message sizes.
- A machine-readable reader compatibility registry covering supported
  Zebra/Motorola, Impinj, Honeywell/Intermec, ThingMagic, and Alien families.

### Reporting, deduplication, and RF observations

- Continuous N-tag reporting through `ro_report_every_n_tags`, independent
  from antenna-inventory termination.
- Timed deduplication with automatic, hardware, and bounded-memory backends.
- Configurable deduplication identity including EPC, antenna, and observation
  fields.
- Standard antenna, RSSI, channel, timestamp, and seen-count observations.
- Supported Zebra phase and physical-port observations.
- Antenna-aware behavior for single- and multi-antenna deployments.
- Impinj fixed-frequency and tag-content-selector inventory extensions.

### Live configuration and reliability

- Transactional `apply_config()` changes with client-only, inventory-restart,
  reader-reconfiguration, and reconnect-required classification.
- Detached desired/generated/applied/reader-reported snapshots through
  `get_config_state()`.
- Exact request/response correlation by message type and message ID.
- Deterministic request timeouts, cancellation, duplicate-request protection,
  and safe disconnect cleanup.
- Timed pause/resume, operation-duration disconnect, reconnect policy, session
  invalidation, and stable callback dispatch.

### Reader management

- Generic authenticated HTTP/HTTPS management with TLS verification,
  same-origin credential protection, redirect blocking, timeout validation,
  and JSON/text/binary response support.
- Zebra fixed-reader management for supported device, network, certificate,
  service, firmware, region, reboot, and LLRP settings.
- Zebra IoT Connector Local REST status, application, configuration, and
  start/stop operations.
- Impinj R700/R720 REST status, settings, MQTT, power, certificate, service,
  and diagnostic-bundle operations.
- Honeywell/Intermec IF-series WSDL/DCWS discovery and SOAP 1.1/1.2 operations.
- Unified model-aware manager selection with a generic documented-endpoint
  escape hatch.

### Platforms, package, and documentation

- Python 3.10 through 3.14 on Windows, Linux, and macOS.
- A platform-independent wheel and source distribution.
- A generated `sllurp` command wrapper that reports version 3.1.2.
- SHA-256 checksums, downloadable workflow artifacts, and build-provenance
  attestations.
- Complete user and developer guides with diagrams, production checklists,
  extension guidance, security expectations, and symptom-driven
  troubleshooting.
- Runnable inventory, deduplication, telemetry, live-configuration,
  management, FastAPI, WebSocket, and command-line examples.

## Material bug fixes included

### Protocol and decoder correctness

- Malformed or truncated message, parameter, and custom headers are rejected
  safely.
- Message size is bounded by default.
- Reader-configuration wire order, regulatory packing, GPI triggers, Motorola
  filters, singulation details, and repeated custom parameters are handled
  correctly.
- Complete Impinj GPS payloads are preserved and frequency tables use the
  correct 32-bit stride.
- KEEPALIVE acknowledgements reuse the reader message ID.
- Fragmented messages and multiple messages in one read are decoded correctly.

### Runtime and state correctness

- Rejected configuration operations roll back without corrupting desired,
  generated, applied, or active reader state.
- Partial inventory replacement failures restore the correct previous
  specification and reporting behavior.
- Disconnect and reconnect clear stale requests, timers, cached modes, and
  prior-session callbacks.
- Repeated EOF and overlapping cleanup paths produce one disconnect
  notification.
- Request timeout and response races cannot complete the same request twice.
- Pause/resume and timeout tests synchronize on actual state rather than
  scheduler timing.
- Callback registration changes during dispatch take effect safely on the next
  dispatch.
- FastAPI updates are bounded and application shutdown stops reader activity.

### CLI, logging, data, and security correctness

- Access failures return a nonzero process status.
- Normal logs do not contaminate standard output or CSV pipelines.
- Application logging handlers survive package logging reconfiguration.
- UTC timestamps, reader-time fallback, EPC filtering, IPv6 formatting,
  multi-reader counts, and serialized CSV writes are corrected.
- Tag-write payloads are read once and reused safely across readers.
- Invalid durations, reconnect settings, deduplication windows, capacities,
  selectors, power/channel values, SGTIN data, lock fields, timeouts, and
  incompatible telemetry combinations are rejected early.
- Reader-management credentials remain bound to the configured origin and are
  not forwarded across redirects.
- Reader XML is parsed with hardened XML handling.

## Compatibility and deprecated behavior

Sllurp 3.1.2 does not formally deprecate a supported public API and does not
emit public deprecation warnings. The following compatibility behavior should
still be understood:

- `report_every_n_tags` and `report_timeout_ms` are legacy names retained
  for compatibility. They stop an antenna inventory; they do not configure
  continuous report cadence. Use `ro_report_every_n_tags` for continuous
  N-tag reports.
- The historical `Channelist` frequency key is accepted and normalized.
  New configuration should use `ChannelList`.
- `SecureLLRPReaderClient` is a supported alias of
  `LLRPTLSReaderClient`, not a deprecated class.
- Low-level decoder compatibility helpers marked legacy are internal and are
  not a supported application API.
- Private legacy Impinj web endpoints are not supported. Use LLRP for RFID
  operations and vendor-documented RShell/SSH for device administration.
- Obsolete wrappers and the superseded Tornado demonstration are not included;
  the maintained web example uses FastAPI and WebSockets.

## Download and verify

Download `sllurp-3.1.2-py3-none-any.whl`,
`sllurp-3.1.2.tar.gz`, and `SHA256SUMS.txt` from this release:

```bash
sha256sum -c SHA256SUMS.txt
python -m pip install ./sllurp-3.1.2-py3-none-any.whl
sllurp --version
```

The expected version output is:

```text
sllurp, version 3.1.2
```

GitHub publishes build-provenance attestations for both Python distributions:

```bash
gh attestation verify sllurp-3.1.2-py3-none-any.whl --repo GuLuLuIt/sllurp
```

## Package-name note

The `sllurp` distribution published on PyPI is not this GuLuLuIT build.
Install the wheel or immutable GitHub release tag from this repository.

## License and attribution

Sllurp 3.1.2 is distributed under GPL-3.0-only and preserves inherited
source-file copyright notices. `LICENSE.txt` contains the license text and
`NOTICE.md` records attribution. Neither file is a version-history notice.
