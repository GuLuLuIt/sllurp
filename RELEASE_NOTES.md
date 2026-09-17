# Sllurp v3.1.0

This is the first formal GuLuLuIT release of the production-focused Sllurp fork. It is based on the upstream Sllurp project and remains import-compatible as `sllurp`, while adding maintained production features and fixes developed in this fork.

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

Download `sllurp-3.1.0-py3-none-any.whl`, `sllurp-3.1.0.tar.gz`, and `SHA256SUMS.txt` from this release. Verify the selected file before installation:

```bash
sha256sum -c SHA256SUMS.txt
python -m pip install ./sllurp-3.1.0-py3-none-any.whl
sllurp --version
```

GitHub also publishes build-provenance attestations for both Python distributions. With GitHub CLI installed, verify an artifact against this repository:

```bash
gh attestation verify sllurp-3.1.0-py3-none-any.whl --repo GuLuLuIt/sllurp
```

## Important package-name note

The `sllurp` project on PyPI belongs to the upstream project. This fork is distributed through its GitHub Releases and immutable Git tags. Running `pip install sllurp` without a file or GitHub URL installs the upstream PyPI distribution, not this fork.

## License and lineage

This repository is a modified fork of `sllurp/sllurp` and is distributed under GPL-3.0-only. See `LICENSE.txt` and `NOTICE.md` in the source distribution for the complete license and attribution information.
