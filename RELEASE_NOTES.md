# Sllurp v3.1.1

This GuLuLuIT maintenance release retains the production-focused Sllurp feature set and the import-compatible `sllurp` module name. It consolidates package and documentation provenance on the maintained GuLuLuIT repository and includes deterministic cross-platform timeout-test synchronization.

## Highlights

- Standard LLRP inventory, access operations, reconnect handling, logging, and multi-reader support.
- Explicit continuous `ROReportSpec` cadence separated from AISpec termination.
- Secure LLRP/TLS with certificate verification, private CAs, mutual TLS, SNI, and conventional port 5085 support.
- Timed tag deduplication with automatic, hardware, and bounded-memory backends.
- Generic HTTP/HTTPS reader management plus Zebra Reader Manager, Zebra IoT Connector, Impinj R700/R720, and Honeywell/Intermec IF-family adapters.
- Transactional runtime reconfiguration and desired/generated/applied/reader-reported state inspection.
- Standard and Zebra RF telemetry, including per-antenna RSSI, channel, timestamps, and supported phase data.
- Python 3.10 through 3.14 support across Linux, Windows, and macOS CI.
- Expanded protocol, state-machine, malformed-input, concurrency, hardware-regression, documentation, and package tests.

## Download and verify

Download `sllurp-3.1.1-py3-none-any.whl`, `sllurp-3.1.1.tar.gz`, and `SHA256SUMS.txt` from this release. Verify the selected file before installation:

```bash
sha256sum -c SHA256SUMS.txt
python -m pip install ./sllurp-3.1.1-py3-none-any.whl
sllurp --version
```

GitHub also publishes build-provenance attestations for both Python distributions. With GitHub CLI installed, verify an artifact against this repository:

```bash
gh attestation verify sllurp-3.1.1-py3-none-any.whl --repo GuLuLuIt/sllurp
```

## Important package-name note

The `sllurp` distribution published on PyPI is not this GuLuLuIT build. This project is distributed through GuLuLuIT GitHub Releases and immutable Git tags. Install its wheel or tagged GitHub source explicitly.

## License and lineage

This repository is distributed under GPL-3.0-only and preserves inherited source-file copyright notices. See `LICENSE.txt` and `NOTICE.md` in the source distribution for the complete license and attribution information.
